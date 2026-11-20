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
from .report_language import METRIC_LABELS, english_note
from .classical.xp_workbench import digest, exact_id, new_directory, read_json, review, write_json

INPUT_FILES = ('status.json', 'summary.json', 'review.json', 'run_contract.json',
               'spectrum.npz', 'prediction.npz', 'posterior.npz')
VERIFIED_FILES = ('summary.json', 'review.json', 'run_contract.json', 'posterior.npz')
QUANTITIES = {
    'facc_w_m2': ('Facc', 'W m⁻²', 'Intrinsic slab flux integrated over 50–2477.47 nm'),
    'r_red': ('r', 'dimensionless', 'Ratio of the mean reddened slab and photospheric flux densities over 700–900 nm'),
    'q_model_facc_over_fstar': ('q', 'dimensionless', 'Facc divided by the bolometrically corrected photospheric flux'),
    'spt_num': ('Spectral type index', 'K0 = 60, M0 = 70', 'Spectral subtype inferred jointly with extinction and excess'),
    'av_mag': ('Av', 'mag', 'V-band extinction'),
    'fstar_bol_w_m2': ('Fstar', 'W m⁻²', 'Inferred bolometric photospheric flux'),
    'lacc_lsun': ('Lacc', 'L☉', 'Accretion luminosity at the adopted distance'),
    'mdot_msun_yr': ('Mdot', 'M☉ yr⁻¹', 'Mass accretion rate for the adopted stellar parameters and Rin = 5 Rstar'),
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
    return 'Not available' if value is None else f'{value:.5g}'


def write_html(destination, report, contract, images, provenance, photometry=None, spectra=None, comparison=None, epoch_html=''):
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
        cells = ''.join(f'<td>{esc(_fmt(v))}</td>' for v in values) if values is not None else '<td colspan="4">Not derived</td>'
        rows.append(f'<tr><th scope="row">{esc(name)}</th><td>{esc(unit)}</td>{cells}<td>{esc(meaning)}</td></tr>')
    metrics = ''.join(f'<tr><th>{esc(METRIC_LABELS.get(k, k))}</th><td>{esc(_fmt(v)) if isinstance(v,(int,float)) or v is None else esc(v)}</td></tr>' for k,v in report['diagnostic_metrics'].items())
    flags = ', '.join(english_note(flag) for flag in report['diagnostic_flags']) or 'No diagnostic flags were raised'
    limits = ''.join(f'<li>{esc(english_note(x))}</li>' for x in report['limits'])
    cfg = contract['config']
    provenance_rows = ''.join(f'<tr><th>{esc(k)}</th><td class="hash">{esc(v)}</td></tr>' for k,v in provenance['input_sha256'].items())
    photometry_section = ''
    if photometry is not None:
        from .photometry_report import photometry_html
        photometry_section = photometry_html(photometry, picture)
    photometry_nav = '<a href="#photometry">Photometry</a>' if photometry is not None else ''
    spectroscopy_section = spectroscopy_nav = ''
    if spectra is not None:
        from .spectroscopy_report import spectroscopy_html
        spectroscopy_section = spectroscopy_html(spectra, comparison, picture)
        spectroscopy_nav = '<a href="#spectroscopy">Archival spectra</a>'
    html = f'''<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{esc(report['name'])} · Gaia XP stellar spectrum</title>
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
<header><div class="eyebrow">GAIA XP · STELLAR ACCRETION</div><h1>{esc(report['name'])}</h1>
<p>Gaia source ID <code>{esc(report['source_id'])}</code> · {esc(meta['release'])} · {esc('Mean XP spectrum' if meta['product']=='mean_xp' else meta['product'])}</p>
<p class="sub">The XP fit constrains the optical excess. Archival observations provide independent measurements of the continuum and emission lines.</p>
<nav><a href="#epochs">Epoch spectra</a><a href="#overview">XP fit</a>{spectroscopy_nav}{photometry_nav}<a href="#results">Fit results</a><a href="#reliability">Interpretation</a><a href="#provenance">Provenance</a></nav></header>
{epoch_html}
<section id="overview"><h2>XP accretion fit</h2><figure>{picture('overview','Fit summary, full spectrum, blue continuum, band residuals and joint posterior for positive accretion')}
<figcaption>The optical excess r is the ratio of accretion to photospheric flux density over 700–900 nm. Facc is the integrated model accretion flux (W m⁻²), and q is its ratio to the bolometric photospheric flux. The reported intervals include the probability of zero accretion. The corner plot shows the positive-accretion branch.</figcaption></figure></section>
{spectroscopy_section}
{photometry_section}
<section id="results"><h2>Fit results and diagnostics</h2><details><summary>Physical quantities and credible intervals</summary><p>The table gives the 16th, 50th, 84th and 95th percentiles. Facc, r and q include the zero-accretion branch. The 95th percentile gives a model-dependent upper limit.</p>
<div class="table-wrap"><table><thead><tr><th>Quantity</th><th>Unit</th><th>p16</th><th>p50</th><th>p84</th><th>p95</th><th>Definition</th></tr></thead><tbody>{''.join(rows)}</tbody></table></div>
<p>{esc(english_note(report['stellar_conversion']))}</p><p>Posterior weight of the zero-accretion branch P0={esc(_fmt(report['p_zero']))}. Log Bayes factor for positive versus zero accretion, ln BF={esc(_fmt(report['ln_bayes_factor']))}. Both depend on the adopted model and priors.</p></details>
<details id="spectrum"><summary>Continuum fit and residuals</summary><figure>{picture('spectrum','Observed and model spectra, blue continuum and residuals in the correlated bands')}
<figcaption>Fluxes are scaled to the observed mean over 700–900 nm. Gray shading shows the marginal 1σ measurement uncertainty. Blue shading spans the 16th–84th percentiles of the model. Component medians can sum to a value different from the median total flux. Adjacent band residuals are correlated.</figcaption></figure></details>
<details id="posterior"><summary>Joint posterior</summary><p>The plotted distribution is conditional on positive accretion. P0={esc(_fmt(report['p_zero']))} gives the posterior weight at zero.</p>
<figure>{picture('posterior','Joint posterior of spectral type, extinction, optical excess and accretion flux')}<figcaption>Diagonal panels show marginal distributions. Off-diagonal panels show correlations. Spectral type bins are centered on the saved grid nodes.</figcaption></figure></details></section>
<section id="reliability"><h2>Scientific interpretation</h2><p>The inferred accretion depends on the adopted photosphere, extinction law and continuum model. Blue-end calibration, template mismatch and priors limit its accuracy. The DR3 spectrum averages multiple transits. Independent calibration of the inferred accretion is still needed.</p>
<details><summary>Fit diagnostics and limitations</summary><p>Numerical integration {esc(report['numerical_status'])}. {esc(flags)}. {esc(english_note(report['prior_note']))}</p><div class="table-wrap"><table>{metrics}</table></div><ul>{limits}</ul></details></section>
<section id="provenance"><h2>Data and methods</h2><details><summary>XP calibration, priors and input files</summary><p>Fit method <code>{esc(report['method_id'])}</code>. Report version {esc(__version__)}.</p>
<p>The priors are centered on spectral type index {esc(meta['spt_num'])}, Av={esc(meta['av_mag'])} mag and Teff={esc(meta['teff_k'])} K. Rv={esc(cfg['rv'])} and Student-t degrees of freedom = {esc(cfg['degrees_of_freedom'])}. The run contract records the prior widths and template assumptions.</p>
<p><b>Calibration</b> {esc(english_note(meta['calibration_version']))}<br><b>Spectrum</b> {esc(english_note(meta['input_reference']))}<br><b>Priors</b> {esc(english_note(meta['prior_reference']))}</p>
<p class="notice">The summary, review, posterior and run contract match their original checksums. The checksums for the spectrum, prediction and status files identify the copies used to build this report.</p>
<div class="table-wrap"><table>{provenance_rows}</table></div></details></section>
<footer>Generated from the saved XP fit · {esc(provenance['created_utc'])}</footer>
</main></body></html>'''
    (destination/'report.html').write_text(html, encoding='utf-8')


def build_report(run, output, photometry=None, spectra=None, epochs=None):
    run, destination = Path(run).expanduser().resolve(), Path(output).expanduser().resolve()
    if destination.is_relative_to(run): raise ValueError('报告输出须位于原运行目录之外')
    report, contract, spectrum, prediction, posterior, hashes = load_saved(run)
    photo_data = photo_path = spec_data = spec_path = epoch_data = epoch_path = None
    if contract['metadata'].get('flux_unit') != 'W m-2 nm-1' or contract['metadata'].get('wavelength_unit') != 'nm':
        raise ValueError('光谱展示需要明确的XP单位：nm及W m-2 nm-1')
    if photometry is not None:
        from .photometry import load_photometry
        photo_path = Path(photometry).expanduser().resolve()
        if photo_path.is_dir(): photo_path = photo_path/'photometry.json'
        if destination.is_relative_to(photo_path.parent): raise ValueError('报告输出须位于测光目录之外')
        photo_data = load_photometry(photo_path, source_id=report['source_id'])
    if spectra is not None:
        from .spectroscopy import load_spectra
        spec_path = Path(spectra).expanduser().resolve()
        if spec_path.is_dir(): spec_path = spec_path/'spectroscopy.json'
        if destination.is_relative_to(spec_path.parent): raise ValueError('报告输出须位于光谱目录之外')
        spec_data = load_spectra(spec_path, source_id=report['source_id'])
    from .epoch_report import load_epoch_bundle, epoch_section, epoch_summary
    if epochs is not None:
        epoch_path = Path(epochs).expanduser().resolve()
        if epoch_path.is_dir(): epoch_path = epoch_path/'epochs.json'
        if destination.is_relative_to(epoch_path.parent): raise ValueError('报告输出须位于历元资料目录之外')
        epoch_data = load_epoch_bundle(epoch_path, source_id=report['source_id'])
    destination = new_directory(destination)
    provenance = dict(schema_version=1, report_version=__version__, source_id=report['source_id'],
                      created_utc=datetime.now(timezone.utc).isoformat(), input_run=str(run),
                      input_sha256=hashes, preexisting_hash_verified=list(VERIFIED_FILES),
                      snapshot_only=['status.json','spectrum.npz','prediction.npz'], fit_executed=False)
    if photo_path is not None:
        provenance['photometry'] = dict(path=str(photo_path), sha256=digest(photo_path))
    if spec_path is not None:
        provenance['spectroscopy'] = dict(path=str(spec_path), sha256=digest(spec_path))
    if epoch_path is not None:
        provenance['epochs'] = dict(path=str(epoch_path), sha256=digest(epoch_path), input_files=epoch_data['input_files'])
    try:
        from .report_plots import render_overview
        images = render_overview(destination, spectrum, prediction, posterior, report, contract)
        if photo_data is not None:
            from .photometry_report import render_photometry
            images['photometry'] = render_photometry(destination, spectrum, prediction, photo_data)
        comparison = None
        if spec_data is not None:
            from .spectroscopy_report import render_spectroscopy
            images['spectroscopy'], comparison = render_spectroscopy(destination, spectrum, prediction, spec_data)
            provenance['spectroscopy_comparison'] = comparison
        provenance['epoch_summary'] = epoch_summary(spectrum, spec_data, epoch_data)
        epoch_html = epoch_section(spectrum, spec_data, epoch_data)
        write_html(destination, report, contract, images, provenance, photo_data, spec_data, comparison, epoch_html)
        if any(digest(run/name) != sha for name,sha in hashes.items()):
            raise RuntimeError('报告期间输入运行发生变化，报告未标记为完成')
        if photo_path is not None and digest(photo_path) != provenance['photometry']['sha256']:
            raise RuntimeError('报告期间测光文件发生变化')
        if spec_path is not None and digest(spec_path) != provenance['spectroscopy']['sha256']:
            raise RuntimeError('报告期间档案光谱记录发生变化')
        if epoch_data is not None and any(digest(Path(path)) != sha for path,sha in epoch_data['input_files'].items()):
            raise RuntimeError('报告期间历元资料发生变化')
        provenance.update(status='complete', output_sha256={name:digest(destination/name) for name in [*images.values(),'report.html']})
    except Exception as error:
        provenance.update(status='failed', error=str(error))
        write_json(destination/'report_manifest.json', provenance)
        raise
    write_json(destination/'report_manifest.json', provenance)
    return dict(status='complete', source_id=report['source_id'], output=str(destination),
                overview=str(destination/'overview.png'), html=str(destination/'report.html'), fit_executed=False)
