"""已有XP与档案光谱的观测比较，不拟合、不调整观测通量尺度。"""
from html import escape
from collections import Counter
from datetime import datetime, timedelta

import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt


def _observation_label(product):
    """图例保留每条谱的观测时间与时标，不作未核验的时间转换。"""
    observed=str(product.get('obs_time') or 'Observation time not provided').replace('T',' ',1)
    scale=str(product.get('time_scale') or 'time scale not provided').split('（',1)[0]
    return f"{product['instrument']} {product.get('arm','')} {product['role']} slit\n{observed} {scale}"


def bin_mean_flux(wave, flux, mask, edges):
    """逐段积分得到等宽波段平均通量；不跨越缺测区或外推。"""
    wave,flux,mask=np.asarray(wave),np.asarray(flux),np.asarray(mask,dtype=bool)
    valid=mask & np.isfinite(wave) & np.isfinite(flux)
    x,y=wave[valid],flux[valid]
    result=np.full(len(edges)-1,np.nan)
    if len(x)<2:return result
    step=np.median(np.diff(wave))
    for i,(lo,hi) in enumerate(zip(edges[:-1],edges[1:])):
        left=np.searchsorted(x,lo,side='right')-1
        right=np.searchsorted(x,hi,side='left')
        if left<0 or right>=len(x):continue
        xs,ys=x[left:right+1],y[left:right+1]
        if len(xs)<2 or np.max(np.diff(xs))>4*step:continue
        inner=(xs>lo)&(xs<hi)
        xx=np.r_[lo,xs[inner],hi]
        yy=np.interp(xx,xs,ys)
        result[i]=np.trapezoid(yy,xx)/(hi-lo)
    return result


def render_spectroscopy(destination, spectrum, prediction, data):
    products=data['products']
    wide=[p for p in products if p.get('role')=='wide']
    narrow=[p for p in products if p.get('role')=='narrow' and str(p.get('arm')).upper()=='VIS']
    edges=np.arange(335.,1025.,5.);centers=(edges[1:]+edges[:-1])/2
    scale=1e-15
    colors={'UVB':'#b36d2e','VIS':'#7b5794','NIR':'#58885d'}
    curves=[]
    for product in wide:
        arrays=product['arrays']
        values=bin_mean_flux(arrays['wave_nm'],arrays['flux_w_m2_nm'],arrays['mask'],edges)
        curves.append((product,values))
    xp_bins=bin_mean_flux(spectrum['wave'],spectrum['flux'],spectrum['mask'],edges)
    ratios=[]
    for p,values in curves:
        red=(centers>=700)&(centers<=900)&np.isfinite(values)&np.isfinite(xp_bins)
        if red.sum()>=20 and np.mean(xp_bins[red])>0:
            ratios.append(dict(product_id=p['product_id'],obs_time=p['obs_time'],
                band_nm=[700,900],common_bins=int(red.sum()),ratio=float(np.mean(values[red])/np.mean(xp_bins[red]))))
    # 显示分箱独立于通量比积分：加密曲线不改变已保存的比较量。
    display={}
    for name,lo,hi,step in (('full',335.,1020.,.5),('blue',336.,480.,.2)):
        display_edges=np.linspace(lo,hi,round((hi-lo)/step)+1)
        display_centers=(display_edges[:-1]+display_edges[1:])/2
        display_curves=[]
        for p in wide:
            a=p['arrays']
            values=bin_mean_flux(a['wave_nm'],a['flux_w_m2_nm'],a['mask'],display_edges)
            display_curves.append((p,values))
        display[name]=(display_centers,display_curves)
    styles={'font.family':'DejaVu Sans','font.size':10,'axes.spines.top':False,'axes.spines.right':False,'savefig.facecolor':'white'}
    with plt.rc_context(styles):
        fig=plt.figure(figsize=(13,8))
        grid=fig.add_gridspec(2,2,height_ratios=[1.1,1],hspace=.42,wspace=.25)
        full=fig.add_subplot(grid[0,:]);blue=fig.add_subplot(grid[1,0]);line=fig.add_subplot(grid[1,1])
        for ax,name,lo,hi in ((full,'full',335,1020),(blue,'blue',336,480)):
            ax.plot(spectrum['wave'],np.where(spectrum['mask'],spectrum['flux']/scale,np.nan),color='#68747d',lw=1,label='Gaia DR3 mean XP\nmulti-epoch average')
            ax.plot(spectrum['wave'],prediction['median']/scale,color='#226e9b',lw=1.2,label='Saved fit to DR3 mean XP')
            display_centers,display_curves=display[name]
            for p,values in display_curves:
                color=colors.get(str(p.get('arm')).upper(),'#b36d2e')
                ax.plot(display_centers,values/scale,color=color,lw=.9,label=_observation_label(p))
            ax.set(xlim=(lo,hi),xlabel='Wavelength (nm)',ylabel='Fλ (10⁻¹⁵ W m⁻² nm⁻¹)')
            ax.grid(alpha=.15)
        full.set_title('Absolute flux comparison · archive spectra in 0.5 nm display bands',loc='left',fontsize=11)
        full.legend(fontsize=9,ncol=2)
        blue.set_title('Blue spectrum · 0.2 nm display bands',loc='left',fontsize=11)
        values=np.r_[spectrum['flux'][(spectrum['wave']>=336)&(spectrum['wave']<=480)&spectrum['mask']]/scale,
                     *[v/scale for _,v in display['blue'][1]]]
        values=values[np.isfinite(values)]
        if len(values):blue.set_ylim(min(0,float(values.min()))-.04*max(float(np.ptp(values)),1e-3),float(values.max())*1.08)
        blue.axvline(364.6,color='#98a2aa',ls=':',lw=.8)
        blue.text(364.6,.95,' Balmer edge',transform=blue.get_xaxis_transform(),fontsize=8,va='top',color='#637381')
        for p in narrow:
            a=p['arrays'];chosen=(a['wave_nm']>=654)&(a['wave_nm']<=659)&a['mask']
            line.plot(a['wave_nm'][chosen],a['flux_w_m2_nm'][chosen]/scale,color='#7b5794',lw=.8,label=_observation_label(p))
        if narrow:
            line.legend(fontsize=8)
        else:
            line.text(.5,.5,'No selected narrow-slit VIS spectrum',transform=line.transAxes,ha='center')
        line.axvline(656.28,color='#98a2aa',ls=':',lw=.8)
        line.set(xlim=(654,659),xlabel='Air wavelength (nm; observed frame)',ylabel='Fλ (10⁻¹⁵ W m⁻² nm⁻¹)')
        line.set_title('Hα · original archive resolution',loc='left',fontsize=11);line.grid(alpha=.15)
        fig.suptitle('Gaia DR3 '+data['source_id']+' · archival spectroscopy',fontsize=14)
        fig.text(.5,.025,'Display band widths do not denote instrumental resolution. No rescaling, Gaia-response convolution or XP refit.',ha='center',fontsize=9,color='#526775')
        fig.subplots_adjust(left=.085,right=.98,bottom=.11,top=.90)
        fig.savefig(destination/'spectroscopy.png',dpi=170);plt.close(fig)
    return 'spectroscopy.png',dict(red_flux_ratios=ratios,bin_width_nm=5.,ratio_bin_width_nm=5.,
        display_bin_width_nm=dict(full=.5,blue=.2),flux_rescaled=False,xp_refitted=False)


def spectroscopy_html(data, comparison, picture):
    esc = lambda value: escape(str(value), quote=True)
    rows = []
    for p in data['products']:
        resolution = p.get('resolving_power')
        role = {'wide': 'Wide slit (continuum)', 'narrow': 'Narrow slit (line profiles)'}.get(p.get('role'), 'Unspecified')
        time_scale = str(p.get('time_scale') or 'time scale unavailable').split('（',1)[0]
        values = [p['instrument']+' '+str(p.get('arm','')),p['obs_time']+' '+time_scale,role,
                  p.get('slit_width_arcsec','—'),'—' if resolution is None else f'{resolution:.0f}',
                  f"{p['match_separation_arcsec']:.2f}"]
        rows.append('<tr>'+''.join(f'<td>{esc(v)}</td>' for v in values)+'</tr>')
    ratios = comparison.get('red_flux_ratios',[])
    ratio_text = ''
    if len(ratios) == 1:
        ratio_text = f" In the common 700–900 nm bins, the mean wide-slit flux density is {ratios[0]['ratio']:.2f} times the XP value."
    instruments = ', '.join(dict.fromkeys(p['instrument'] for p in data['products']))
    counts = Counter(c['instrument'] for c in data.get('candidates',[]))
    discovery_text = 'The ESO search returned ' + ', '.join(f'{v} {k}' for k,v in counts.items()) + ' products. ' if counts else ''
    for archive in data.get('archives',[]):
        if archive['name']=='MAST':
            discovery_text += ('The MAST search returned no spectra within the search radius.' if archive.get('status')=='complete' and archive.get('spectra')==0
                               else 'MAST query status: '+str(archive.get('status','unavailable'))+'.')
    available_rows = []
    for instrument,count in counts.items():
        group = [c for c in data['candidates'] if c['instrument']==instrument]
        dates = [(datetime(1858,11,17)+timedelta(days=c['mjd_start'])).date().isoformat() for c in group]
        resolutions = [c['resolving_power'] for c in group if c.get('resolving_power')]
        span = min(dates) if min(dates)==max(dates) else min(dates)+' to '+max(dates)
        r = '—' if not resolutions else f'{min(resolutions):.0f}'
        if resolutions and max(resolutions) != min(resolutions):
            r += f'–{max(resolutions):.0f}'
        available_rows.append('<tr>'+''.join(f'<td>{esc(v)}</td>' for v in [instrument,count,span,r])+'</tr>')
    product_rows = []
    for p in data['products']:
        units = p.get('original_units','—')
        if isinstance(units,dict):
            flux_unit=units['flux'].replace('erg.cm**(-2).s**(-1).angstrom**(-1)','erg s⁻¹ cm⁻² Å⁻¹')
            units=f"λ ({units['wavelength']}), Fλ ({flux_unit})"
        calibration = 'Absolute' if p.get('flux_calibration')=='ABSOLUTE' else p.get('flux_calibration','Unavailable')
        if p.get('flux_scale_error_percent') is not None and p['flux_scale_error_percent']<0:
            calibration += ' (scale uncertainty unavailable)'
        values=[p['product_id'],units,calibration,p.get('wavelength_medium','Unavailable'),
                {'TOPOCENT':'Topocentric'}.get(p.get('spectral_frame'),p.get('spectral_frame','Unavailable'))]
        product_rows.append('<tr>'+''.join(f'<td>{esc(v)}</td>' for v in values)+'</tr>')
    return f'''<section id="spectroscopy"><h2>Archival spectroscopy</h2><p>The comparison uses {len(data['products'])} optical spectra from {esc(instruments)}.{esc(ratio_text)} The wide slit measures the continuum. The narrow slit resolves line profiles.</p>
<figure>{picture('spectroscopy','Archival spectra and mean Gaia XP in the full optical range, the blue continuum and Hα')}<figcaption>Legends give the exposure start and time scale. The Gaia DR3 XP spectrum averages multiple epochs. Wide-slit spectra are displayed in 0.5 nm bins in the full view and 0.2 nm bins in the blue. The red flux ratio uses 5 nm bins. Spectra retain their observed flux scales and instrumental responses. The Hα panel uses the native narrow-slit resolution. Its dotted line marks the rest wavelength in air, before any stellar velocity correction.</figcaption></figure>
<div class="table-wrap"><table><thead><tr><th>Instrument and arm</th><th>Exposure start and time scale</th><th>Spectrum</th><th>Slit width (″)</th><th>Nominal R = λ/Δλ</th><th>Separation (″)</th></tr></thead><tbody>{''.join(rows)}</tbody></table></div>
<p>These spectra test the XP continuum shape and flux scale and reveal emission lines. Different observing epochs, narrow-slit losses, absolute calibration uncertainty and telluric absorption limit any inference about accretion variability.</p>
<details><summary>Archive coverage, matching and calibration</summary><p>{esc(discovery_text)}</p>
<div class="table-wrap"><table><thead><tr><th>Instrument</th><th>Candidate products</th><th>Observation dates</th><th>Nominal R</th></tr></thead><tbody>{''.join(available_rows)}</tbody></table></div>
<p>Archive pointings are compared with the Gaia position propagated to the observation epoch. Companions may contribute flux. Resolving powers are nominal arc-lamp values. The spectra retain their wavelength medium and velocity frame, so the overlay supports broad spectral comparisons. For ESO exposures, DATE-OBS gives the start time and UTC follows the ESO convention where TIMESYS is absent.</p>
<div class="table-wrap"><table><thead><tr><th>Archive product</th><th>Original units</th><th>Flux calibration</th><th>Wavelength medium</th><th>Velocity frame</th></tr></thead><tbody>{''.join(product_rows)}</tbody></table></div>
<p>The spectroscopy records include the original FITS files, all candidates, product links and unit conversions. <a href="https://archive.eso.org/tap_obs">ESO Science Archive</a></p></details></section>'''
