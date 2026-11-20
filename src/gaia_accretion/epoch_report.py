"""已保存的逐次光谱交互展示；不下载、不校准，也不拟合。"""
from __future__ import annotations

import json
from datetime import datetime
from html import escape
from pathlib import Path

import numpy as np

from .classical.xp_workbench import digest, exact_id, read_json


def _arrays(arrays):
    wave = np.asarray(arrays['wave_nm'])
    flux = np.asarray(arrays['flux_w_m2_nm'])
    mask = np.asarray(arrays['mask'])
    if (wave.ndim != 1 or len(wave) < 2 or flux.shape != wave.shape or mask.shape != wave.shape
            or mask.dtype != bool or not mask.any() or not np.isfinite(wave).all()
            or not np.all(np.diff(wave) > 0) or wave[0] <= 0 or not np.isfinite(flux[mask]).all()):
        raise ValueError('历元光谱的波长、通量或掩码无效')
    return dict(wave_nm=wave, flux_w_m2_nm=flux, mask=mask)


def load_epoch_bundle(path, source_id):
    """读取经过独立校准的展示输入；此格式不是 Gaia 官方产品适配器。"""
    path = Path(path).expanduser().resolve()
    if path.is_dir():
        path = path/'epochs.json'
    data = read_json(path)
    if not isinstance(data.get('source_id'), str) or exact_id(data['source_id']) != exact_id(source_id):
        raise ValueError('历元光谱与 XP 源编号不一致，编号须为精确字符串')
    if data.get('schema_version') != 1 or data.get('wavelength_unit') != 'nm' or data.get('flux_unit') != 'W m-2 nm-1':
        raise ValueError('历元展示格式要求 schema_version=1，波长 nm，绝对通量 W m-2 nm-1')
    if not isinstance(data.get('records'), list):
        raise ValueError('历元展示输入缺少 records')
    result = dict(data, records=[], input_files={str(path): digest(path)})
    identities = set()
    for saved in data['records']:
        row = dict(saved)
        for field in ('epoch_id', 'group_id', 'instrument', 'calibration_reference'):
            if not isinstance(row.get(field), str) or not row[field].strip():
                raise ValueError('历元记录缺少 '+field)
        if row['epoch_id'] in identities:
            raise ValueError('历元记录 epoch_id 重复')
        identities.add(row['epoch_id'])
        if row.get('release') == 'Gaia DR4':
            if not isinstance(row.get('native_source_id'), str):
                raise ValueError('DR4 历元需保留精确字符串 native_source_id')
            exact_id(row['native_source_id'])
            if not isinstance(row.get('identity_reference'), str) or not row['identity_reference'].strip():
                raise ValueError('DR4 历元需注明与当前报告源的身份对应依据')
        time = row.get('time', {})
        for field in ('value', 'format', 'scale', 'definition'):
            if not isinstance(time.get(field), str) or not time[field].strip():
                raise ValueError('历元记录缺少官方时间 '+field)
        if time['format'] == 'ISO 8601':
            datetime.fromisoformat(time['value'])
        elif time['format'] in ('JD', 'MJD', 'offset days'):
            if not np.isfinite(float(time['value'])):
                raise ValueError('历元时间不是有限值')
            if time['format'] == 'offset days' and not time.get('zero_point'):
                raise ValueError('偏移日数缺少时间零点')
        else:
            raise ValueError('支持的时间格式为 ISO 8601、JD、MJD、offset days；不得丢弃官方零点')
        array_path = (path.parent/row['arrays_file']).resolve()
        if not array_path.is_relative_to(path.parent):
            raise ValueError('历元光谱数组路径越出资料目录')
        actual = digest(array_path)
        if actual != row.get('sha256'):
            raise ValueError('历元光谱数组校验失败')
        with np.load(array_path, allow_pickle=False) as values:
            if 'source_id' in values and str(values['source_id'].item()) != data['source_id']:
                raise ValueError('历元光谱数组源编号不一致')
            row['arrays'] = _arrays(values)
        result['input_files'][str(array_path)] = actual
        result['records'].append(row)
    return result


def _records(archive_data=None, epoch_data=None):
    records = []
    for product in (archive_data or {}).get('products', []):
        if 'arrays' not in product:
            continue
        role = {'wide': 'wide slit', 'narrow': 'narrow slit'}.get(product.get('role'), '')
        time_scale = str(product.get('time_scale') or 'time scale unspecified').split('（', 1)[0]
        instrument = product['instrument']
        group = str(product.get('obs_id') or product['product_id'])
        records.append(dict(
            record_id=product['product_id'], group_id='archive:'+instrument+':'+group,
            instrument=instrument, label=' '.join([instrument, str(product.get('arm', '')), role]).strip(),
            time=dict(value=product.get('obs_time') or 'observation time unavailable', format='ISO 8601', scale=time_scale,
                      definition='exposure start (DATE-OBS)'),
            detail=f"{product.get('wavelength_medium', 'wavelength medium unspecified')} · {product.get('spectral_frame', 'reference frame unspecified')}",
            resolving_power=product.get('resolving_power'), default=product.get('role') == 'wide', slit_role=product.get('role'),
            release='archive', arrays=_arrays(product['arrays'])))
    for row in (epoch_data or {}).get('records', []):
        # 兼容旧历元清单里写在自由文本标签中的狭缝类型和曝光时刻。
        label = str(row.get('label', '')).replace('窄缝', 'narrow slit').replace('宽缝', 'wide slit')
        slit_role = row.get('role') or ('narrow' if 'narrow slit' in label.lower() else None)
        time = dict(row['time'])
        time['definition'] = {
            '曝光开始（DATE-OBS）': 'exposure start (DATE-OBS)', '曝光开始': 'exposure start',
            '曝光起点': 'exposure start', '曝光中点': 'exposure midpoint', '曝光结束': 'exposure end',
            '覆盖范围': 'observing interval',
        }.get(time['definition'], time['definition'])
        records.append(dict(
            record_id=row['epoch_id'], group_id='epoch:'+row['instrument']+':'+row['group_id'],
            instrument=row['instrument'], label=' '.join([row['instrument'], str(row.get('arm', '')), label]).strip(),
            time=time, detail=' · '.join([str(row.get('wavelength_medium', 'wavelength medium unspecified')),
                                               str(row.get('spectral_frame', 'reference frame unspecified'))]),
            resolving_power=row.get('resolving_power'), default=True, slit_role=slit_role, release=row.get('release', ''),
            arrays=_arrays(row['arrays'])))
    return records


def epoch_summary(spectrum, archive_data=None, epoch_data=None):
    """按观测组计数，不把同一曝光组的不同臂或狭缝算成独立历元。"""
    records = _records(archive_data, epoch_data)
    groups = list(dict.fromkeys(row['group_id'] for row in records))
    return dict(observation_groups=len(groups), spectral_products=len(records),
                gaia_dr3_mean_is_reference=True, gaia_dr4_records=sum(row['release'] == 'Gaia DR4' for row in records),
                group_ids=groups, calibrated_epoch_input=epoch_data is not None,
                fit_executed=False, observation_times_converted=False)


def epoch_section(spectrum, archive_data=None, epoch_data=None):
    """将原采样数组内嵌到 HTML，视图变化不写回科学结果。"""
    records = _records(archive_data, epoch_data)
    summary = epoch_summary(spectrum, archive_data, epoch_data)
    palette = ['#b66b21', '#7854a1', '#147c8c', '#b34863', '#548032', '#456cc0']
    series = []
    for i, row in enumerate(records):
        arrays = row.pop('arrays')
        wave, flux, mask = arrays['wave_nm'], arrays['flux_w_m2_nm'], arrays['mask']
        series.append(dict(row, color=palette[i % len(palette)], reference=False,
                           x=wave.tolist(), y=[float(v/1e-15) if good else None for v, good in zip(flux, mask)],
                           step=float(np.median(np.diff(wave)))))
    wave = np.asarray(spectrum['wave'])
    series.insert(0, dict(record_id='gaia-dr3-mean', group_id=None, instrument='Gaia DR3',
                         label='Gaia DR3 mean XP spectrum', time=None, detail='Mean over multiple visits',
                         color='#657581', default=True, reference=True, x=wave.tolist(),
                         y=[float(v/1e-15) if good else None for v, good in zip(spectrum['flux'], spectrum['mask'])],
                         step=float(np.median(np.diff(wave)))))
    payload = json.dumps(dict(series=series, summary=summary), ensure_ascii=False, allow_nan=False,
                         separators=(',', ':')).replace('<', '\\u003c').replace('>', '\\u003e').replace('&', '\\u0026')
    groups = summary['observation_groups']
    count = summary['spectral_products']
    spectrum_word = 'spectrum' if count == 1 else 'spectra'
    visit_word = 'visit' if groups == 1 else 'visits'
    available = (f'{count} {spectrum_word} from {groups} observing {visit_word}. '
                 'Spectra from different arms or slits in a single visit share one epoch.'
                 if groups else 'Only the Gaia DR3 mean spectrum is available for display.')
    pending = ('Gaia DR4 epoch spectra are pending for this source.' if not summary['gaia_dr4_records']
               else 'Gaia DR4 curves use the calibration and release identification supplied with the epoch spectra.')
    counts = {}
    for item in (archive_data or {}).get('candidates', []):
        if item.get('instrument') not in {r['instrument'] for r in records}:
            counts[item['instrument']] = counts.get(item['instrument'], 0)+1
    pending_archive = ' '.join(
        f'{escape(name)} has {count} archive {"record" if count == 1 else "records"} awaiting spectral data.'
        for name, count in counts.items()
    )
    coverage = '<p class="sub">DR4 observations span 25 July 2014 to 20 January 2020 (<a href="https://gaia.aip.de/cms/data/gdr4/">Gaia release notes</a>).'
    archive_products = (archive_data or {}).get('products', [])
    if archive_products and all(str(p.get('time_scale', '')).startswith('UTC') and str(p.get('obs_time', ''))[:10] > '2020-01-20' for p in archive_products):
        coverage += ' All loaded archival spectra were taken later and provide a comparison at different epochs.'
    coverage += '</p>'
    return '<section id="epochs"><h2>Multi-epoch spectra</h2><p>'+available+'</p><p class="epoch-pending">'+pending+'</p>'+coverage+(' <p class="sub">'+pending_archive+'</p>' if pending_archive else '')+_WINDOW.replace('__DATA__', payload)


_WINDOW = r'''
<style>
#epochs .epoch-pending{padding:9px 13px;background:#eef5fa;border-radius:6px;color:#31566c;font-size:14px}
#epochs .epoch-controls{display:flex;align-items:center;gap:8px;flex-wrap:wrap;margin:15px 0 8px;font-size:14px}
#epochs .epoch-controls>label{max-width:100%;min-width:0}
#epochs button,#epochs select,#epochs input[type=number]{font:inherit;color:#244352;border:1px solid #cbd8e0;border-radius:5px;background:#fff;padding:6px 9px}
#epochs button{cursor:pointer}#epochs button:hover{background:#eaf3f7}#epochs select{max-width:100%}
#epochs input[type=number]{width:90px}#epochs canvas{display:block;width:100%;height:400px;border:1px solid #e0e8ed;border-radius:8px;touch-action:none}
#epochs .epoch-legend{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:8px;margin:12px 0}
#epochs .epoch-key{display:flex;gap:8px;align-items:flex-start;border:1px solid #e2e8ec;padding:8px;border-radius:6px;font-size:13px;line-height:1.45}
#epochs .epoch-key small{display:block;color:#526775;font-size:12px}#epochs .epoch-swatch{width:19px;height:3px;margin-top:8px;flex:none}
#epochs .epoch-status{font-size:13px;color:#526775;min-height:22px}#epochs .epoch-note{font-size:13px;color:#526775}
@media(max-width:700px){#epochs .epoch-legend{grid-template-columns:1fr}#epochs canvas{height:330px}#epochs .epoch-controls{font-size:12px}}
</style>
<div class="epoch-controls"><label>Visit <select data-role="group"><option value="all">Overlay selected visits</option></select></label><button type="button" data-role="previous">Previous visit</button><button type="button" data-role="next">Next visit</button><label><input type="checkbox" data-role="reference" checked> DR3 mean spectrum</label></div>
<div class="epoch-controls"><button type="button" data-range="full">Full spectrum</button><button type="button" data-range="blue">Blue</button><button type="button" data-range="halpha">Hα</button><label>Wavelength <input type="number" data-role="lower" value="336" step="0.1" aria-label="Minimum wavelength"> — <input type="number" data-role="upper" value="480" step="0.1" aria-label="Maximum wavelength"> nm</label><button type="button" data-role="apply">Zoom</button></div>
<canvas data-role="plot" aria-label="Multi-epoch spectra. Wavelength in nm versus absolute flux density." role="img"></canvas>
<div class="epoch-status" data-role="status" aria-live="polite"></div><div class="epoch-legend" data-role="legend"></div>
<p class="epoch-note">Drag across the spectrum to zoom. Double-click to restore the full wavelength range. Each curve retains its native sampling, pixel mask and absolute flux scale. Line positions retain each instrument’s wavelength convention and velocity frame. Instrumental response and slit losses also affect the comparison.</p>
<noscript><p>Enable JavaScript to explore the spectra. The static spectra and fit figures appear below.</p></noscript>
<script type="application/json" id="epoch-data">__DATA__</script>
<script>
(()=>{
const root=document.getElementById('epochs'),data=JSON.parse(root.querySelector('#epoch-data').textContent),series=data.series;
const get=name=>root.querySelector('[data-role="'+name+'"]'),canvas=get('plot'),ctx=canvas.getContext('2d');
const groupSelect=get('group'),lower=get('lower'),upper=get('upper'),status=get('status');
let limits=[336,480],drag=null,box=null;
const groups=[...new Set(series.filter(s=>!s.reference).map(s=>s.group_id))];
const timeLabel=s=>s.time ? s.time.value+' '+s.time.scale+' ('+s.time.format+')'+(s.time.zero_point?' · zero point '+s.time.zero_point:'')+' · '+s.time.definition : 'Mean spectrum over multiple visits';
groups.forEach(id=>{const rows=series.filter(s=>s.group_id===id),first=rows[0],o=document.createElement('option');o.value=id;o.textContent=first.instrument+' · '+timeLabel(first)+' · '+rows.length+(rows.length===1?' spectrum':' spectra');groupSelect.append(o)});
const checks=new Map();series.filter(s=>!s.reference).forEach(s=>{const label=document.createElement('label');label.className='epoch-key';const check=document.createElement('input');check.type='checkbox';check.checked=s.default;check.addEventListener('change',draw);checks.set(s.record_id,check);const swatch=document.createElement('span');swatch.className='epoch-swatch';swatch.style.background=s.color;const text=document.createElement('span'),title=document.createElement('strong'),time=document.createElement('small'),detail=document.createElement('small');title.textContent=s.label;time.textContent=timeLabel(s);detail.textContent=(s.resolving_power?'R ≈ '+s.resolving_power+' · ':'')+s.detail;text.append(title,time,detail);label.append(check,swatch,text);get('legend').append(label)});
function visible(){return series.filter(s=>s.reference ? get('reference').checked : checks.get(s.record_id).checked && (groupSelect.value==='all'||s.group_id===groupSelect.value))}
function draw(){
 const width=canvas.clientWidth,height=canvas.clientHeight,dpr=window.devicePixelRatio||1;canvas.width=Math.round(width*dpr);canvas.height=Math.round(height*dpr);ctx.setTransform(dpr,0,0,dpr,0,0);ctx.clearRect(0,0,width,height);
 const selected=visible(),lo=limits[0],hi=limits[1];let ymin=Infinity,ymax=-Infinity,points=0;
 selected.forEach(s=>{for(let i=0;i<s.x.length;i++){if(s.x[i]<lo||s.x[i]>hi||s.y[i]===null)continue;ymin=Math.min(ymin,s.y[i]);ymax=Math.max(ymax,s.y[i]);points++}});
 if(!Number.isFinite(ymin)){ymin=0;ymax=1}const pad=Math.max((ymax-ymin)*.08,Math.abs(ymax)*.025,1e-6);ymin-=pad;ymax+=pad;
 const left=75,right=20,top=27,bottom=54,pw=width-left-right,ph=height-top-bottom;
 const xp=x=>left+(x-lo)/(hi-lo)*pw,yp=y=>top+(ymax-y)/(ymax-ymin)*ph;
 box={left,right:width-right,top,bottom:height-bottom,width:pw};ctx.font='12px system-ui';ctx.lineWidth=1;
 for(let k=0;k<=5;k++){const x=left+k*pw/5,y=top+k*ph/5;ctx.strokeStyle='#e6edf1';ctx.beginPath();ctx.moveTo(x,top);ctx.lineTo(x,height-bottom);ctx.moveTo(left,y);ctx.lineTo(width-right,y);ctx.stroke();ctx.fillStyle='#526775';ctx.textAlign='center';ctx.fillText((lo+k*(hi-lo)/5).toFixed(hi-lo<10?2:0),x,height-bottom+21);ctx.textAlign='right';const value=ymax-k*(ymax-ymin)/5;ctx.fillText(Math.abs(value)>1000||Math.abs(value)<.001&&value!==0?value.toExponential(1):value.toPrecision(3),left-8,y+4)}
 ctx.fillStyle='#244352';ctx.textAlign='center';ctx.fillText('Wavelength (nm, native frames)',left+pw/2,height-12);ctx.save();ctx.translate(16,top+ph/2);ctx.rotate(-Math.PI/2);ctx.fillText('Fλ (10⁻¹⁵ W m⁻² nm⁻¹)',0,0);ctx.restore();
 ctx.save();ctx.beginPath();ctx.rect(left,top,pw,ph);ctx.clip();
 selected.forEach(s=>{ctx.strokeStyle=s.color;ctx.lineWidth=s.reference?1.4:1;ctx.beginPath();let previous=null;for(let i=0;i<s.x.length;i++){const x=s.x[i],y=s.y[i];if(y===null||x<lo||x>hi){previous=null;continue}if(previous===null||x-previous>4*s.step)ctx.moveTo(xp(x),yp(y));else ctx.lineTo(xp(x),yp(y));previous=x}ctx.stroke()});
 if(drag){ctx.fillStyle='rgba(29,101,135,.12)';ctx.fillRect(Math.min(drag[0],drag[1]),top,Math.abs(drag[1]-drag[0]),ph)}ctx.restore();
 ctx.strokeStyle='#9db1bf';ctx.strokeRect(left,top,pw,ph);const count=selected.filter(s=>!s.reference).length;status.textContent=points ? count+(count===1?' epoch spectrum':' epoch spectra')+(get('reference').checked?' + DR3 mean spectrum':'')+'. All valid samples in this interval are shown.' : 'The selected spectra have no valid samples in this interval.';
}
function setRange(lo,hi){if(!Number.isFinite(lo)||!Number.isFinite(hi)||lo>=hi){status.textContent='Enter a finite wavelength interval with the lower limit first.';return}limits=[lo,hi];lower.value=String(lo);upper.value=String(hi);draw()}
root.querySelectorAll('[data-range]').forEach(b=>b.addEventListener('click',()=>{const r={full:[335,1020],blue:[336,480],halpha:[654,659]}[b.dataset.range];setRange(...r);if(b.dataset.range==='halpha'){series.filter(s=>!s.reference&&s.slit_role==='narrow'&&s.x[0]<659&&s.x[s.x.length-1]>654).forEach(s=>checks.get(s.record_id).checked=true);draw()}}));
get('apply').addEventListener('click',()=>setRange(Number(lower.value),Number(upper.value)));get('reference').addEventListener('change',draw);groupSelect.addEventListener('change',draw);
function step(direction){if(!groups.length)return;const current=groups.indexOf(groupSelect.value);groupSelect.value=groups[(current<0?(direction>0?0:groups.length-1):(current+direction+groups.length)%groups.length)];const rows=series.filter(s=>s.group_id===groupSelect.value);if(!rows.some(s=>checks.get(s.record_id).checked))rows.forEach(s=>checks.get(s.record_id).checked=true);draw()}
get('previous').addEventListener('click',()=>step(-1));get('next').addEventListener('click',()=>step(1));
function pointerX(e){return e.clientX-canvas.getBoundingClientRect().left}
canvas.addEventListener('pointerdown',e=>{const x=pointerX(e);if(box&&x>=box.left&&x<=box.right){drag=[x,x];canvas.setPointerCapture(e.pointerId)}});
canvas.addEventListener('pointermove',e=>{if(drag){drag[1]=Math.max(box.left,Math.min(box.right,pointerX(e)));draw()}});
canvas.addEventListener('pointerup',()=>{if(!drag)return;const [a,b]=drag;drag=null;if(Math.abs(a-b)>8){const lo=limits[0]+(Math.min(a,b)-box.left)/box.width*(limits[1]-limits[0]),hi=limits[0]+(Math.max(a,b)-box.left)/box.width*(limits[1]-limits[0]);setRange(Number(lo.toFixed(4)),Number(hi.toFixed(4)))}else draw()});
canvas.addEventListener('pointercancel',()=>{drag=null;draw()});canvas.addEventListener('dblclick',()=>setRange(335,1020));
get('previous').disabled=get('next').disabled=!groups.length;new ResizeObserver(draw).observe(canvas);draw();
})();
</script></section>
'''
