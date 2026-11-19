"""按源查询档案光谱，下载指定ESO一维产品；不重拟合XP。"""
from __future__ import annotations

import csv
from datetime import datetime, timezone
import io
import json
import math
from pathlib import Path
import re
from urllib.parse import urlencode, urlparse
from urllib.request import Request, urlopen
import xml.etree.ElementTree as ET

import numpy as np

from .classical.xp_workbench import digest, exact_id, new_directory, read_json, write_json
from .photometry import propagate_position, separation_arcsec

ESO_TAP = 'https://archive.eso.org/tap_obs/sync'
MAST_API = 'https://mast.stsci.edu/api/v0/invoke'
XSHOOTER_REFERENCE = 'https://www.eso.org/rm/api/v1/public/releaseDescriptions/70'
MAX_CANDIDATES = 200


def _number(value):
    if value is None or str(value).strip() in ('','null','NaN'): return None
    number=float(value)
    return number if math.isfinite(number) else None


def _safe_name(value):
    return re.sub(r'[^A-Za-z0-9._-]', '_', value)


def _download(url, path, provenance, *, payload=None, maximum=100_000_000):
    request=Request(url,data=payload,headers={'User-Agent':'gaia-xp-workbench spectroscopy'})
    with urlopen(request,timeout=45) as response: raw=response.read(maximum+1)
    if len(raw)>maximum: raise ValueError('单个档案响应超过设定大小')
    path.write_bytes(raw)
    provenance.append(dict(file=str(path),url=url,retrieved_utc=datetime.now(timezone.utc).isoformat(),
                           sha256=digest(path),bytes=len(raw)))
    return raw


def _relative_provenance(provenance, directory):
    for item in provenance:
        if not item.get('file'):continue
        path=Path(item['file'])
        if path.is_absolute(): item['file']=str(path.relative_to(directory)).replace('\\','/')


def _gaia_target(source_id, destination, provenance):
    from .photometry import _download as vizier_download, _check_units
    params={'-source':'I/355/gaiadr3','Source':source_id,'-out':'Source,RA_ICRS,DE_ICRS,pmRA,pmDE','-out.max':'5'}
    rows,fields,coords,url=vizier_download(destination,'gaia',params,provenance)
    _check_units(fields,{'RA_ICRS':'deg','DE_ICRS':'deg','pmRA':'mas/yr','pmDE':'mas/yr'})
    if len(rows)!=1 or rows[0]['Source']!=source_id: raise ValueError('Gaia源编号未唯一对应')
    ref=next(f['ref'] for f in fields if f['name']=='RA_ICRS')
    epoch=next((_number(c.get('epoch')) for c in coords if c.get('ID')==ref),None)
    if epoch is None: raise ValueError('Gaia位置缺少历元')
    row=rows[0]
    return dict(source_id=source_id,ra_deg=_number(row['RA_ICRS']),dec_deg=_number(row['DE_ICRS']),epoch_year=epoch,
                pmra_mas_yr=_number(row['pmRA']),pmdec_mas_yr=_number(row['pmDE']),source_url=url)


def recommended_products(candidates):
    """选一次含UVB/VIS的X-shooter观测，保留该观测各光学设置。"""
    groups={}
    for c in candidates:
        if c['instrument']=='XSHOOTER' and c.get('matched') and c['wave_min_nm']<600 and c['wave_max_nm']>330:
            groups.setdefault(c['obs_id'],[]).append(c)
    complete=[group for group in groups.values() if any(c['wave_min_nm']<350 for c in group)
              and any(c['wave_max_nm']>900 and c['wave_min_nm']>400 for c in group)]
    if not complete:return []
    chosen=max(complete,key=lambda group:max(c['mjd_start'] for c in group))
    if len(chosen)>6:return []
    return [c['product_id'] for c in sorted(chosen,key=lambda c:(c['wave_min_nm'],c['resolving_power'] or 0))]


def discover_spectra(source_id, output, target=None, radius_arcsec=5.):
    source_id=exact_id(source_id)
    radius_arcsec=float(radius_arcsec)
    if not math.isfinite(radius_arcsec) or not 0<radius_arcsec<=10:raise ValueError('光谱查询半径须在0–10角秒内')
    destination=new_directory(output);(destination/'raw').mkdir()
    result=dict(schema_version=1,source_id=source_id,status='running',provenance=[],candidates=[],archives=[])
    try:
        if target is None: target=_gaia_target(source_id,destination,result['provenance'])
        elif target.get('source_id',source_id)!=source_id:raise ValueError('位置与源编号不一致')
        target=dict(target);result['target']=target;result['radius_arcsec']=radius_arcsec
        ra,dec=target['ra_deg'],target['dec_deg']
        columns='target_name,dp_id,s_ra,s_dec,t_min,t_max,t_exptime,em_min,em_max,em_res_power,instrument_name,obs_collection,obs_id,obs_publisher_did,access_url,access_format,calib_level'
        # ESO将一维谱的s_region保存为点；此空间索引比逐行POINT计算有效。
        query=f"SELECT TOP {MAX_CANDIDATES} {columns} FROM ivoa.ObsCore WHERE CONTAINS(s_region,CIRCLE('ICRS',{ra:.10f},{dec:.10f},{radius_arcsec/3600:.12f}))=1 AND dataproduct_type='spectrum'"
        result['eso_query']=query
        url=ESO_TAP+'?'+urlencode(dict(REQUEST='doQuery',LANG='ADQL',FORMAT='csv',QUERY=query,MAXREC=MAX_CANDIDATES))
        raw=_download(url,destination/'raw/eso_obscore.csv',result['provenance'],maximum=5_000_000)
        rows=list(csv.DictReader(io.StringIO(raw.decode('utf-8'))))
        if not raw.startswith(b'target_name,'):raise ValueError('ESO没有返回预期ObsCore表，不能解释为无光谱')
        if len(rows)>=MAX_CANDIDATES:raise ValueError('光谱候选达到上限；须缩小查询或明确产品')
        for r in rows:
            epoch=2000.+(float(r['t_min'])-51544.5)/365.25
            center=propagate_position(target,epoch)
            sep=separation_arcsec(*center,float(r['s_ra']),float(r['s_dec']))
            result['candidates'].append(dict(product_id=r['dp_id'],target_name=r['target_name'],instrument=r['instrument_name'],
                obs_id=r['obs_id'],collection=r['obs_collection'],ra_deg=float(r['s_ra']),dec_deg=float(r['s_dec']),
                mjd_start=float(r['t_min']),mjd_end=float(r['t_max']),exposure_s=float(r['t_exptime']),
                wave_min_nm=float(r['em_min'])*1e9,wave_max_nm=float(r['em_max'])*1e9,resolving_power=_number(r['em_res_power']),
                match_epoch_year=epoch,match_separation_arcsec=sep,matched=sep<=radius_arcsec,
                access_url=r['access_url'],access_format=r['access_format'],publisher_id=r['obs_publisher_did'],calib_level=int(r['calib_level']),raw=r))
        result['archives'].append(dict(name='ESO ObsCore',status='complete',spectra=len(rows)))
        request=dict(service='Mast.Caom.Filtered.Position',params=dict(columns='*',filters=[dict(paramName='dataproduct_type',values=['spectrum'])],
                     position=f'{ra},{dec},{radius_arcsec/3600}'),format='json',pagesize=MAX_CANDIDATES,page=1)
        result['mast_request']=request
        try:
            raw=_download(MAST_API,destination/'raw/mast_spectra.json',result['provenance'],payload=urlencode(dict(request=json.dumps(request))).encode(),maximum=5_000_000)
            mast=json.loads(raw)
            if mast.get('status')!='COMPLETE':raise ValueError('MAST查询未完成')
            rows=mast.get('data',[])
            result['mast_candidates']=rows
            result['archives'].append(dict(name='MAST',status='complete' if len(rows)<MAX_CANDIDATES else 'truncated',spectra=len(rows),download_supported=False))
        except (OSError,ValueError) as error:
            result['archives'].append(dict(name='MAST',status='query_failed',error=str(error)))
        result['recommended_product_ids']=recommended_products(result['candidates'])
        result['selection_note']='默认建议最新一组含UVB/VIS的X-shooter观测，保留该组宽/窄缝光学产品；产品可用不等于已确认质量。其他仪器需明确产品编号。'
        result['matching_note']='以Gaia参考位置作有界初查，再按各观测日期线性传播自行核对；未传播位置协方差。指向位置不等于排除伴星或狭缝混叠；初查半径外的高自行源可能漏检。'
        result['status']='complete' if all(a['status']=='complete' for a in result['archives']) else 'partial'
    except Exception as error:
        result.update(status='failed',error=str(error));_relative_provenance(result['provenance'],destination);write_json(destination/'discovery.json',result);raise
    _relative_provenance(result['provenance'],destination);write_json(destination/'discovery.json',result)
    write_json(destination/'manifest.json',dict(source_id=source_id,discovery_sha256=digest(destination/'discovery.json')))
    return dict(status=result['status'],source_id=source_id,output=str(destination),eso_spectra=len(result['candidates']),recommended_product_ids=result['recommended_product_ids'])


def _load_discovery(path):
    path=Path(path).expanduser().resolve();directory=path if path.is_dir() else path.parent
    manifest=read_json(directory/'manifest.json')
    if digest(directory/'discovery.json')!=manifest['discovery_sha256']:raise ValueError('光谱查询记录校验失败')
    data=read_json(directory/'discovery.json')
    if data['status'] not in ('complete','partial'):raise ValueError('光谱查询未完成')
    _verify_files(directory,data['provenance'])
    return directory,data


def _verify_files(directory, provenance):
    for item in provenance:
        if not item.get('file'):continue
        path=(directory/item['file']).resolve()
        if not path.is_relative_to(directory) or digest(path)!=item['sha256']:raise ValueError('档案文件校验失败')


def parse_datalink(raw, publisher_id):
    root=ET.fromstring(raw)
    table=root.find('.//{*}TABLE')
    if table is None:raise ValueError('DataLink缺少产品表')
    names=[f.get('name') for f in table.findall('{*}FIELD')]
    rows=[dict(zip(names,[td.text or '' for td in tr.findall('{*}TD')])) for tr in table.findall('.//{*}TR')]
    main=[r for r in rows if r.get('ID')==publisher_id and r.get('semantics')=='#this']
    if len(main)!=1 or main[0].get('error_message'):raise ValueError('DataLink未返回唯一主产品')
    return main[0],rows


def read_eso_fits(path, candidate):
    """仅接收带明确物理通量单位的ESO标准一维谱；保留负通量与质量掩码。"""
    try:
        from astropy.io import fits
        from astropy import units as u
    except ImportError as error:raise RuntimeError('下载光谱需安装 gaia-xp-workbench[spectroscopy]') from error
    with fits.open(path,memmap=False) as hdus:
        primary=hdus[0].header
        tables=[h for h in hdus[1:] if h.data is not None and set(['WAVE','FLUX','ERR']).issubset(h.columns.names)]
        if len(tables)!=1:raise ValueError('未找到唯一WAVE/FLUX/ERR标准谱表')
        table=tables[0];header=table.header
        if len(table.data)!=1:raise ValueError('只支持单行向量式ESO一维光谱')
        unit={c.name:c.unit for c in table.columns}
        wave_factor=u.Unit(unit['WAVE'],format='fits').to(u.nm)
        flux_factor=u.Unit(unit['FLUX'],format='fits').to(u.W/u.m**2/u.nm)
        err_factor=u.Unit(unit['ERR'],format='fits').to(u.W/u.m**2/u.nm)
        wave=np.asarray(table.data['WAVE'][0],dtype=float).ravel()*wave_factor
        flux=np.asarray(table.data['FLUX'][0],dtype=float).ravel()*flux_factor
        error=np.asarray(table.data['ERR'][0],dtype=float).ravel()*err_factor
        if not (wave.shape==flux.shape==error.shape) or not np.all(np.diff(wave)>0):raise ValueError('光谱长度或波长顺序无效')
        quality=np.asarray(table.data['QUAL'][0],dtype=np.int64).ravel() if 'QUAL' in unit else np.zeros(len(wave),dtype=np.int64)
        mask=np.isfinite(wave)&np.isfinite(flux)&np.isfinite(error)&(error>0)&(quality==0)
        if not mask.any():raise ValueError('光谱没有有效像素')
        get=lambda key,default=None:primary.get(key,header.get(key,default))
        obs_time=get('DATE-OBS');mjd=_number(get('MJD-OBS'))
        if str(get('ARCFILE','')).removesuffix('.fits')!=candidate['product_id']:raise ValueError('FITS产品编号与DataLink选择不一致')
        if not obs_time or mjd is None:raise ValueError('光谱缺少观测日期')
        if abs(mjd-candidate['mjd_start'])>.01:raise ValueError('FITS观测日期与查询产品不一致')
        if str(get('INSTRUME'))!=candidate['instrument']:raise ValueError('FITS仪器与查询产品不一致')
        if str(get('FLUXCAL','')).upper()!='ABSOLUTE':raise ValueError('此入口只转换有绝对通量标定的ESO一维产品')
        slit=get('ESO QC SLITW')
        slit_width=_number(str(slit).split('x')[0]) if slit else None
        medium='air' if 'obs.atmos' in str(header.get('TUCD1','')) else 'unspecified'
        frame=get('SPECSYS','unspecified')
        timesys=get('TIMESYS')
        notes=['未作大气吸收改正；逐点误差不含波长间协方差及绝对标定误差。']
        if not get('TOT_FLUX',False):notes.append('窄缝可能损失通量，不用于直接比较绝对亮度。')
        if _number(get('FLUXERR')) is None or float(get('FLUXERR',-1))<0:notes.append('绝对通量标定误差未定量给出。')
        metadata=dict(product_id=candidate['product_id'],instrument=candidate['instrument'],target_name=get('OBJECT'),
            arm=get('ESO SEQ ARM','unknown'),obs_id=candidate['obs_id'],obs_time=obs_time,mjd_start=mjd,
            time_scale=timesys or 'UTC（ESO日期约定；FITS未另列TIMESYS）',
            exposure_s=_number(get('TEXPTIME',candidate['exposure_s'])),resolving_power=_number(get('SPEC_RES',candidate['resolving_power'])),
            resolving_power_note='SPEC_RES为同狭缝弧灯标定的名义分辨率，非逐次恒星实测值',
            slit_width_arcsec=slit_width,role='wide' if slit_width is not None and slit_width>=3 else 'narrow',
            flux_calibration=get('FLUXCAL','unknown'),total_flux=bool(get('TOT_FLUX',False)),flux_scale_error_percent=_number(get('FLUXERR')),
            wavelength_medium=medium,spectral_frame=frame,telluric_corrected=False,
            original_units=dict(wavelength=unit['WAVE'],flux=unit['FLUX'],error=unit['ERR']),
            converted_units=dict(wavelength='nm',flux='W m-2 nm-1',error='W m-2 nm-1'),
            conversion_factors=dict(wavelength=wave_factor,flux=flux_factor,error=err_factor),
            snr_header=_number(get('SNR')),match_separation_arcsec=candidate['match_separation_arcsec'],
            proposal_id=get('PROG_ID'),quality_mask_rule='finite wave/flux/error, error>0, QUAL==0',
            valid_pixels=int(mask.sum()),total_pixels=len(mask),quality_notes=notes,reference=XSHOOTER_REFERENCE)
    return metadata,dict(wave_nm=wave,flux_w_m2_nm=flux,error_w_m2_nm=error,mask=mask,quality=quality)


def fetch_spectra(discovery, output, product_ids=None):
    directory,data=_load_discovery(discovery)
    selected=list(data['recommended_product_ids'] if product_ids is None else product_ids)
    if not selected or len(set(selected))!=len(selected) or len(selected)>6:raise ValueError('须选择1–6个不同的明确产品；本次没有自动建议时请先检查查询记录')
    candidates={c['product_id']:c for c in data['candidates']}
    if any(pid not in candidates or not candidates[pid]['matched'] for pid in selected):raise ValueError('所选产品不在已核对的位置候选中')
    destination=new_directory(output);(destination/'raw').mkdir();(destination/'normalized').mkdir()
    result=dict(schema_version=1,source_id=data['source_id'],status='running',target=data['target'],products=[],provenance=[],
                discovery_sha256=digest(directory/'discovery.json'),archives=data['archives'],candidates=data['candidates'],
                matching_note=data['matching_note'],fit_executed=False)
    try:
        copied=destination/'raw/discovery.json';copied.write_bytes((directory/'discovery.json').read_bytes())
        result['provenance'].append(dict(file=str(copied),sha256=digest(copied),source_path=str(directory/'discovery.json')))
        for pid in selected:
            candidate=candidates[pid];name=_safe_name(pid)
            raw=_download(candidate['access_url'],destination/'raw'/(name+'_links.xml'),result['provenance'],maximum=5_000_000)
            main,links=parse_datalink(raw,candidate['publisher_id'])
            if urlparse(main['access_url']).hostname not in ('dataportal.eso.org','archive.eso.org'):raise ValueError('ESO主产品链接指向未知站点')
            path=destination/'raw'/(name+'.fits');_download(main['access_url'],path,result['provenance'])
            metadata,arrays=read_eso_fits(path,candidate)
            array_path=destination/'normalized'/(name+'.npz');np.savez_compressed(array_path,**arrays)
            result['provenance'].append(dict(file=str(array_path),sha256=digest(array_path),source_file=str(path.relative_to(destination))))
            metadata.update(arrays_file=str(array_path.relative_to(destination)).replace('\\','/'),raw_file=str(path.relative_to(destination)).replace('\\','/'),
                            source_url=main['access_url'],original_filename=main.get('eso_origfile'))
            result['products'].append(metadata)
            for link in links:
                if link.get('eso_category')=='ANCILLARY.README':
                    _download(link['access_url'],destination/'raw'/(name+'_readme.txt'),result['provenance'],maximum=1_000_000)
        if any(p['instrument']=='XSHOOTER' for p in result['products']):
            _download(XSHOOTER_REFERENCE,destination/'raw/xshooter_release_description.pdf',result['provenance'],maximum=10_000_000)
        result['status']='complete'
    except Exception as error:
        result.update(status='failed',error=str(error));_relative_provenance(result['provenance'],destination);write_json(destination/'spectroscopy.json',result);raise
    _relative_provenance(result['provenance'],destination);write_json(destination/'spectroscopy.json',result)
    write_json(destination/'manifest.json',dict(source_id=data['source_id'],spectroscopy_sha256=digest(destination/'spectroscopy.json')))
    return dict(status='complete',source_id=data['source_id'],output=str(destination),products=len(result['products']),fit_executed=False)


def load_spectra(path, source_id=None):
    directory=Path(path).expanduser().resolve()
    if directory.is_file():directory=directory.parent
    manifest=read_json(directory/'manifest.json')
    if digest(directory/'spectroscopy.json')!=manifest['spectroscopy_sha256']:raise ValueError('光谱摘要校验失败')
    data=read_json(directory/'spectroscopy.json');sid=exact_id(data['source_id'])
    if sid!=manifest['source_id'] or (source_id is not None and sid!=exact_id(source_id)):raise ValueError('档案光谱与XP源编号不一致')
    if data['status']!='complete':raise ValueError('档案光谱下载未完成')
    _verify_files(directory,data['provenance'])
    for product in data['products']:
        path=(directory/product['arrays_file']).resolve()
        if not path.is_relative_to(directory):raise ValueError('光谱数组路径越出资料目录')
        with np.load(path,allow_pickle=False) as arrays:product['arrays']=dict(arrays)
    return data
