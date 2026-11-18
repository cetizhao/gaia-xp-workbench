"""查询单源巡天测光，保留原表、位置匹配和单位；不读取或拟合 XP。"""
from __future__ import annotations

import csv
from datetime import datetime, timezone
import math
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import Request, urlopen
import xml.etree.ElementTree as ET

from .classical.xp_workbench import digest, exact_id, new_directory, read_json, write_json

ENDPOINTS = ('https://vizier.cds.unistra.fr/viz-bin/asu-xml',
             'https://vizier.cfa.harvard.edu/viz-bin/asu-xml')
MAX_ROWS = 100
TWO_MASS_CAL = 'https://www.ipac.caltech.edu/2mass/releases/allsky/doc/sec6_4a.html'
WISE_CAL = 'https://irsa.ipac.caltech.edu/data/WISE/docs/release/All-Sky/expsup/sec4_4h.html'
APASS_CAL = 'https://svo2.cab.inta-csic.es/theory/fps/index.php?mode=browse&gname=Misc&gname2=APASS'
SURVEYS = (
    dict(name='APASS DR9', key='apass', catalogue='II/336/apass9', epoch_year=None,
         epoch_note='逐源观测历元未提供；目录观测约为 2010–2014 年，匹配采用 Gaia 2016 位置，不将 J2000 当作观测历元。',
         reference='https://cdsarc.cds.unistra.fr/viz-bin/cat/II/336',
         quality_reference='https://mintaka.aavso.org/apass',
         bands=(('g', "g'mag", 0.463927, 3631.), ('r', "r'mag", 0.612196, 3631.), ('i', "i'mag", 0.743889, 3631.))),
    dict(name='2MASS', key='2mass', catalogue='II/246/out', epoch_year=2000.,
         epoch_note='以 2000.0 年位置初查，使用候选的 JD 观测日期重新计算角距离。',
         reference='https://cdsarc.cds.unistra.fr/viz-bin/cat/II/246',
         quality_reference='https://www.ipac.caltech.edu/2mass/releases/allsky/doc/sec2_2a.html',
         bands=(('J', 'Jmag', 1.235, 1594.), ('H', 'Hmag', 1.662, 1024.), ('Ks', 'Kmag', 2.159, 666.7))),
    dict(name='AllWISE', key='allwise', catalogue='II/328/allwise', epoch_year=2010.5,
         epoch_note='使用约 2010.5 年的观测中心历元作线性自行修正；合并观测并非单次历元。',
         reference='https://cdsarc.cds.unistra.fr/viz-bin/cat/II/328',
         quality_reference='https://irsa.ipac.caltech.edu/data/WISE/docs/release/AllWISE/expsup/sec2_1a.html',
         bands=(('W1', 'W1mag', 3.3526, 309.540), ('W2', 'W2mag', 4.6028, 171.787),
                ('W3', 'W3mag', 11.5608, 31.674), ('W4', 'W4mag', 22.0883, 8.363))),
)


def _number(text):
    if text is None or str(text).strip() in ('', '--', 'null', 'NaN'):
        return None
    value = float(text)
    return value if math.isfinite(value) else None


def parse_votable(raw, catalogue):
    """保留标识符的十进制字符串，读取 CDS 的 TABLEDATA 或内嵌 TSV。"""
    root = ET.fromstring(raw, parser=ET.XMLParser(target=ET.TreeBuilder(insert_comments=True)))
    for info in root.findall('.//{*}INFO'):
        if info.get('name', '').upper() in ('QUERY_STATUS', 'ERROR') and info.get('value', '').upper() in ('ERROR', 'OVERFLOW'):
            raise ValueError('VizieR 查询失败或结果被截断：' + ''.join(info.itertext()))
    tables = [t for t in root.findall('.//{*}TABLE') if t.get('name') == catalogue]
    if len(tables) != 1:
        raise ValueError(f'响应没有唯一的 {catalogue} 表，不能解释成未检出')
    table = tables[0]
    fields = []
    for f in table.findall('{*}FIELD'):
        fields.append(dict(name=f.get('name'), unit=f.get('unit', ''), datatype=f.get('datatype'),
                           description=f.findtext('{*}DESCRIPTION', default=''), ref=f.get('ref')))
    names = [f['name'] for f in fields]
    rows = []
    data = table.find('.//{*}CSV')
    if data is not None:
        lines = (data.text or '').strip('\r\n').splitlines()
        count = int(data.get('headlines', 0))
        if not lines or count < 1 or lines[0].split('\t') != names:
            raise ValueError('VizieR 内嵌表列名不一致')
        values = list(csv.reader(lines[count:], delimiter='\t'))
    else:
        values = [[td.text or '' for td in tr.findall('{*}TD')] for tr in table.findall('.//{*}TR')]
        explicitly_empty = any(e.tag is ET.Comment and 'EMPTY result, no DATA part' in (e.text or '') for e in table)
        if table.find('.//{*}DATA') is None and not explicitly_empty:
            raise ValueError('VizieR 响应没有数据区')
    for row in values:
        if len(row) != len(names): raise ValueError('VizieR 数据列数不一致')
        rows.append(dict(zip(names, (v.strip() for v in row))))
    if len(rows) >= MAX_ROWS: raise ValueError('候选达到数量上限，未自动选择匹配')
    coordinates = [dict(e.attrib) for e in root.findall('.//{*}COOSYS')]
    return rows, fields, coordinates


def _check_units(fields, expected):
    units = {f['name']: f['unit'] for f in fields}
    for name, unit in expected.items():
        if units.get(name) != unit:
            raise ValueError(f'目录字段 {name} 的单位不是预期的 {unit}')


def _download(directory, key, parameters, provenance):
    attempts = []
    for attempt_index, endpoint in enumerate(ENDPOINTS, start=1):
        url = endpoint + '?' + urlencode(parameters)
        try:
            request = Request(url, headers={'User-Agent': 'gaia-xp-workbench photometry/0.3'})
            with urlopen(request, timeout=25) as response:
                raw = response.read(5_000_001)
            if len(raw) > 5_000_000: raise ValueError('单源响应超出 5 MB 限额')
            path = directory/'raw'/(key+f'_attempt{attempt_index}.xml')
            path.write_bytes(raw)
            item = dict(file=str(path.relative_to(directory)).replace('\\', '/'), url=url,
                        retrieved_utc=datetime.now(timezone.utc).isoformat(), sha256=digest(path), attempts=attempts)
            provenance.append(item)
            rows, fields, coordinates = parse_votable(raw, parameters['-source'])
            path = path.rename(directory/'raw'/(key+'.xml'))
            item['file'] = str(path.relative_to(directory)).replace('\\', '/')
            item['fields'] = fields
            item['coordinates'] = coordinates
            return rows, fields, coordinates, url
        except (OSError, ValueError, ET.ParseError) as error:
            attempts.append(dict(url=url, error=str(error)))
    provenance.append(dict(file=None, attempts=attempts, status='failed'))
    raise RuntimeError('VizieR 查询失败：' + '; '.join(a['error'] for a in attempts))


def propagate_position(target, epoch_year):
    """按 Gaia pmRA=mu_alpha*cos(dec) 作短时间线性修正，不含透视加速度。"""
    ra, dec = target['ra_deg'], target['dec_deg']
    if epoch_year is None or target['pmra_mas_yr'] is None or target['pmdec_mas_yr'] is None:
        return ra, dec
    if abs(dec) >= 89.9: raise ValueError('本位置修正不适用于极区源')
    years = epoch_year-target['epoch_year']
    return ((ra + target['pmra_mas_yr']*years/(3.6e6*math.cos(math.radians(dec)))) % 360,
            dec + target['pmdec_mas_yr']*years/3.6e6)


def separation_arcsec(ra1, dec1, ra2, dec2):
    a, b = map(math.radians, (dec1, dec2))
    dra = math.radians(ra2-ra1)
    sine = math.sin((b-a)/2)**2 + math.cos(a)*math.cos(b)*math.sin(dra/2)**2
    return math.degrees(2*math.asin(min(1., math.sqrt(max(0., sine)))))*3600


def magnitude_to_flux(magnitude, error, zero_point_jy):
    flux = zero_point_jy*10**(-.4*magnitude)
    return flux, None if error is None else math.log(10)*.4*flux*error


def match_candidates(rows, target, survey, radius_arcsec):
    candidates = []
    for row in rows:
        ra, dec = _number(row['RAJ2000']), _number(row['DEJ2000'])
        if ra is None or dec is None: raise ValueError('候选缺少坐标')
        epoch = survey['epoch_year']
        if survey['key'] == '2mass' and _number(row.get('JD')) is not None:
            epoch = 2000. + (_number(row['JD'])-2451545.)/365.25
        center = propagate_position(target, epoch)
        sep = separation_arcsec(*center, ra, dec)
        identifier = row.get('2MASS') if survey['key']=='2mass' else row.get('AllWISE')
        if survey['key'] == 'apass': identifier = f'APASS DR9 ({ra:.6f}, {dec:+.6f} deg)'
        candidates.append(dict(object_id=identifier, ra_deg=ra, dec_deg=dec, epoch_year=epoch,
                               separation_arcsec=sep, within_radius=sep <= radius_arcsec,
                               compared_gaia_ra_deg=center[0], compared_gaia_dec_deg=center[1], raw=row))
    candidates.sort(key=lambda c:c['separation_arcsec'])
    inside = [c for c in candidates if c['within_radius']]
    status = 'matched' if len(inside)==1 else ('ambiguous' if inside else 'no_match')
    return candidates, status, inside[0] if len(inside)==1 else None


def _flag(text, index):
    text = str(text or '')
    return text[index] if len(text)>index else '?'


def measurements_for(candidate, survey):
    row = candidate['raw']; measurements = []
    for index, (band, column, wave, zero) in enumerate(survey['bands']):
        mag, error = _number(row.get(column)), _number(row.get('e_'+column))
        flags, reasons = {}, []
        upper = False
        if survey['key']=='2mass':
            quality = _flag(row.get('Qflg'), index); contamination = _flag(row.get('Cflg'), index)
            flags = {k:row.get(k) for k in ('Qflg','Rflg','Bflg','Cflg','Xflg','Aflg','prox','use')}
            upper = quality == 'U'
            if quality not in 'ABCU': reasons.append('测光质量非 A/B/C 或上限 U')
            if contamination != '0': reasons.append('存在伪像或混叠旗标')
            if row.get('Xflg') != '0' or row.get('Aflg') != '0': reasons.append('扩展源污染或太阳系天体旗标')
        elif survey['key']=='allwise':
            quality = _flag(row.get('qph'), index); contamination = _flag(row.get('ccf'), index)
            upper = quality == 'U'
            flags = {k:row.get(k) for k in ('qph','ccf','ex','nb','na','var','fmoon','sat'+str(index+1))}
            if quality not in 'ABCU': reasons.append('测光质量非 A/B/C 或上限 U')
            if contamination != '0': reasons.append('WISE 伪像污染旗标 '+contamination)
            if row.get('ex') != '0': reasons.append('可能为扩展源')
            if (_number(row.get('sat'+str(index+1))) or 0)>0: reasons.append('含饱和像素')
        else:
            quality = row.get('u_e_'+column, '?')
            flags = {k:row.get(k) for k in ('u_e_'+column,'nobs','mobs','Field')}
            if quality not in ('0', '1'): reasons.append('目录误差类型旗标缺失')
        if mag is None: reasons.append('无有效星等')
        if not upper and (error is None or error<=0): reasons.append('无有效星等误差')
        if upper: error=None
        flux, flux_error = (None,None) if mag is None else magnitude_to_flux(mag,error,zero)
        calibration = APASS_CAL if survey['key']=='apass' else (TWO_MASS_CAL if survey['key']=='2mass' else WISE_CAL)
        measurements.append(dict(survey=survey['name'], band=band, wavelength_um=wave,
            mag=mag, mag_error=error, magnitude_unit='mag', system='AB' if survey['key']=='apass' else 'Vega',
            zero_point_jy=zero, flux_jy=flux, flux_error_jy=flux_error, flux_unit='Jy',
            is_upper_limit=upper, upper_limit_confidence=.95 if upper and survey['key']=='allwise' else None,
            upper_limit_note=('保留目录上限；CDS 表说明与 2MASS FAQ 对置信度分别写 95% 和 97%，此处不指定统一数值'
                              if upper and survey['key']=='2mass' else None),
            quality=quality, quality_flags=flags, usable=not reasons, quality_notes=reasons,
            catalogue=survey['catalogue'], object_id=candidate['object_id'], epoch_year=candidate['epoch_year'],
            calibration_reference=calibration, separation_arcsec=candidate['separation_arcsec'],
            error_note=('多次观测的标准差，不是均值标准误' if quality=='0' else '单次观测的 Poisson 误差')
                       if survey['key']=='apass' else '目录星等误差；未额外传播零点或颜色改正误差'))
    return measurements


def fetch_photometry(source_id, output, radius_arcsec=3.):
    source_id = exact_id(source_id)
    radius_arcsec = float(radius_arcsec)
    if not math.isfinite(radius_arcsec) or not 0<radius_arcsec<=10:
        raise ValueError('单源匹配半径必须大于 0 且不超过 10 arcsec')
    destination = new_directory(output); (destination/'raw').mkdir()
    result = dict(schema_version=1,source_id=source_id,status='running',target=None,
                  surveys=[], measurements=[], provenance=[], notes=[
        '位置匹配不等于已排除混叠；多候选时不自动选择最近的一颗。',
        '测光与 Gaia DR3 平均 XP 通常不同期，差别可来自变光、孔径或标定。',
        '通量按目录零点换算，未作消光或颜色改正；误差只传播目录星等误差。',
        'APASS 波长只作代表位置，采用 SVO 中假定与 SDSS 相同的滤光片；不作精确合成测光。',
        'APASS 南天 DR9 的 V/r/i 部分观测受散焦影响，使用 15–20 arcsec 孔径，需留意混叠。',
        'APASS 误差旗标 0 为多次观测标准差，1 为单次观测 Poisson 误差；不把标准差当作均值标准误。',
        'WISE W3/W4 对谱形的颜色改正可能重要；红外测光不能直接验证光学吸积量。'])
    try:
        params={'-source':'I/355/gaiadr3','Source':source_id,'-out':'Source,RA_ICRS,DE_ICRS,pmRA,pmDE','-out.max':'5'}
        rows,fields,coords,url=_download(destination,'gaia',params,result['provenance'])
        _check_units(fields,{'RA_ICRS':'deg','DE_ICRS':'deg','pmRA':'mas/yr','pmDE':'mas/yr'})
        if len(rows)!=1 or rows[0]['Source']!=source_id: raise ValueError('Gaia 精确源编号查询未返回唯一对应行')
        ref=next(f['ref'] for f in fields if f['name']=='RA_ICRS')
        epoch=next((_number(c.get('epoch')) for c in coords if c.get('ID')==ref),None)
        if epoch is None: raise ValueError('Gaia 响应未提供坐标历元')
        row=rows[0]
        target=dict(ra_deg=_number(row['RA_ICRS']),dec_deg=_number(row['DE_ICRS']),epoch_year=epoch,
                    pmra_mas_yr=_number(row['pmRA']),pmdec_mas_yr=_number(row['pmDE']),source_url=url,
                    catalogue='I/355/gaiadr3',proper_motion_note='pmRA 包含 cos(dec)；未传播位置协方差或透视加速度。')
        if target['ra_deg'] is None or target['dec_deg'] is None: raise ValueError('Gaia 缺少有效坐标')
        result['target']=target
        for survey in SURVEYS:
            center=propagate_position(target,survey['epoch_year'])
            item={k:survey[k] for k in ('name','catalogue','epoch_year','epoch_note','reference','quality_reference')}
            item.update(query_center=dict(ra_deg=center[0],dec_deg=center[1]),radius_arcsec=radius_arcsec,
                        status='query_failed',candidates=[],selected_id=None,separation_arcsec=None)
            if target['pmra_mas_yr'] is None or target['pmdec_mas_yr'] is None:
                item['epoch_note'] += ' Gaia 自行缺失，本次保留 Gaia 原历元位置，匹配需人工复查。'
            result['surveys'].append(item)
            try:
                params={'-source':survey['catalogue'],'-c':f'{center[0]:.10f} {center[1]:+.10f}',
                        '-c.rs':str(radius_arcsec),'-out.all':'1','-out.max':str(MAX_ROWS)}
                rows,fields,_,url=_download(destination,survey['key'],params,result['provenance'])
                expected={'RAJ2000':'deg','DEJ2000':'deg'}
                for _,col,_,_ in survey['bands']:expected.update({col:'mag','e_'+col:'mag'})
                _check_units(fields,expected)
                candidates,status,chosen=match_candidates(rows,target,survey,radius_arcsec)
                item.update(status=status,candidates=candidates,source_url=url)
                if chosen:
                    item.update(selected_id=chosen['object_id'],separation_arcsec=chosen['separation_arcsec'])
                    result['measurements'].extend(measurements_for(chosen,survey))
            except (RuntimeError,ValueError,KeyError) as error:item['error']=str(error)
        result['status']='partial' if any(s['status']=='query_failed' for s in result['surveys']) else 'complete'
    except Exception as error:
        result.update(status='failed',error=str(error));write_json(destination/'photometry.json',result)
        raise
    write_json(destination/'photometry.json',result)
    write_json(destination/'manifest.json',dict(schema_version=1,source_id=source_id,
        photometry_sha256=digest(destination/'photometry.json'),status=result['status']))
    return dict(status=result['status'],source_id=source_id,output=str(destination),
                photometry=str(destination/'photometry.json'),measurements=len(result['measurements']))


def load_photometry(path, source_id=None):
    directory=Path(path).expanduser().resolve()
    if directory.is_file():directory=directory.parent
    manifest=read_json(directory/'manifest.json')
    if digest(directory/'photometry.json')!=manifest['photometry_sha256']:raise ValueError('测光摘要校验失败')
    data=read_json(directory/'photometry.json')
    sid=exact_id(data['source_id'])
    if (source_id is not None and sid!=exact_id(source_id)) or sid!=manifest['source_id']:
        raise ValueError('测光与 XP 源编号不一致')
    if data['status'] not in ('complete','partial'):raise ValueError('测光查询未完成')
    for item in data['provenance']:
        if item.get('file'):
            raw=(directory/item['file']).resolve()
            if not raw.is_relative_to(directory) or digest(raw)!=item['sha256']:raise ValueError('测光原表校验失败')
    return data
