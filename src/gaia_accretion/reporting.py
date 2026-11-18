"""只读加载已完成运行并输出单源图文报告，不调用拟合或模型预测。"""
from __future__ import annotations

import base64
from html import escape
import json
import struct
from pathlib import Path
from datetime import datetime, timezone

import numpy as np

from . import __version__
from .classical.xp_workbench import digest, exact_id, new_directory, read_json, review, write_json

INPUT_FILES = ('status.json', 'summary.json', 'review.json', 'run_contract.json',
               'spectrum.npz', 'prediction.npz', 'posterior.npz')
VERIFIED_FILES = ('summary.json', 'review.json', 'run_contract.json', 'posterior.npz')
QUANTITIES = {
    'facc_w_m2': ('Facc', 'W m⁻²', 'slab 在 50–2477.47 nm 的本征积分通量'),
    'r_red': ('r', '无量纲', '消光后 700–900 nm slab / 光球平均通量密度比'),
    'q_model_facc_over_fstar': ('q', '无量纲', '模型 Facc / Fstar，包含光球总量修正'),
    'spt_num': ('光谱型编码', 'K0=60，M0=70', '联合后验，不等同于温度的直接测量'),
    'av_mag': ('Av', 'mag', '视向消光'),
    'fstar_bol_w_m2': ('Fstar', 'W m⁻²', '光球总通量诊断'),
    'lacc_lsun': ('Lacc', 'L☉', '固定距离条件下的吸积光度'),
    'mdot_msun_yr': ('Mdot', 'M☉ yr⁻¹', '固定恒星参数和 Rin=5Rstar 条件下的质量吸积率'),
}


def load_saved(run):
    run = Path(run).expanduser().resolve()
    missing = [name for name in INPUT_FILES if not (run/name).is_file()]
    if missing:
        raise FileNotFoundError('报告缺少保存产物：' + ', '.join(missing) + '；请提供完整运行，不会自动重新拟合或生成预测')
    hashes = {name: digest(run/name) for name in INPUT_FILES}
    report = review(run)
    summary, contract = read_json(run/'summary.json'), read_json(run/'run_contract.json')
    status = read_json(run/'status.json')
    arrays = []
    for name in ('spectrum.npz', 'prediction.npz', 'posterior.npz'):
        with np.load(run/name, allow_pickle=False) as saved:
            arrays.append(dict(saved))
    spectrum, prediction, posterior = arrays
    sid = exact_id(report['source_id'])
    ids = [summary['source_id'], status['source_id'], contract['metadata']['source_id'],
           report['metadata']['source_id'], spectrum['source_id'].item()]
    if any(exact_id(x) != sid for x in ids):
        raise ValueError('保存产物的源编号不一致')
    wave = spectrum['wave']; n = len(wave)
    if wave.ndim != 1 or not np.isfinite(wave).all() or not np.all(np.diff(wave) > 0):
        raise ValueError('保存的波长网格无效')
    for name in ('flux', 'mask'):
        if spectrum[name].shape != (n,): raise ValueError(f'光谱字段{name}维度不一致')
    mask = spectrum['mask']
    if mask.dtype != bool or not mask.any(): raise ValueError('保存的光谱掩码无效')
    factor = spectrum['noise_factor']
    if factor.ndim != 2 or factor.shape[0] != n or not np.isfinite(factor).all():
        raise ValueError('保存的误差因子无效')
    if not np.isfinite(spectrum['flux'][mask]).all(): raise ValueError('有效观测含非有限通量')
    for name in ('lower', 'median', 'upper', 'photo', 'slab'):
        if prediction[name].shape != (n,) or not np.isfinite(prediction[name]).all():
            raise ValueError(f'保存的预测字段{name}无效')
    if np.any(prediction['lower'] > prediction['median']) or np.any(prediction['median'] > prediction['upper']):
        raise ValueError('预测区间次序无效')
    windows = np.asarray(contract['config']['fit_windows_nm'])
    if windows.ndim != 2 or windows.shape[1] != 2: raise ValueError('拟合波段定义无效')
    for name in ('band_observed', 'band_predicted', 'band_error', 'band_residual_sigma'):
        if prediction[name].shape != (len(windows),) or not np.isfinite(prediction[name]).all():
            raise ValueError(f'保存的波段字段{name}无效')
    if np.any(prediction['band_error'] <= 0): raise ValueError('波段误差必须为正')
    count = None
    for name in ('positive_spt', 'positive_av_mag', 'positive_r_red', 'positive_facc_w_m2'):
        values = posterior[name]
        if values.ndim != 1 or not len(values) or not np.isfinite(values).all(): raise ValueError('正分支样本无效')
        if count is not None and len(values) != count: raise ValueError('正分支样本长度不一致')
        count = len(values)
    if np.any(posterior['positive_r_red'] <= 0) or np.any(posterior['positive_facc_w_m2'] <= 0):
        raise ValueError('正分支对数图包含非正数')
    p0 = report['p_zero']
    if not isinstance(p0, (int, float)) or not 0 <= p0 <= 1: raise ValueError('P0不在有效范围内')
    levels = report['quantile_levels']
    if len(levels) != 4 or not np.allclose(levels, [.16,.5,.84,.95]): raise ValueError('报告要求已存16/50/84/95%分位数')
    for values in report['quantities'].values():
        if values is not None and (len(values) != len(levels) or not np.isfinite(values).all()):
            raise ValueError('已存结果分位数缺失或无效')
    return report, contract, spectrum, prediction, posterior, hashes


def _fmt(value):
    return '未提供' if value is None else f'{value:.5g}'


def write_html(destination, report, contract, images, provenance):
    """图片内嵌，所有来自数据的文字转义，单个HTML可离线打开。"""
    esc = lambda x: escape(str(x), quote=True)
    def picture(key, alt):
        raw = (destination/images[key]).read_bytes()
        width, height = struct.unpack('>II', raw[16:24])
        encoded = base64.b64encode(raw).decode('ascii')
        # 预留图片比例，避免页内导航跳转后因图片展开而错位。
        return f'<img src="data:image/png;base64,{encoded}" alt="{esc(alt)}" width="{width}" height="{height}">'
    meta = report['metadata']; q = report['quantities']
    rows = []
    for key, (name, unit, meaning) in QUANTITIES.items():
        values = q.get(key)
        cells = ''.join(f'<td>{esc(_fmt(v))}</td>' for v in values) if values is not None else '<td colspan="4">未提供；未推导该量</td>'
        rows.append(f'<tr><th scope="row">{esc(name)}</th><td>{esc(unit)}</td>{cells}<td>{esc(meaning)}</td></tr>')
    metrics = ''.join(f'<tr><th>{esc(k)}</th><td>{esc(_fmt(v)) if isinstance(v,(int,float)) or v is None else esc(v)}</td></tr>' for k,v in report['diagnostic_metrics'].items())
    flags = '、'.join(report['diagnostic_flags']) or '未触发已列旗标；这不构成可靠性认证'
    limits = ''.join(f'<li>{esc(x)}</li>' for x in report['limits'])
    cfg = contract['config']
    provenance_rows = ''.join(f'<tr><th>{esc(k)}</th><td class="hash">{esc(v)}</td></tr>' for k,v in provenance['input_sha256'].items())
    html = f'''<!doctype html>
<html lang="zh-CN"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{esc(report['name'])} · Gaia XP 单源报告</title>
<style>
:root{{color-scheme:light;--ink:#172d3c;--muted:#526775;--accent:#1d6587;--line:#dbe4e9}}
*{{box-sizing:border-box}}body{{margin:0;background:#f1f5f7;color:var(--ink);font:16px/1.7 system-ui,"Microsoft YaHei",sans-serif}}
main{{max-width:1240px;margin:auto;padding:36px 28px 60px}}header{{border-top:5px solid var(--accent);padding:26px 0 22px}}
h1{{font-size:32px;line-height:1.25;margin:8px 0 12px}}h2{{font-size:23px;margin:0 0 14px}}h3{{font-size:18px}}
p{{margin:10px 0}}.eyebrow{{color:var(--accent);font-size:13px;letter-spacing:.12em}}.sub,.caption{{color:var(--muted);font-size:14px}}
section{{background:white;border:1px solid var(--line);border-radius:12px;padding:25px;margin:20px 0}}
nav{{display:flex;gap:18px;flex-wrap:wrap}}a{{color:var(--accent)}}.cards{{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:14px;margin:22px 0}}
.card{{background:white;border:1px solid var(--line);border-radius:10px;padding:16px}}.card b{{display:block;font-size:20px}}
.table-wrap{{overflow-x:auto}}table{{width:100%;border-collapse:collapse;font-size:14px}}th,td{{border-bottom:1px solid var(--line);padding:10px;text-align:left;vertical-align:top}}
th{{font-weight:600}}td{{font-variant-numeric:tabular-nums}}img{{display:block;width:100%;height:auto}}figure{{margin:0}}figcaption{{padding-top:14px;color:var(--muted);font-size:14px}}
details{{margin-top:18px}}summary{{cursor:pointer;color:var(--accent);font-weight:600}}.hash,code{{font-family:ui-monospace,monospace;overflow-wrap:anywhere}}.hash{{font-size:11px}}
.notice{{border-left:4px solid #b88436;padding-left:14px}}footer{{color:var(--muted);font-size:13px}}
@media(max-width:700px){{main{{padding:18px 12px}}section{{padding:15px}}h1{{font-size:25px}}.cards{{grid-template-columns:1fr}}}}
@media print{{body{{background:white}}main{{max-width:none;padding:0}}section{{break-inside:avoid;border:none;padding:10px 0}}nav{{display:none}}}}
</style></head><body><main>
<header><div class="eyebrow">GAIA XP · SAVED-RUN REPORT</div><h1>{esc(report['name'])}</h1>
<p>Gaia 源编号 <code>{esc(report['source_id'])}</code> · {esc(meta['release'])} · {esc(meta['product'])}</p>
<p class="sub">由保存的模型预测与后验生成。此报告没有重新拟合或重新计算正式物理分位数。</p>
<nav><a href="#overview">总览</a><a href="#results">主要结果</a><a href="#spectrum">光谱与残差</a><a href="#posterior">后验</a><a href="#reliability">可靠性</a><a href="#provenance">来源</a></nav></header>
<div class="cards"><div class="card">数值积分检查<b>{esc(report['numerical_status'])}</b><span class="sub">保存的积分稳定性检查</span></div>
<div class="card">零吸积分支权重 P0<b>{esc(_fmt(report['p_zero']))}</b><span class="sub">模型与先验条件下的权重</span></div>
<div class="card">独立物理标定<b>尚未建立</b><span class="sub">好拟合不等于普适校准测量</span></div></div>
<section id="overview"><h2>一源一张总览图</h2><figure>{picture('overview','主要结果、全谱拟合、蓝端放大、波段残差和正分支联合后验总览')}
<figcaption>全谱、蓝端、残差与后验使用同一保存运行。总览中的分位数取自正式结果；corner 仅包含正分支。</figcaption></figure></section>
<section id="results"><h2>主要结果</h2><p>表中依次为 16%、50%、84%、95% 分位值。Facc、r、q 包含精确零分支；中位数为零不能解释为精确测得零吸积。p95 是后验上限，不是仪器检出阈值。</p>
<div class="table-wrap"><table><thead><tr><th>物理量</th><th>单位</th><th>p16</th><th>p50</th><th>p84</th><th>p95</th><th>含义</th></tr></thead><tbody>{''.join(rows)}</tbody></table></div>
<p>{esc(report['stellar_conversion'])}。</p><p>正分支对零分支 ln BF = {esc(_fmt(report['ln_bayes_factor']))}；这里使用自然对数。P0 和 Bayes 因子尚未标定为真实吸积概率或误报率。</p></section>
<section id="spectrum"><h2>全谱、蓝端放大与残差</h2><figure>{picture('spectrum','全谱与蓝端模型分量以及相关宽波段残差')}
<figcaption>观测及预测以观测 700–900 nm 平均通量密度归一。观测阴影为逐点边缘 1σ；模型阴影为保存预测的 16–84% 范围。灰线为观测，蓝线为总模型，光球和 slab 分量分别显示；逐波长分量中位数不必相加成总谱中位数。残差使用相关宽波段的边缘观测误差，不是独立点的约化 χ²。</figcaption></figure></section>
<section id="posterior"><h2>参数联合后验</h2><p class="notice">下图仅使用正吸积分支样本；P0={esc(_fmt(report['p_zero']))} 的零点质量另行报告，不送入 log 坐标。二维分布用于看退化，不能作为单独的检出证明。</p>
<figure>{picture('posterior','光谱型、消光、光学超额比与Facc的条件正分支corner图')}<figcaption>对角线为正分支边缘分布，非对角面板显示参数退化；这些条件分布与上表含零分支的正式分位数用途不同。后验来自数值网格积分与抽样，图中不存在 MCMC 链收敛检验。</figcaption></figure></section>
<section id="reliability"><h2>可靠性与解释范围</h2><p><b>适用性旗标：</b>{esc(flags)}。</p><p>{esc(report['prior_note'])}。</p>
<details><summary>查看保存的诊断指标</summary><div class="table-wrap"><table>{metrics}</table></div></details><ul>{limits}</ul></section>
<section id="provenance"><h2>方法、输入与可追溯性</h2><p>拟合方法 <code>{esc(report['method_id'])}</code>；报告程序版本 {esc(__version__)}。</p>
<p>外部先验中心：光谱型编码 {esc(meta['spt_num'])}、Av={esc(meta['av_mag'])} mag、Teff={esc(meta['teff_k'])} K。Rv={esc(cfg['rv'])}，Student-t 自由度 {esc(cfg['degrees_of_freedom'])}。光谱型与消光先验宽度及模板假设见运行契约。</p>
<p>标定：{esc(meta['calibration_version'])}。输入来源：{esc(meta['input_reference'])}。先验来源：{esc(meta['prior_reference'])}。</p>
<p class="notice">summary、review、posterior 与运行契约已对照原运行保存的哈希。旧运行的 spectrum、prediction 和 status 没有各自预存校验值，本报告记录它们本次读取的哈希；这不证明它们自拟合时起从未改变。</p>
<details><summary>查看本次读取文件的 SHA256</summary><div class="table-wrap"><table>{provenance_rows}</table></div></details></section>
<footer>离线自包含报告 · 不联网、不依赖模型资产 · {esc(provenance['created_utc'])}</footer>
</main></body></html>'''
    (destination/'report.html').write_text(html, encoding='utf-8')


def build_report(run, output):
    run, destination = Path(run).expanduser().resolve(), Path(output).expanduser().resolve()
    if destination.is_relative_to(run): raise ValueError('报告输出须位于原运行目录之外')
    report, contract, spectrum, prediction, posterior, hashes = load_saved(run)
    destination = new_directory(destination)
    provenance = dict(schema_version=1, report_version=__version__, source_id=report['source_id'],
                      created_utc=datetime.now(timezone.utc).isoformat(), input_run=str(run),
                      input_sha256=hashes, preexisting_hash_verified=list(VERIFIED_FILES),
                      snapshot_only=['status.json','spectrum.npz','prediction.npz'], fit_executed=False)
    try:
        from .report_plots import render_overview
        images = render_overview(destination, spectrum, prediction, posterior, report, contract)
        write_html(destination, report, contract, images, provenance)
        if any(digest(run/name) != sha for name,sha in hashes.items()):
            raise RuntimeError('报告期间输入运行发生变化，报告未标记为完成')
        provenance.update(status='complete', output_sha256={name:digest(destination/name) for name in [*images.values(),'report.html']})
    except Exception as error:
        provenance.update(status='failed', error=str(error))
        write_json(destination/'report_manifest.json', provenance)
        raise
    write_json(destination/'report_manifest.json', provenance)
    return dict(status='complete', source_id=report['source_id'], output=str(destination),
                overview=str(destination/'overview.png'), html=str(destination/'report.html'), fit_executed=False)
