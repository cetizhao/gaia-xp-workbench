"""测光比较检查通量单位、源身份以及报告只读性。"""
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import numpy as np
from gaia_accretion import reporting
from gaia_accretion.classical import xp_workbench as work
from gaia_accretion.photometry_report import xp_fnu_jy
from test_reporting import saved_run, fake_plots


class PhotometryReportTests(unittest.TestCase):
    def test_flux_density_conversion(self):
        # 1 Jy在500 nm对应1.199169832e-14 W m⁻² nm⁻¹。
        self.assertAlmostEqual(float(xp_fnu_jy(500.,1.199169832e-14)),1.)
        np.testing.assert_allclose(xp_fnu_jy([500.,1000.],[1.199169832e-14]*2),[1.,4.])
        self.assertLess(float(xp_fnu_jy(500.,-1e-14)),0.)

    def test_joint_report_offline_and_readonly(self):
        with tempfile.TemporaryDirectory() as temp:
            base=Path(temp);run=base/'run';saved_run(run)
            (base/'phot').mkdir()
            phot=base/'phot/photometry.json';phot.write_text('{}')
            data=dict(source_id='6719035052475592576',target=dict(ra_deg=287.44136196,dec_deg=-37.07405919,epoch_year=2016.),
                surveys=[dict(name='APASS',catalogue='II/336/apass9',selected_id='target',status='matched',epoch_year=2012.,separation_arcsec=.3,candidates=[{}])],
                measurements=[dict(survey='APASS',band='g',wavelength_um=.463927,mag=14.,mag_error=.07,system='AB',
                                   flux_jy=.009,flux_error_jy=.0006,is_upper_limit=False,usable=True,quality='0')])
            before={p.name:work.digest(p) for p in run.iterdir()}
            def photo_plot(destination,*args):
                (destination/'photometry.png').write_bytes((destination/'overview.png').read_bytes())
                return 'photometry.png'
            with patch('gaia_accretion.photometry.load_photometry',return_value=data) as loader, \
                 patch.object(work,'fit',side_effect=AssertionError('不得拟合')), \
                 patch('gaia_accretion.report_plots.render_overview',side_effect=fake_plots), \
                 patch('gaia_accretion.photometry_report.render_photometry',side_effect=photo_plot):
                reporting.build_report(run,base/'report',photometry=phot)
                loader.assert_called_once_with(phot.resolve(),source_id='6719035052475592576')
            self.assertEqual(before,{p.name:work.digest(p) for p in run.iterdir()})
            manifest=work.read_json(base/'report/report_manifest.json')
            self.assertEqual(manifest['photometry']['sha256'],work.digest(phot))
            self.assertFalse(manifest['fit_executed'])
            html=(base/'report/report.html').read_text(encoding='utf-8')
            self.assertEqual(html.count('src="data:image/png;base64,'),4)
            self.assertIn('Fν (Jy)',html)

    def test_unknown_xp_units_rejected_for_photometry(self):
        with tempfile.TemporaryDirectory() as temp:
            base=Path(temp);run=base/'run';saved_run(run)
            loaded=list(reporting.load_saved(run))
            loaded[1]['metadata']['flux_unit']='unknown'
            with patch.object(reporting,'load_saved',return_value=tuple(loaded)),self.assertRaisesRegex(ValueError,'单位'):
                reporting.build_report(run,base/'report',photometry=base/'photometry.json')
            self.assertFalse((base/'report').exists())
