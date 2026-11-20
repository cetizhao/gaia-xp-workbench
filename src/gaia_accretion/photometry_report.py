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
        fig.text(.5,.015,'Observed flux densities at different epochs, without extinction or colour corrections. Open symbols mark flagged photometry.',ha='center',fontsize=8,color='#526775')
        fig.tight_layout(rect=(0,.055,1,.96))
        fig.savefig(destination/'photometry.png',dpi=170)
        plt.close(fig)
    return 'photometry.png'


# 历史测光数据保留原文；仅在报告中转换工作台生成的质量说明。
_NOTE_TRANSLATIONS = {
    '测光质量非 A/B/C 或上限 U': 'Photometric quality outside accepted grades A/B/C or upper limit U',
    '存在伪像或混叠旗标': 'Artifact or confusion flag',
    '扩展源污染或太阳系天体旗标': 'Possible extended-source contamination or Solar System object',
    '可能为扩展源': 'Possible extended source',
    '含饱和像素': 'Saturated pixels',
    '目录误差类型旗标缺失': 'Missing uncertainty flag',
    '无有效星等': 'Magnitude unavailable',
    '无有效星等误差': 'Magnitude uncertainty unavailable',
    '多次观测的标准差，不是均值标准误': 'Standard deviation of repeated observations',
    '单次观测的 Poisson 误差': 'Single-observation Poisson uncertainty',
    '目录星等误差；未额外传播零点或颜色改正误差': 'Catalogue uncertainty excludes zero-point and colour-correction uncertainties',
    '保留目录上限；CDS 表说明与 2MASS FAQ 对置信度分别写 95% 和 97%，此处不指定统一数值':
        'Catalogue upper limit. CDS quotes 95% confidence and the 2MASS FAQ quotes 97%.',
}


def _quality_note(note):
    prefix = 'WISE 伪像污染旗标 '
    if note.startswith(prefix):
        return 'WISE artifact flag ' + note[len(prefix):]
    return _NOTE_TRANSLATIONS.get(note, note)


def photometry_html(data, picture):
    """主文只保留比较图和结论条件，星表明细按需展开。"""
    esc=lambda value:escape(str(value),quote=True)
    fmt=lambda value: '—' if value is None else f'{value:.4g}'
    points=data['measurements']
    usable=sum(bool(p.get('usable')) and not p.get('is_upper_limit') for p in points)
    limits=sum(bool(p.get('is_upper_limit')) for p in points)
    surveys=data['surveys']
    matched=[s['name'] for s in surveys if s.get('selected_id')]
    brief = ('Positional matches in ' + ', '.join(matched) + '. ') if matched else 'No positional counterpart selected. '
    brief += f'{usable} of {len(points)} bands have detections that pass the quality cuts.'
    if limits:
        brief += f' Upper limits are reported in {limits} band(s).'
    flagged=[p['survey']+' '+p['band'] for p in points if not p.get('usable') and not p.get('is_upper_limit')]
    if flagged:
        brief += ' Flagged bands include ' + ', '.join(flagged) + '.'
    status_names = {'matched':'Unique positional match', 'ambiguous':'Multiple candidates',
                    'no_match':'No match in search radius', 'query_failed':'Query failed'}
    unavailable=[s['name']+' ('+status_names.get(s.get('status'),'Unknown status')+')' for s in surveys if not s.get('selected_id')]
    if unavailable:
        brief += ' ' + ', '.join(unavailable) + '.'
    rows=[]
    for p in points:
        mark='Upper limit' if p.get('is_upper_limit') else ('Accepted' if p.get('usable') else 'Flagged')
        notes = [('Error flag ' if p['survey'].startswith('APASS') else 'Grade ') + str(p.get('quality','—'))]
        if p.get('error_note') and p['survey'].startswith('APASS'):
            notes.append(_quality_note(p['error_note']))
        notes.extend(_quality_note(note) for note in p.get('quality_notes', []))
        if p.get('upper_limit_note'):
            notes.append(_quality_note(p['upper_limit_note']))
        rows.append('<tr>'+''.join(f'<td>{esc(v)}</td>' for v in [p['survey'],p['band'],fmt(p['wavelength_um']),
                    fmt(p.get('mag')),fmt(p.get('mag_error')),p.get('system',''),fmt(p.get('flux_jy')),
                    fmt(p.get('flux_error_jy')),mark,' · '.join(notes)])+'</tr>')
    match_rows=[]
    for s in surveys:
        candidates=s.get('candidates',[])
        selected=next((c for c in candidates if c.get('object_id')==s.get('selected_id')), {})
        epoch=selected.get('epoch_year',s.get('epoch_year'))
        epoch_label='Unavailable' if epoch is None else (f'~{epoch:.1f} (adopted)' if s['name']=='AllWISE' else f'{epoch:.3f}')
        match_rows.append('<tr>'+''.join(f'<td>{esc(v)}</td>' for v in [s['name'],s['catalogue'],s.get('selected_id') or '—',
                      fmt(s.get('separation_arcsec')),len(candidates),epoch_label,
                      s.get('radius_arcsec','—'),status_names.get(s.get('status'),'Unknown status')])+'</tr>')
    sources=[]
    for s in surveys:
        cat=s['catalogue']
        sources.append(f'<a href="https://vizier.cds.unistra.fr/viz-bin/VizieR?-source={esc(cat)}">{esc(s["name"])} ({esc(cat)})</a>')
    target=data['target']
    dates=sorted({p['retrieved_utc'][:10] for p in data.get('provenance',[]) if p.get('retrieved_utc')})
    retrieval=', '.join(dates) or 'see photometry records'
    return f'''<section id="photometry"><h2>Broadband photometry</h2><p>{esc(brief)}</p>
<figure>{picture('photometry','Broadband photometry and the Gaia mean XP spectrum in flux density units')}<figcaption>Filled symbols mark accepted detections, open symbols mark flagged measurements and downward arrows show upper limits. The grey curve is the mean XP spectrum with its pointwise 1σ uncertainty. Blue shows the fitted spectrum. Broadband measurements appear at representative wavelengths. The logarithmic axes show positive flux densities.</figcaption></figure>
<p>These surveys observed the source at different times. Variability, blending (particularly in the large APASS aperture), calibration and infrared emission from a disc can affect this comparison. Fluxes are shown before extinction and colour corrections.</p>
<details><summary>Catalogue matches and photometry</summary><p>Gaia DR3 position at epoch {esc(target['epoch_year'])}: RA {target['ra_deg']:.8f}°, Dec {target['dec_deg']:.8f}°. Matches use proper motions where the survey epoch is available. APASS uses the Gaia position because individual epochs are unavailable. Blending remains possible even for a unique match.</p>
<div class="table-wrap"><table><thead><tr><th>Survey</th><th>VizieR table</th><th>Counterpart</th><th>Separation (″)</th><th>Candidates</th><th>Match epoch</th><th>Search radius (″)</th><th>Match status</th></tr></thead><tbody>{''.join(match_rows)}</tbody></table></div>
<div class="table-wrap"><table><thead><tr><th>Survey</th><th>Band</th><th>λ (μm)</th><th>Magnitude</th><th>σm</th><th>System</th><th>Fν (Jy)</th><th>σFν (Jy)</th><th>Use</th><th>Quality notes</th></tr></thead><tbody>{''.join(rows)}</tbody></table></div>
<p>Catalogue tables: {', '.join(sources)}. Retrieval date (UTC): {esc(retrieval)}. The photometry records include the original tables, field units, all candidates and flux zero points.</p></details></section>'''
