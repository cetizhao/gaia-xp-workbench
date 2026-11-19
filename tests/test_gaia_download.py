"""Gaia 下载检查源身份、完整误差、选样截断和未开放发布的处理。"""
import csv
import io
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import numpy as np
from gaia_accretion import gaia_download as g
from gaia_accretion.classical.xp_workbench import read_json,write_json

SID='6719035052475592576'


def row(has_xp='true'):
    return dict(source_id=SID,ra='287.44136',dec='-37.07406',ref_epoch='2016',pmra='5.368',pmdec='-27.072',
                phot_g_mean_mag='12.248',bp_rp='2.132',ruwe='2.102',has_xp_continuous=has_xp,has_xp_sampled=has_xp)


class GaiaDownloadTests(unittest.TestCase):
    def test_selection_keeps_exact_ids_and_bounds(self):
        query=g.selection_query([SID])
        self.assertIn(SID,query)
        self.assertNotIn('has_xp_continuous=true',query)
        self.assertEqual(g._source_rows([row()])[0]['source_id'],SID)
        with self.assertRaises(ValueError):g.selection_query([float(SID)])
        with self.assertRaises(ValueError):g.selection_query(ra_deg=1,dec_deg=2,radius_arcmin=61)
        with self.assertRaises(ValueError):g.selection_query(ra_deg=1,dec_deg=2,radius_arcmin=1,limit=1000)

    def test_truncated_candidate_list_is_explicit(self):
        with tempfile.TemporaryDirectory() as temp:
            second=row();second['source_id']='6719035052475592577'
            with patch.object(g,'_query',return_value=([row(),second],list(g.FIELDS))):
                result=g.select_sources(Path(temp)/'selection',ra_deg=287,dec_deg=-37,radius_arcmin=1,limit=1)
            self.assertEqual(result['status'],'truncated')
            self.assertEqual(result['source_ids'],[SID])

    def test_probe_empty_is_different_from_failed_query(self):
        with tempfile.TemporaryDirectory() as temp:
            with patch.object(g,'_query',return_value=([],['schema_name','description'])):
                result=g.probe_release(Path(temp)/'empty')
            self.assertEqual(result['status'],'not_available')
            with patch.object(g,'_query',side_effect=OSError('offline')),self.assertRaises(OSError):
                g.probe_release(Path(temp)/'failed')
            self.assertEqual(read_json(Path(temp)/'failed/release_status.json')['status'],'query_failed')

    def test_dr4_does_not_reuse_dr3_download(self):
        with tempfile.TemporaryDirectory() as temp:
            with patch.object(g,'_query',return_value=([],['schema_name','description'])), \
                 patch.object(g,'_fetch',side_effect=AssertionError('不能调用 DR3 DataLink')), \
                 patch.object(g,'calibrate_dr3',side_effect=AssertionError('不能调用 DR3 校准')):
                result=g.download_xp(SID,Path(temp)/'dr4',release='dr4')
            self.assertEqual(result['status'],'not_available')
            self.assertFalse(result['fit_executed'])

    def test_coefficient_input_checks_identity_and_missing_covariance(self):
        values=dict(source_id=SID)
        for band in ('bp','rp'):
            values.update({band+'_coefficients':'[1,2]',band+'_coefficient_errors':'[2,3]',
                           band+'_coefficient_correlations':'[0.5]',band+'_standard_deviation':'10'})
        def encoded():
            stream=io.StringIO();writer=csv.DictWriter(stream,fieldnames=list(values));writer.writeheader();writer.writerow(values)
            return stream.getvalue().encode()
        self.assertEqual(g.coefficient_row(encoded(),SID)['source_id'],SID)
        with self.assertRaises(ValueError):g.coefficient_row(encoded(),'123')
        del values['rp_coefficient_correlations']
        with self.assertRaises(ValueError):g.coefficient_row(encoded(),SID)

    def test_factor_preserves_correlated_errors_without_double_scaling(self):
        values={}
        for b in ('bp','rp'):
            values.update({b+'_coefficients':'[1,2]',b+'_coefficient_errors':'[2,3]',
                           b+'_coefficient_correlations':'[0.5]',b+'_standard_deviation':'10'})
        matrices={b:np.eye(2) for b in ('bp','rp')};weights={b:np.ones(2)*.5 for b in matrices}
        symmetric=lambda x,n:np.array([[1,x[0]],[x[0],1]])
        flux,factor=g.factor_from_coefficients(values,matrices,weights,symmetric)
        np.testing.assert_allclose(flux,[1,2])
        np.testing.assert_allclose(factor@factor.T,np.array([[4,3],[3,9]])*.5)

    def test_aip_serialization_preserves_id_and_coefficients(self):
        fields=['<FIELD name="source_id" datatype="long" ID="datalinkID"/>'];values=[f'<TD>{SID}</TD>']
        for band in ('bp','rp'):
            for suffix,text in [('coefficients','1.2345678901234567 2'),('coefficient_errors','2 3'),('coefficient_correlations','0.5')]:
                fields.append(f'<FIELD name="{band}_{suffix}" datatype="double" arraysize="*"/>');values.append(f'<TD>{text}</TD>')
            fields.append(f'<FIELD name="{band}_standard_deviation" datatype="float"/>');values.append('<TD>10</TD>')
        raw=('<VOTABLE><RESOURCE><INFO name="QUERY_STATUS" value="OK"/><INFO name="SOURCE" value="gaiadr3.xp_continuous_mean_spectrum"/>'
             +'<TABLE>'+''.join(fields)+'<DATA><TABLEDATA><TR>'+''.join(values)+'</TR></TABLEDATA></DATA></TABLE></RESOURCE></VOTABLE>').encode()
        result=g.coefficient_row(g.aip_votable_to_csv(raw,SID),SID)
        self.assertEqual(result['source_id'],SID)
        self.assertIn('1.2345678901234567',result['bp_coefficients'])

    def test_no_xp_and_wrong_priors_cannot_start_calibration(self):
        with tempfile.TemporaryDirectory() as temp:
            base=Path(temp)
            with patch.object(g,'_query',return_value=([row('false')],list(g.FIELDS))), \
                 patch.object(g,'_fetch',side_effect=AssertionError('没有 XP 不下载')), \
                 patch.object(g,'calibrate_dr3',side_effect=AssertionError('没有 XP 不校准')):
                result=g.download_xp(SID,base/'missing')
            self.assertEqual(result['status'],'no_xp')
            write_json(base/'priors.json',dict(source_id='123'))
            with self.assertRaises(ValueError):g.download_xp(SID,base/'wrong',metadata_path=base/'priors.json')
            self.assertFalse((base/'wrong').exists())
