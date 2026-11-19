"""验证档案光谱身份、单位、质量掩码与观测选择。"""
from pathlib import Path
import tempfile
import unittest

import numpy as np
from gaia_accretion import spectroscopy as s
from gaia_accretion.classical.xp_workbench import digest, write_json

try:
    from astropy.io import fits
except ImportError:
    fits=None

SID='6719035052475592576'


def candidate():
    return dict(product_id='ADP.test',instrument='XSHOOTER',mjd_start=59705.0,exposure_s=100.,resolving_power=10000.,obs_id='1',match_separation_arcsec=.1)


def save_fits(path,unit='erg cm-2 s-1 Angstrom-1'):
    primary=fits.PrimaryHDU()
    for k,v in dict(ARCFILE='ADP.test.fits',INSTRUME='XSHOOTER',FLUXCAL='ABSOLUTE',OBJECT='test',
                    **{'DATE-OBS':'2022-05-06T00:00:00','MJD-OBS':59705.,'ESO QC SLITW':'5.0x11','ESO SEQ ARM':'UVB'}).items():primary.header[k]=v
    columns=[fits.Column(name=n,format='3D' if n!='QUAL' else '3J',unit=u,array=[v]) for n,u,v in
             [('WAVE','nm',[400,500,600]),('FLUX',unit,[-1,2,3]),('ERR',unit,[.1,.2,.3]),('QUAL',None,[0,1,0])]]
    table=fits.BinTableHDU.from_columns(columns);table.header['TUCD1']='em.wl;obs.atmos'
    fits.HDUList([primary,table]).writeto(path)


class SpectroscopyTests(unittest.TestCase):
    @unittest.skipIf(fits is None,'需要可选Astropy读取FITS')
    def test_flux_conversion_preserves_negative_and_masks_bad_pixels(self):
        with tempfile.TemporaryDirectory() as temp:
            p=Path(temp)/'test.fits';save_fits(p)
            metadata,arrays=s.read_eso_fits(p,candidate())
            np.testing.assert_allclose(arrays['flux_w_m2_nm'],[-.01,.02,.03])
            np.testing.assert_array_equal(arrays['mask'],[True,False,True])
            self.assertEqual(metadata['role'],'wide');self.assertEqual(metadata['wavelength_medium'],'air')

    @unittest.skipIf(fits is None,'需要可选Astropy读取FITS')
    def test_unknown_flux_units_and_wrong_product_rejected(self):
        with tempfile.TemporaryDirectory() as temp:
            p=Path(temp)/'test.fits';save_fits(p,unit='adu')
            with self.assertRaises(ValueError):s.read_eso_fits(p,candidate())
        with tempfile.TemporaryDirectory() as temp:
            p=Path(temp)/'test.fits';save_fits(p)
            c=candidate();c['product_id']='ADP.other'
            with self.assertRaisesRegex(ValueError,'编号'):s.read_eso_fits(p,c)

    def test_selection_retains_same_visit_optical_settings(self):
        records=[]
        for pid,low,high,res in [('uvn',300,556,9000),('uvw',300,556,1000),('visn',534,1020,18000),('visw',534,1020,1500),('nir',994,2479,10000)]:
            records.append(dict(product_id=pid,instrument='XSHOOTER',matched=True,wave_min_nm=low,wave_max_nm=high,resolving_power=res,obs_id='visit',mjd_start=59705.))
        self.assertEqual(set(s.recommended_products(records)),{'uvn','uvw','visn','visw'})
        self.assertEqual(s.recommended_products([records[0]]),[])

    def test_datalink_requires_matching_primary_product(self):
        raw=b'''<VOTABLE><RESOURCE><TABLE><FIELD name="ID"/><FIELD name="semantics"/><FIELD name="access_url"/>
        <DATA><TABLEDATA><TR><TD>ivo://test</TD><TD>#this</TD><TD>https://archive.eso.org/test</TD></TR></TABLEDATA></DATA></TABLE></RESOURCE></VOTABLE>'''
        self.assertEqual(s.parse_datalink(raw,'ivo://test')[0]['semantics'],'#this')
        with self.assertRaises(ValueError):s.parse_datalink(raw,'ivo://wrong')

    def test_saved_bundle_identity_and_raw_integrity(self):
        with tempfile.TemporaryDirectory() as temp:
            p=Path(temp);np.savez(p/'arrays.npz',wave_nm=[400.,500.],flux_w_m2_nm=[1.,2.],error_w_m2_nm=[.1,.1],mask=[True,True])
            (p/'raw.fits').write_bytes(b'raw')
            data=dict(source_id=SID,status='complete',products=[dict(arrays_file='arrays.npz')],
                      provenance=[dict(file=n,sha256=digest(p/n)) for n in ['raw.fits','arrays.npz']])
            write_json(p/'spectroscopy.json',data);write_json(p/'manifest.json',dict(source_id=SID,spectroscopy_sha256=digest(p/'spectroscopy.json')))
            self.assertEqual(s.load_spectra(p,SID)['products'][0]['arrays']['wave_nm'][0],400.)
            with self.assertRaises(ValueError):s.load_spectra(p,'123')
            (p/'raw.fits').write_bytes(b'changed')
            with self.assertRaises(ValueError):s.load_spectra(p,SID)


if __name__=='__main__':unittest.main()
