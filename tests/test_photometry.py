"""测光验证身份、单位、位置多解和质量旗标，不调用网络或 XP 拟合。"""
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from gaia_accretion import photometry as p
from gaia_accretion.classical.xp_workbench import digest, write_json

SID = '6719035052475592576'


def target():
    return dict(ra_deg=100., dec_deg=0., epoch_year=2016., pmra_mas_yr=100., pmdec_mas_yr=-50.)


class PhotometryTests(unittest.TestCase):
    def test_flux_and_proper_motion_units(self):
        flux, error=p.magnitude_to_flux(10., .1, 3631.)
        self.assertAlmostEqual(flux,.3631)
        self.assertAlmostEqual(error/flux,.09210340372)
        ra,dec=p.propagate_position(target(),2000.)
        self.assertAlmostEqual((ra-100)*3600,-1.6)
        self.assertAlmostEqual(dec*3600,.8)

    def test_ambiguous_match_does_not_choose_nearest(self):
        survey=p.SURVEYS[0]
        rows=[dict(RAJ2000='100',DEJ2000='0'),dict(RAJ2000='100.0001',DEJ2000='0')]
        candidates,status,chosen=p.match_candidates(rows,target(),survey,3)
        self.assertEqual(len(candidates),2)
        self.assertEqual(status,'ambiguous'); self.assertIsNone(chosen)
        _,status,chosen=p.match_candidates([],target(),survey,3)
        self.assertEqual(status,'no_match');self.assertIsNone(chosen)

    def test_flags_distinguish_upper_limit_contamination_and_single_observation(self):
        wise=dict(object_id='WISE test',epoch_year=2010.5,separation_arcsec=.2,
                  raw=dict(qph='AAUZ',ccf='d000',ex='0',W1mag='10',e_W1mag='.1',
                           W2mag='10',e_W2mag='.1',W3mag='10',e_W3mag='',W4mag='10',e_W4mag=''))
        values=p.measurements_for(wise,p.SURVEYS[2])
        self.assertFalse(values[0]['usable']);self.assertFalse(values[0]['is_upper_limit'])
        self.assertTrue(values[1]['usable'])
        self.assertTrue(values[2]['usable']);self.assertTrue(values[2]['is_upper_limit'])
        self.assertIsNone(values[2]['flux_error_jy']);self.assertEqual(values[2]['upper_limit_confidence'],.95)
        self.assertFalse(values[3]['usable']);self.assertFalse(values[3]['is_upper_limit'])
        apass=dict(object_id='APASS test',epoch_year=None,separation_arcsec=.2,
                   raw={"g'mag":'10',"e_g'mag":'.1',"u_e_g'mag":'1'})
        value=p.measurements_for(apass,p.SURVEYS[0])[0]
        self.assertTrue(value['usable']);self.assertIn('Poisson',value['error_note'])
        mass=dict(object_id='2MASS test',epoch_year=2000.,separation_arcsec=.1,
                  raw=dict(Qflg='UAA',Cflg='000',Xflg='0',Aflg='0',Jmag='16'))
        limit=p.measurements_for(mass,p.SURVEYS[1])[0]
        self.assertTrue(limit['is_upper_limit']);self.assertIsNone(limit['upper_limit_confidence'])
        self.assertIsNone(limit['flux_error_jy'])

    def test_votable_preserves_exact_id_and_rejects_service_error(self):
        raw=f'''<VOTABLE><RESOURCE><TABLE name="I/355/gaiadr3"><FIELD name="Source" datatype="long"/>
        <DATA><TABLEDATA><TR><TD>{SID}</TD></TR></TABLEDATA></DATA></TABLE></RESOURCE></VOTABLE>'''.encode()
        rows,_,_=p.parse_votable(raw,'I/355/gaiadr3')
        self.assertEqual(rows[0]['Source'],SID)
        with self.assertRaises(ValueError):
            p.parse_votable(b'<VOTABLE><INFO name="QUERY_STATUS" value="ERROR">failed</INFO></VOTABLE>','x')
        with self.assertRaises(ValueError):p._check_units([dict(name='RA',unit='rad')],dict(RA='deg'))
        empty=b'<VOTABLE><RESOURCE><TABLE name="x"><FIELD name="RA"/><!--  EMPTY result, no DATA part  --></TABLE></RESOURCE></VOTABLE>'
        self.assertEqual(p.parse_votable(empty,'x')[0],[])
        with self.assertRaises(ValueError):p.parse_votable(empty.replace(b'<!--  EMPTY result, no DATA part  -->',b''),'x')

    def test_invalid_response_preserved_separately_from_mirror(self):
        from io import BytesIO
        invalid=b'<invalid/>'
        valid=b'<VOTABLE><RESOURCE><TABLE name="x"><FIELD name="RA"/><!--  EMPTY result, no DATA part  --></TABLE></RESOURCE></VOTABLE>'
        with tempfile.TemporaryDirectory() as folder:
            directory=Path(folder);(directory/'raw').mkdir();records=[]
            with patch.object(p,'urlopen',side_effect=[BytesIO(invalid),BytesIO(valid)]):
                rows,_,_,_=p._download(directory,'survey',{'-source':'x'},records)
            self.assertEqual(rows,[])
            self.assertEqual(len({item['file'] for item in records}),2)
            self.assertTrue(all(digest(directory/item['file'])==item['sha256'] for item in records))

    def test_saved_bundle_integrity_and_identity(self):
        with tempfile.TemporaryDirectory() as folder:
            directory=Path(folder);raw=directory/'raw.xml';raw.write_text('saved catalogue')
            data=dict(source_id=SID,status='complete',provenance=[dict(file='raw.xml',sha256=digest(raw))])
            write_json(directory/'photometry.json',data)
            write_json(directory/'manifest.json',dict(source_id=SID,photometry_sha256=digest(directory/'photometry.json')))
            self.assertEqual(p.load_photometry(directory/'photometry.json',SID)['source_id'],SID)
            with self.assertRaises(ValueError):p.load_photometry(directory,'123')
            raw.write_text('changed')
            with self.assertRaises(ValueError):p.load_photometry(directory,SID)

    def test_failed_download_is_not_no_match(self):
        fields=[dict(name=n,unit=u,ref='gaia') for n,u in [('RA_ICRS','deg'),('DE_ICRS','deg'),('pmRA','mas/yr'),('pmDE','mas/yr')]]
        gaia=([dict(Source=SID,RA_ICRS='100',DE_ICRS='0',pmRA='100',pmDE='-50')],fields,[dict(ID='gaia',epoch='2016')],'https://example.test')
        with tempfile.TemporaryDirectory() as folder:
            with patch.object(p,'_download',side_effect=[gaia,RuntimeError('offline'),RuntimeError('offline'),RuntimeError('offline')]):
                result=p.fetch_photometry(SID,Path(folder)/'new')
            self.assertEqual(result['status'],'partial')
            data=p.load_photometry(result['output'])
            self.assertTrue(all(s['status']=='query_failed' for s in data['surveys']))
            self.assertEqual(data['measurements'],[])


if __name__=='__main__':unittest.main()
