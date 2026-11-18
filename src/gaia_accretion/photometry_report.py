"""把非同期测光与保存的XP光谱并列展示，不拟合或外推红外模型。"""
from html import escape

import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt


def xp_fnu_jy(wave_nm, flux_per_nm):
    """Fλ以W m⁻² nm⁻¹给出，按Fν=Fλ λ²/c换成Jy。"""
    return np.asarray(flux_per_nm) * np.asarray(wave_nm)**2 * 1e17 / 299792458.


def render_photometry(destination, spectrum, prediction, data):
    wave = spectrum['wave']
    mask = spectrum['mask']
    flux = xp_fnu_jy(wave, spectrum['flux'])
    error = xp_fnu_jy(wave, np.linalg.norm(spectrum['noise_factor'], axis=1))
    points = [p for p in data['measurements'] if p.get('flux_jy') is not None and p['flux_jy'] > 0]
    optical = any(p['wavelength_um'] < 1.02 for p in points)
    colors = {'2MASS':'#b56b29','AllWISE':'#9c4c85','APASS':'#31805e','SkyMapper':'#31805e'}
    styles = {'font.family':'DejaVu Sans','font.size':10,'axes.spines.top':False,
              'axes.spines.right':False,'savefig.facecolor':'white'}
    with plt.rc_context(styles):
        fig, axes = plt.subplots(1, 2 if optical else 1, figsize=(12.5,4.8), squeeze=False)
        for index, ax in enumerate(axes[0]):
            ax.plot(wave/1000, np.where(mask & (flux > 0), flux, np.nan), color='#737e88', lw=1, label='Gaia DR3 mean XP')
            low, high = flux-error, flux+error
            ax.fill_between(wave/1000, np.where(mask & (low>0),low,np.nan), np.where(mask & (high>0),high,np.nan),color='#c6cdd3',alpha=.5)
            ax.plot(wave/1000, xp_fnu_jy(wave,prediction['median']), color='#226e9b', lw=1.2,label='Saved XP model')
            seen=set()
            for point in points:
                x,y=point['wavelength_um'],point['flux_jy']
                if index and not .33 <= x <= 1.04: continue
                name=point['survey']; usable=point.get('usable',False)
                color=colors.get(name,'#31805e') if usable else '#888888'
                label=name if usable else name+' (flagged)'
                limit=point.get('is_upper_limit',False)
                err=y*.25 if limit else point.get('flux_error_jy')
                ax.errorbar(x,y,yerr=err,fmt='v' if limit else 'o',uplims=limit,
                            color=color,mfc=color if usable else 'white',ms=5,capsize=2,
                            label=label if label not in seen else None,zorder=5)
                seen.add(label)
                if not index and x>1.02: ax.annotate(point['band'],(x,y),xytext=(0,8),textcoords='offset points',ha='center',fontsize=8,color=color)
                if index: ax.annotate(point['band']+'′',(x,y),xytext=(4,8),textcoords='offset points',fontsize=9,color=color)
            ax.set_yscale('log'); ax.set_xlabel('Wavelength (μm)');ax.set_ylabel('Flux density Fν (Jy)')
            ax.grid(alpha=.15,which='both')
            if index:
                ax.set_xlim(.33,1.04); ax.set_title('Optical comparison')
                optical_flux=np.r_[flux[mask & (flux>0)], [p['flux_jy'] for p in points if p['wavelength_um']<1.04]]
                if optical_flux.size: ax.set_ylim(max(np.percentile(optical_flux,2)*.6,1e-10),optical_flux.max()*1.5)
            else:
                ax.set_xscale('log'); ax.set_title('Optical to infrared')
                ax.set_xlim(.30,max([1.1]+[p['wavelength_um']*1.35 for p in points]))
                ax.legend(fontsize=8,loc='best')
        fig.suptitle('Gaia DR3 '+data['source_id'],fontsize=12)
        fig.text(.5,.015,'Non-contemporaneous; observed fluxes, no extinction or colour correction. Open symbols: flagged photometry.',ha='center',fontsize=8,color='#526775')
        fig.tight_layout(rect=(0,.055,1,.96))
        fig.savefig(destination/'photometry.png',dpi=170)
        plt.close(fig)
    return 'photometry.png'


def photometry_html(data, picture):
    """主文只保留比较图和结论条件，星表明细按需展开。"""
    esc=lambda value:escape(str(value),quote=True)
    fmt=lambda value: '—' if value is None else f'{value:.4g}'
    points=data['measurements']
    usable=sum(bool(p.get('usable')) and not p.get('is_upper_limit') for p in points)
    limits=sum(bool(p.get('is_upper_limit')) for p in points)
    surveys=data['surveys']
    matched=[s['name'] for s in surveys if s.get('selected_id')]
    brief=('、'.join(matched)+' 有位置匹配。') if matched else '尚无可采用的位置匹配。'
    brief+=f' 共 {len(points)} 个波段，其中 {usable} 个通过所列质量筛选、{limits} 个为通量上限。'
    flagged=[p['survey']+' '+p['band'] for p in points if not p.get('usable') and not p.get('is_upper_limit')]
    if flagged: brief+=' '+ '、'.join(flagged)+' 有质量问题，图中仅作参考。'
    status_names={'matched':'唯一位置候选','ambiguous':'多个候选，未采用','no_match':'范围内无匹配','query_failed':'查询失败'}
    unavailable=[s['name']+'（'+status_names.get(s.get('status'),s.get('status','未知'))+'）' for s in surveys if not s.get('selected_id')]
    if unavailable: brief+=' '+ '、'.join(unavailable)+'。'
    rows=[]
    for p in points:
        mark='上限' if p.get('is_upper_limit') else ('可用' if p.get('usable') else '需检查')
        quality=('误差旗标 ' if p['survey'].startswith('APASS') else '等级 ')+str(p.get('quality','—'))
        if p.get('error_note') and p['survey'].startswith('APASS'): quality+='；'+p['error_note']
        if p.get('quality_notes'): quality+='；'+'；'.join(p['quality_notes'])
        if p.get('upper_limit_note'): quality+='；'+p['upper_limit_note']
        rows.append('<tr>'+''.join(f'<td>{esc(v)}</td>' for v in [p['survey'],p['band'],fmt(p['wavelength_um']),
                    fmt(p.get('mag')),fmt(p.get('mag_error')),p.get('system',''),fmt(p.get('flux_jy')),
                    fmt(p.get('flux_error_jy')),mark,quality])+'</tr>')
    match_rows=[]
    for s in surveys:
        candidates=s.get('candidates',[])
        selected=next((c for c in candidates if c.get('object_id')==s.get('selected_id')), {})
        epoch=selected.get('epoch_year',s.get('epoch_year'))
        epoch_label='未提供' if epoch is None else (f'约 {epoch:.1f}（采用）' if s['name']=='AllWISE' else f'{epoch:.3f}')
        match_rows.append('<tr>'+''.join(f'<td>{esc(v)}</td>' for v in [s['name'],s['catalogue'],s.get('selected_id') or '—',
                      fmt(s.get('separation_arcsec')),len(candidates),epoch_label,
                      s.get('radius_arcsec','—'),status_names.get(s.get('status'),s.get('status','—'))])+'</tr>')
    sources=[]
    for s in surveys:
        cat=s['catalogue']
        sources.append(f'<a href="https://vizier.cds.unistra.fr/viz-bin/VizieR?-source={esc(cat)}">{esc(s["name"])} ({esc(cat)})</a>')
    target=data['target']
    dates=sorted({p['retrieved_utc'][:10] for p in data.get('provenance',[]) if p.get('retrieved_utc')})
    retrieval='、'.join(dates) or '见测光目录'
    return f'''<section id="photometry"><h2>多波段测光</h2><p>{esc(brief)}</p>
<figure>{picture('photometry','巡天测光与Gaia平均XP的通量密度比较')}<figcaption>实心点通过筛选，空心点需检查，上限用向下箭头。灰线为 XP，蓝线为已有拟合；阴影为 XP 逐点 1σ。误差沿用目录定义，APASS 的观测散布不等于均值误差。宽带点放在代表波长，不是单色测量或合成测光；对数轴只显示正通量。</figcaption></figure>
<p>测光与 Gaia 并非同期，均未作消光或颜色改正。差异可能来自变光、混叠或标定，APASS 较大口径尤其需注意混叠；红外辐射还可能来自盘，不能据此校准吸积率。</p>
<details><summary>交叉匹配与测光表</summary><p>Gaia DR3：RA={target['ra_deg']:.8f}°，Dec={target['dec_deg']:.8f}°；位置历元 {esc(target['epoch_year'])}。有历元与自行时先修正位置；APASS 未提供逐源历元，采用 Gaia 位置。唯一位置候选不等于已排除混叠。</p>
<div class="table-wrap"><table><thead><tr><th>巡天</th><th>VizieR 表</th><th>匹配源</th><th>角距 (″)</th><th>候选数</th><th>匹配历元</th><th>搜索半径 (″)</th><th>匹配状态</th></tr></thead><tbody>{''.join(match_rows)}</tbody></table></div>
<div class="table-wrap"><table><thead><tr><th>巡天</th><th>波段</th><th>λ (μm)</th><th>星等</th><th>σm</th><th>系统</th><th>Fν (Jy)</th><th>σFν (Jy)</th><th>采用情况</th><th>质量与注意事项</th></tr></thead><tbody>{''.join(rows)}</tbody></table></div>
<p>来源：{'；'.join(sources)}。获取日期（UTC）：{esc(retrieval)}。原始星表、字段单位、全部候选与换算零点均保存在测光目录。</p></details></section>'''
