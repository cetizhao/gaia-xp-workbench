"""已有XP与档案光谱的观测比较，不拟合、不调整观测通量尺度。"""
from html import escape
from collections import Counter
from datetime import datetime, timedelta

import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt


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
    styles={'font.family':'DejaVu Sans','font.size':10,'axes.spines.top':False,'axes.spines.right':False,'savefig.facecolor':'white'}
    with plt.rc_context(styles):
        fig=plt.figure(figsize=(13,8))
        grid=fig.add_gridspec(2,2,height_ratios=[1.1,1],hspace=.42,wspace=.25)
        full=fig.add_subplot(grid[0,:]);blue=fig.add_subplot(grid[1,0]);line=fig.add_subplot(grid[1,1])
        for ax,lo,hi in ((full,335,1020),(blue,336,480)):
            ax.plot(spectrum['wave'],np.where(spectrum['mask'],spectrum['flux']/scale,np.nan),color='#68747d',lw=1,label='Gaia DR3 mean XP')
            ax.plot(spectrum['wave'],prediction['median']/scale,color='#226e9b',lw=1.2,label='Saved XP model')
            for p,values in curves:
                color=colors.get(str(p.get('arm')).upper(),'#b36d2e')
                ax.plot(centers,values/scale,color=color,lw=1.3,label=f"{p['instrument']} {p['arm']} wide slit")
            ax.set(xlim=(lo,hi),xlabel='Wavelength (nm)',ylabel='Fλ (10⁻¹⁵ W m⁻² nm⁻¹)')
            ax.grid(alpha=.15)
        full.set_title('Absolute flux comparison · archive spectra averaged in 5 nm bands',loc='left',fontsize=11)
        full.legend(fontsize=9,ncol=2)
        blue.set_title('Blue continuum',loc='left',fontsize=11)
        values=np.r_[spectrum['flux'][(spectrum['wave']>=336)&(spectrum['wave']<=480)&spectrum['mask']]/scale,
                     *[v[(centers>=336)&(centers<=480)]/scale for _,v in curves]]
        values=values[np.isfinite(values)]
        if len(values):blue.set_ylim(min(0,float(values.min()))-.04*max(float(np.ptp(values)),1e-3),float(values.max())*1.08)
        blue.axvline(364.6,color='#98a2aa',ls=':',lw=.8)
        blue.text(364.6,.95,' Balmer edge',transform=blue.get_xaxis_transform(),fontsize=8,va='top',color='#637381')
        for p in narrow:
            a=p['arrays'];chosen=(a['wave_nm']>=654)&(a['wave_nm']<=659)&a['mask']
            line.plot(a['wave_nm'][chosen],a['flux_w_m2_nm'][chosen]/scale,color='#7b5794',lw=.8,label=f"{p['instrument']} narrow slit")
        if narrow:
            line.legend(fontsize=8)
        else:
            line.text(.5,.5,'No selected narrow-slit VIS spectrum',transform=line.transAxes,ha='center')
        line.axvline(656.28,color='#98a2aa',ls=':',lw=.8)
        line.set(xlim=(654,659),xlabel='Air wavelength (nm; observed frame)',ylabel='Fλ (10⁻¹⁵ W m⁻² nm⁻¹)')
        line.set_title('Hα · original archive resolution',loc='left',fontsize=11);line.grid(alpha=.15)
        fig.suptitle('Gaia DR3 '+data['source_id']+' · archival spectroscopy',fontsize=14)
        fig.text(.5,.025,'No rescaling or XP refit. 5 nm averaging is for display, not a simulation of the Gaia spectral response.',ha='center',fontsize=9,color='#526775')
        fig.subplots_adjust(left=.085,right=.98,bottom=.11,top=.90)
        fig.savefig(destination/'spectroscopy.png',dpi=170);plt.close(fig)
    return 'spectroscopy.png',dict(red_flux_ratios=ratios,bin_width_nm=5.,flux_rescaled=False,xp_refitted=False)


def spectroscopy_html(data, comparison, picture):
    esc=lambda value:escape(str(value),quote=True)
    rows=[]
    for p in data['products']:
        resolution=p.get('resolving_power')
        role='宽缝：连续谱' if p.get('role')=='wide' else '窄缝：谱线'
        values=[p['instrument']+' '+str(p.get('arm','')),p['obs_time'],role,
                p.get('slit_width_arcsec','—'),'未提供' if resolution is None else f'{resolution:.0f}',
                f"{p['match_separation_arcsec']:.2f}"]
        rows.append('<tr>'+''.join(f'<td>{esc(v)}</td>' for v in values)+'</tr>')
    ratios=comparison.get('red_flux_ratios',[])
    ratio_text=''
    if len(ratios)==1:
        ratio_text=f"宽缝光谱在共同有效的 700–900 nm 波段平均通量为 XP 的 {ratios[0]['ratio']:.2f} 倍。"
    instruments='、'.join(dict.fromkeys(p['instrument'] for p in data['products']))
    counts=Counter(c['instrument'] for c in data.get('candidates',[]))
    discovery_text='ESO 查询到'+ '、'.join(f'{k} {v} 个产品' for k,v in counts.items())+'。' if counts else ''
    for archive in data.get('archives',[]):
        if archive['name']=='MAST':
            discovery_text+=('MAST 本次小范围查询未返回光谱。' if archive.get('status')=='complete' and archive.get('spectra')==0
                             else 'MAST 查询状态：'+str(archive.get('status'))+'。')
    available_rows=[]
    for instrument,count in counts.items():
        group=[c for c in data['candidates'] if c['instrument']==instrument]
        dates=[(datetime(1858,11,17)+timedelta(days=c['mjd_start'])).date().isoformat() for c in group]
        resolutions=[c['resolving_power'] for c in group if c.get('resolving_power')]
        span=min(dates)+' 至 '+max(dates)
        r='未提供' if not resolutions else f'{min(resolutions):.0f}–{max(resolutions):.0f}'
        available_rows.append('<tr>'+''.join(f'<td>{esc(v)}</td>' for v in [instrument,count,span,r])+'</tr>')
    product_rows=[]
    for p in data['products']:
        units=p.get('original_units','—')
        if isinstance(units,dict):
            flux_unit=units['flux'].replace('erg.cm**(-2).s**(-1).angstrom**(-1)','erg s⁻¹ cm⁻² Å⁻¹')
            units='λ：'+units['wavelength']+'；Fλ：'+flux_unit
        calibration='绝对' if p.get('flux_calibration')=='ABSOLUTE' else p.get('flux_calibration','未提供')
        if p.get('flux_scale_error_percent') is not None and p['flux_scale_error_percent']<0: calibration+='（误差未定量）'
        values=[p['product_id'],units,calibration,{'air':'空气'}.get(p.get('wavelength_medium'),p.get('wavelength_medium','未提供')),
                {'TOPOCENT':'地面观测者'}.get(p.get('spectral_frame'),p.get('spectral_frame','未提供'))]
        product_rows.append('<tr>'+''.join(f'<td>{esc(v)}</td>' for v in values)+'</tr>')
    return f'''<section id="spectroscopy"><h2>档案光谱对照</h2><p>采用 {esc(instruments)} 的 {len(data['products'])} 个光学产品。{esc(ratio_text)}宽缝谱比较连续谱，窄缝谱保留谱线形状。</p>
<figure>{picture('spectroscopy','档案光谱与XP的绝对通量、蓝端和Hα比较')}<figcaption>上图及左下图将档案谱按 5 nm 波段取平均，仅便于比较谱形，并未模拟 Gaia 响应或重新归一化。右下图保留窄缝原分辨率；虚线为 Hα 空气静止波长，未作恒星速度改正。各图通量均为 W m⁻² nm⁻¹。</figcaption></figure>
<div class="table-wrap"><table><thead><tr><th>仪器／臂</th><th>观测时间（UTC）</th><th>用途</th><th>缝宽（″）</th><th>名义 R=λ/Δλ</th><th>位置角距（″）</th></tr></thead><tbody>{''.join(rows)}</tbody></table></div>
<p>这些观测可检查 XP 的连续谱形、通量尺度和发射线背景。它们与 Gaia 平均谱并非同期；窄缝损失、未定量的绝对标定误差和未改正的大气吸收仍影响比较，不能据此单独验证吸积光度或将通量差认定为吸积变化。</p>
<details><summary>可用档案、匹配与标定说明</summary><p>{esc(discovery_text)}</p>
<div class="table-wrap"><table><thead><tr><th>候选仪器</th><th>产品数</th><th>观测日期</th><th>档案名义 R</th></tr></thead><tbody>{''.join(available_rows)}</tbody></table></div>
<p>按 Gaia 位置与档案指向交叉匹配，并保留观测历元和自行比较；同一指向不能排除伴星混叠。R 取档案给出的弧灯名义值，不代表逐波长实测分辨率。原谱为地面观测者参考系的空气波长；宽带比较未作空气／真空或速度转换，不用于逐点窄线差或测速。时间采用 ESO DATE-OBS 的 UTC 约定。</p>
<div class="table-wrap"><table><thead><tr><th>档案产品</th><th>原单位</th><th>通量标定</th><th>波长介质</th><th>参考系</th></tr></thead><tbody>{''.join(product_rows)}</tbody></table></div>
<p>来源：<a href="https://archive.eso.org/tap_obs">ESO 科学档案</a>。原 FITS、查询候选、产品链接和单位换算均保存在光谱目录。</p></details></section>'''
