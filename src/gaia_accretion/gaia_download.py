"""有界选源、Gaia DR3 XP 下载与相关误差校准；DR4 按实时可用性单独检查。"""
from __future__ import annotations

import ast
import csv
from datetime import datetime, timezone
from importlib.metadata import version
import io
import math
from pathlib import Path
from urllib.parse import urlencode
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen
import xml.etree.ElementTree as ET
import zipfile

import numpy as np

from .classical.xp_workbench import digest, exact_id, new_directory, read_json, write_json

TAP = 'https://gea.esac.esa.int/tap-server/tap/sync'
DATALINK = 'https://gea.esac.esa.int/data-server/data'
AIP_TAP = 'https://gaia.aip.de/tap/sync'
FIELDS = ('source_id','ra','dec','ref_epoch','pmra','pmdec','phot_g_mean_mag','bp_rp','ruwe',
          'has_xp_continuous','has_xp_sampled')


def _release(value):
    value=str(value).lower().replace('gaia ', '')
    if value not in ('dr3','dr4'): raise ValueError('只接受明确的 dr3 或 dr4 发布版本')
    return value


def _fetch(url, destination, provenance, *, limit=5_000_000):
    request=Request(url,headers={'User-Agent':'gaia-xp-workbench/0.4'})
    filename=('raw/' if destination.parent.name=='raw' else '')+destination.name
    try:
        with urlopen(request,timeout=50) as response:
            raw=response.read(limit+1)
            content_type=response.headers.get('Content-Type','')
    except (HTTPError,URLError) as error:
        item=dict(url=url,retrieved_utc=datetime.now(timezone.utc).isoformat(),status='failed',error=str(error))
        if isinstance(error,HTTPError):
            destination.write_bytes(error.read(limit));item.update(file=filename,sha256=digest(destination),http_status=error.code)
        provenance.append(item)
        raise
    if len(raw)>limit: raise ValueError('单次公开查询超过本工具的大小限制')
    destination.write_bytes(raw)
    provenance.append(dict(file=filename,url=url,retrieved_utc=datetime.now(timezone.utc).isoformat(),
                           sha256=digest(destination),bytes=len(raw),content_type=content_type))
    return raw


def _csv(raw):
    text=raw.decode('utf-8-sig')
    if text.lstrip().startswith('<'): raise ValueError('Archive 返回 XML/HTML 错误而非 CSV 数据')
    reader=csv.DictReader(io.StringIO(text))
    if not reader.fieldnames: raise ValueError('Archive CSV 缺少列名')
    return list(reader),reader.fieldnames


def _query(query, destination, provenance):
    url=TAP+'?'+urlencode(dict(REQUEST='doQuery',LANG='ADQL',FORMAT='csv',QUERY=query))
    return _csv(_fetch(url,destination,provenance))


def _finite(value,label):
    value=float(value)
    if not math.isfinite(value): raise ValueError(label+'必须有限')
    return value


def selection_query(source_ids=None, ra_deg=None, dec_deg=None, radius_arcmin=None,
                    g_max=None, bp_rp_min=None, bp_rp_max=None, limit=20):
    """只允许精确源号或有限天区及亮度/颜色条件，不接收任意 ADQL。"""
    if isinstance(limit,bool) or int(limit)!=limit or not 1<=limit<=100: raise ValueError('选源数量上限须为 1–100')
    has_cone=any(x is not None for x in (ra_deg,dec_deg,radius_arcmin))
    if bool(source_ids)==has_cone: raise ValueError('须且只能给出源编号列表或完整圆形天区')
    conditions=[]
    if source_ids:
        ids=list(dict.fromkeys(exact_id(x) for x in source_ids))
        if len(ids)>limit: raise ValueError('源编号数量超过所选上限')
        conditions.append('source_id IN ('+','.join(ids)+')')
    else:
        if any(x is None for x in (ra_deg,dec_deg,radius_arcmin)): raise ValueError('天区需要 RA、Dec 和半径')
        ra,dec,radius=(_finite(x,n) for x,n in zip((ra_deg,dec_deg,radius_arcmin),('RA','Dec','半径')))
        if not 0<=ra<360 or not -90<=dec<=90 or not 0<radius<=60: raise ValueError('坐标无效或半径超过 60 arcmin')
        conditions.append(f"1=CONTAINS(POINT('ICRS',ra,dec),CIRCLE('ICRS',{ra:.12g},{dec:.12g},{radius/60:.12g}))")
    for value,column,operator in ((g_max,'phot_g_mean_mag','<='),(bp_rp_min,'bp_rp','>='),(bp_rp_max,'bp_rp','<=')):
        if value is not None: conditions.append(f'{column}{operator}{_finite(value,column):.12g}')
    if bp_rp_min is not None and bp_rp_max is not None and float(bp_rp_min)>float(bp_rp_max): raise ValueError('颜色下限大于上限')
    # 多取一行，用于识别截断；不把返回的较亮子集冒充完整样本。
    return f"SELECT TOP {int(limit)+1} "+','.join(FIELDS)+' FROM gaiadr3.gaia_source WHERE '+' AND '.join(conditions)+' ORDER BY phot_g_mean_mag ASC,source_id ASC'


def _source_rows(rows):
    result=[]
    for row in rows:
        source=dict(source_id=exact_id(row['source_id']))
        for field in FIELDS[1:]:
            if field.startswith('has_'): source[field]=str(row.get(field,'')).lower() in ('true','1','t')
            else: source[field]=None if row.get(field) in ('',None) else _finite(row[field],field)
        result.append(source)
    return result


def probe_release(output, release='dr4'):
    """检查实时公开 schema；无返回与网络错误分开记录。"""
    release=_release(release);destination=new_directory(output);provenance=[]
    result=dict(release='Gaia '+release.upper(),checked_utc=datetime.now(timezone.utc).isoformat(),provenance=provenance)
    try:
        query=f"SELECT schema_name,description FROM TAP_SCHEMA.schemas WHERE schema_name LIKE '%{release}%'"
        rows,fields=_query(query,destination/'schemas.csv',provenance)
        if 'schema_name' not in fields: raise ValueError('TAP schema 响应缺少名称列')
        result.update(status='available' if rows else 'not_available',schemas=rows,
            download_adapter='validated_dr3_mean_xp' if release=='dr3' else 'not_validated',
            note='公开 schema 可见不等于 XP 下载、DR3/DR4 身份映射和校准已通过验证。')
    except Exception as error:
        result.update(status='query_failed',error=str(error));write_json(destination/'release_status.json',result);raise
    write_json(destination/'release_status.json',result)
    return dict(status=result['status'],release=result['release'],output=str(destination),download_adapter=result['download_adapter'])


def select_sources(output, source_ids=None, ra_deg=None, dec_deg=None, radius_arcmin=None,
                   g_max=None, bp_rp_min=None, bp_rp_max=None, limit=20, release='dr3'):
    release=_release(release)
    if release=='dr4':
        result=probe_release(output,release)
        result.update(status='not_available' if result['status']=='not_available' else 'adapter_not_validated',
                      reason='DR4 需先核验正式表与 DR3 对应源关系；不能直接沿用 DR3 编号。')
        write_json(Path(output)/'selection.json',result)
        return result
    query=selection_query(source_ids,ra_deg,dec_deg,radius_arcmin,g_max,bp_rp_min,bp_rp_max,limit)
    destination=new_directory(output);provenance=[]
    rows,fields=_query(query,destination/'sources.csv',provenance)
    if not set(FIELDS)<=set(fields): raise ValueError('Gaia 主表响应缺少所需字段')
    sources=_source_rows(rows);truncated=len(sources)>limit
    sources=sources[:limit]
    found={s['source_id'] for s in sources}
    result=dict(status='truncated' if truncated else 'complete',release='Gaia DR3',sources=sources,
                source_ids=[s['source_id'] for s in sources],missing_requested=[sid for sid in (source_ids or []) if sid not in found],
                query=query,provenance=provenance,selection_limit=limit,
                units=dict(ra='deg',dec='deg',ref_epoch='Julian year',pmra='mas/yr; includes cos(dec)',pmdec='mas/yr',phot_g_mean_mag='mag',bp_rp='mag',ruwe='dimensionless'),
                note='按位置、亮度和颜色选出候选，不代表星协成员或已确认年轻星；无 XP 的源也保留。')
    write_json(destination/'selection.json',result)
    return dict(status=result['status'],output=str(destination),source_ids=result['source_ids'],missing_requested=result['missing_requested'])


def coefficient_row(raw, source_id):
    rows,fields=_csv(raw)
    if len(rows)!=1 or rows[0].get('source_id')!=exact_id(source_id): raise ValueError('XP 响应不是指定源的唯一记录')
    required={band+'_'+suffix for band in ('bp','rp') for suffix in ('coefficients','coefficient_errors','coefficient_correlations','standard_deviation')}
    if not required<=set(fields): raise ValueError('XP 缺少连续系数或相关误差，不能退回对角误差')
    row=rows[0]
    for band in ('bp','rp'):
        arrays=[np.asarray(ast.literal_eval(row[band+'_'+suffix]),dtype=float) for suffix in ('coefficients','coefficient_errors','coefficient_correlations')]
        coefficient,error,correlation=arrays;n=len(coefficient)
        if n==0 or coefficient.ndim!=1 or error.shape!=(n,) or correlation.shape!=(n*(n-1)//2,): raise ValueError('XP 系数或相关系数长度不符')
        if not all(np.isfinite(x).all() for x in arrays) or np.any(error<=0): raise ValueError('XP 系数或误差无效')
        if _finite(row[band+'_standard_deviation'],'standard_deviation')<=0: raise ValueError('XP 系数归一化误差无效')
    return row


def aip_votable_to_csv(raw, source_id):
    """AIP 原 XML 单独保存；仅改序列化，保留源号和数字词串。"""
    root=ET.fromstring(raw)
    info={x.get('name'):x.get('value') for x in root.findall('.//{*}INFO')}
    if info.get('QUERY_STATUS')!='OK' or info.get('SOURCE')!='gaiadr3.xp_continuous_mean_spectrum':
        raise ValueError('AIP 返回的状态或光谱表身份不符')
    tables=root.findall('.//{*}TABLE')
    if len(tables)!=1: raise ValueError('AIP 响应没有唯一光谱表')
    table=tables[0];fields=table.findall('{*}FIELD');rows=table.findall('.//{*}TR')
    if len(rows)!=1: raise ValueError('AIP 单源查询未返回唯一行')
    cells=rows[0].findall('{*}TD')
    if len(cells)!=len(fields): raise ValueError('AIP 数据列数不符')
    row={}
    for field,cell in zip(fields,cells):
        text=(cell.text or '').strip()
        row[field.get('name')]='['+','.join(text.split())+']' if field.get('arraysize') and field.get('datatype') in ('float','double') else text
    stream=io.StringIO();writer=csv.DictWriter(stream,fieldnames=list(row));writer.writeheader();writer.writerow(row)
    result=stream.getvalue().encode('utf-8')
    coefficient_row(result,source_id)
    return result


def factor_from_coefficients(row, design, merge, symmetric):
    """传播各臂完整系数协方差；BP/RP 跨臂协方差未发布，采用零。"""
    flux=np.zeros(len(next(iter(merge.values()))));factors=[]
    for band in ('bp','rp'):
        coefficients=np.asarray(ast.literal_eval(row[band+'_coefficients']),float)
        errors=np.asarray(ast.literal_eval(row[band+'_coefficient_errors']),float)
        correlation=symmetric(np.asarray(ast.literal_eval(row[band+'_coefficient_correlations']),float),len(coefficients))
        covariance=errors[:,None]*correlation*errors[None,:]
        values,vectors=np.linalg.eigh((covariance+covariance.T)/2)
        if values.min() < -values.max()*1e-8: raise ValueError('系数协方差不是半正定矩阵')
        root=vectors*np.sqrt(np.maximum(values,0))
        matrix=np.asarray(design[band]);weight=np.asarray(merge[band])
        factors.append((matrix.T@root)*weight[:,None])
        flux+=weight*(coefficients@matrix)
    factor=np.column_stack(factors)
    return flux,factor


def calibrate_dr3(raw_path, source_id, destination, metadata_path=None):
    try:
        from gaiaxpy import calibrate
        from gaiaxpy.core.generic_functions import array_to_symmetric_matrix
        from gaiaxpy.core.satellite import BANDS
        import gaiaxpy.calibrator.calibrator as calibrator
    except ImportError as error: raise RuntimeError('请安装 Gaia 下载附加依赖：pip install ".[gaia]"') from error
    if version('GaiaXPy')!='2.1.2': raise RuntimeError('本协方差适配器只验证了 GaiaXPy 2.1.2')
    row=coefficient_row(raw_path.read_bytes(),source_id)
    wave=np.arange(336.,1021.,2.)
    objects,weights=calibrator.__generate_xp_matrices_and_merge('calibrator',wave,'v375wi','v142r')
    design={str(b):objects[b].get_design_matrix() for b in BANDS};merge={str(b):np.asarray(weights[b]) for b in BANDS}
    flux,factor=factor_from_coefficients(row,design,merge,array_to_symmetric_matrix)
    official,_=calibrate(str(raw_path),sampling=wave,truncation=False,save_file=False)
    np.testing.assert_allclose(flux,official.iloc[0]['flux'],rtol=1e-6,atol=0)
    error=np.linalg.norm(factor,axis=1)
    np.testing.assert_allclose(error,official.iloc[0]['flux_error'],rtol=1e-6,atol=0)
    metadata=read_json(metadata_path) if metadata_path is not None else {}
    if metadata and exact_id(metadata.get('source_id'))!=source_id: raise ValueError('提供先验的源编号与下载源不一致')
    metadata.update(source_id=source_id,name=metadata.get('name',source_id),release='Gaia DR3',product='mean_xp',
        calibration='externally_calibrated',calibration_version='GaiaXPy 2.1.2; v375wi/v142r; no additional Huang correction',
        wavelength_unit='nm',flux_unit='W m-2 nm-1',epoch_time=None,bp_rp_cross_covariance='assumed_zero',
        input_reference='Gaia DR3 XP continuous coefficients; provider and original response in download.json; raw/xp_continuous.csv; SHA256='+digest(raw_path))
    np.savez_compressed(destination/'spectrum.npz',source_id=np.array(source_id),wave=wave,flux=flux,
                        noise_factor=factor,error=error,mask=np.isfinite(flux)&np.isfinite(error)&(error>0))
    write_json(destination/'metadata.json',metadata)
    audit=dict(gaiaxpy='2.1.2',sampling_nm=[336,1020,2],truncation=False,
        noise_factor_shape=list(factor.shape),flux_and_error_match_gaiaxpy=True,bp_rp_cross_covariance='assumed_zero',
        formal_covariance='Within-band coefficient covariance retained; no diagonal approximation',
        raw_sha256=digest(raw_path),fit_executed=False)
    missing=[k for k in ('spt_num','av_mag','teff_k','prior_reference') if metadata.get(k) is None]
    if missing:
        audit.update(analysis_status='awaiting_priors',missing_priors=missing)
    else:
        from .classical.xp_workbench import load_input,inspect
        inspection=inspect(load_input(destination/'spectrum.npz',destination/'metadata.json'))
        write_json(destination/'inspection.json',inspection)
        audit.update(analysis_status='ready_for_fit' if inspection['ready_for_fit'] else 'not_ready',blockers=inspection['blockers'])
    write_json(destination/'calibration.json',audit)
    return audit


def download_xp(source_id, output, release='dr3', metadata_path=None, calibrate=True):
    source_id=exact_id(source_id);release=_release(release)
    if metadata_path is not None and exact_id(read_json(metadata_path).get('source_id'))!=source_id:
        raise ValueError('提供先验的源编号与下载源不一致')
    if release=='dr4':
        result=probe_release(output,release)
        result.update(status='not_available' if result['status']=='not_available' else 'adapter_not_validated',
            source_id=source_id,reason='DR4 的对应源映射、XP 产品和协方差校准尚未核验；未把 DR3 源编号用作 DR4 编号。',fit_executed=False)
        write_json(Path(output)/'download.json',result)
        return result
    destination=new_directory(output);raw_dir=destination/'raw';raw_dir.mkdir();provenance=[]
    result=dict(source_id=source_id,release='Gaia DR3',status='running',provenance=provenance,fit_executed=False)
    if metadata_path is not None:result['prior_metadata_sha256']=digest(metadata_path)
    try:
        query='SELECT '+','.join(FIELDS)+' FROM gaiadr3.gaia_source WHERE source_id='+source_id
        rows,_=_query(query,raw_dir/'source.csv',provenance)
        if len(rows)!=1 or rows[0].get('source_id')!=source_id: raise ValueError('Gaia 未返回唯一对应源')
        source=_source_rows(rows)[0];result['source']=source
        if not source['has_xp_continuous']:
            result.update(status='no_xp',analysis_status='not_available')
        else:
            params=dict(RETRIEVAL_TYPE='XP_CONTINUOUS',ID=source_id,RELEASE='Gaia DR3',DATA_STRUCTURE='DATAMODEL_GAIA',FORMAT='csv')
            try:
                raw=_fetch(DATALINK+'?'+urlencode(params),raw_dir/'response.dat',provenance)
                result['provider']='ESA Archive DataLink'
            except URLError:
                # ESA 公开服务不可用时，仅访问已核验的同版 DPAC 合作档案表一次。
                query='SELECT TOP 2 * FROM gaiadr3.xp_continuous_mean_spectrum WHERE source_id='+source_id
                url=AIP_TAP+'?'+urlencode(dict(REQUEST='doQuery',LANG='ADQL',FORMAT='votable',QUERY=query))
                raw=aip_votable_to_csv(_fetch(url,raw_dir/'aip_coefficients.xml',provenance),source_id)
                result.update(provider='Gaia@AIP',provider_reference='https://gaia.aip.de/metadata/gaiadr3/xp_continuous_mean_spectrum/',
                              serialization_note='原 VOTable 转为 GaiaXPy CSV；未改变系数、误差或相关系数数值。')
            if zipfile.is_zipfile(io.BytesIO(raw)):
                with zipfile.ZipFile(io.BytesIO(raw)) as z:
                    names=[n for n in z.namelist() if n.lower().endswith('.csv')]
                    if len(names)!=1 or z.getinfo(names[0]).file_size>5_000_000: raise ValueError('单源 XP 压缩包结构或大小异常')
                    raw=z.read(names[0])
            coefficient_row(raw,source_id)
            raw_path=raw_dir/'xp_continuous.csv';raw_path.write_bytes(raw)
            result['coefficient_sha256']=digest(raw_path)
            if calibrate:
                audit=calibrate_dr3(raw_path,source_id,destination,metadata_path)
                result.update(status='complete',analysis_status=audit['analysis_status'])
            else: result.update(status='downloaded',analysis_status='coefficients_only')
        result['files_sha256']={str(p.relative_to(destination)).replace('\\','/'):digest(p) for p in destination.rglob('*') if p.is_file()}
    except Exception as error:
        result.update(status='failed',error=str(error));write_json(destination/'download.json',result);raise
    write_json(destination/'download.json',result)
    return dict(status=result['status'],source_id=source_id,output=str(destination),analysis_status=result['analysis_status'],fit_executed=False)
