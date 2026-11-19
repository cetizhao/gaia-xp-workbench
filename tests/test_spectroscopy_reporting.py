"""档案光谱比较保留绝对尺度、缺测区和原XP后验。"""
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import numpy as np
from gaia_accretion import reporting
from gaia_accretion.classical import xp_workbench as work
from gaia_accretion.spectroscopy_report import bin_mean_flux
from test_reporting import saved_run, fake_plots


class SpectroscopyReportTests(unittest.TestCase):
    def test_band_average_conserves_linear_flux(self):
        wave=np.arange(300.,901.,.1);flux=wave*2+10
        edges=np.arange(335.,905.,5.)
        binned=bin_mean_flux(wave,flux,np.ones(len(wave),bool),edges)
        np.testing.assert_allclose(binned,edges[:-1]+edges[1:]+10)
        self.assertAlmostEqual(np.sum(binned*np.diff(edges)),(edges[-1]**2+10*edges[-1])-(edges[0]**2+10*edges[0]))

    def test_masked_gaps_are_not_interpolated_away(self):
        wave=np.arange(400.,421.,.1);flux=np.ones(len(wave))
        mask=~((wave>407)&(wave<413))
        binned=bin_mean_flux(wave,flux,mask,np.arange(400.,421.,5.))
        np.testing.assert_allclose(binned[[0,3]],1.)
        self.assertTrue(np.isnan(binned[1:3]).all())

    def test_report_reuses_result_and_records_spectrum_input(self):
        with tempfile.TemporaryDirectory() as temp:
            base=Path(temp);run=base/'run';saved_run(run)
            folder=base/'spectra';folder.mkdir();path=folder/'spectroscopy.json';path.write_text('{}')
            p=dict(product_id='ESO test',instrument='XSHOOTER',arm='VIS',obs_time='2022-05-06T10:00:00',
                   role='wide',slit_width_arcsec=5.,resolving_power=1512.,match_separation_arcsec=.4,
                   original_units='erg cm-2 s-1 Angstrom-1',flux_calibration='ABSOLUTE',
                   wavelength_medium='air',spectral_frame='TOPOCENT')
            data=dict(source_id='6719035052475592576',products=[p])
            before={p.name:work.digest(p) for p in run.iterdir()}
            def plot(destination,*args):
                (destination/'spectroscopy.png').write_bytes((destination/'overview.png').read_bytes())
                return 'spectroscopy.png',dict(red_flux_ratios=[],xp_refitted=False)
            with patch('gaia_accretion.spectroscopy.load_spectra',return_value=data) as loader, \
                 patch.object(work,'fit',side_effect=AssertionError('不得拟合')), \
                 patch('gaia_accretion.report_plots.render_overview',side_effect=fake_plots), \
                 patch('gaia_accretion.spectroscopy_report.render_spectroscopy',side_effect=plot):
                reporting.build_report(run,base/'report',spectra=folder)
                loader.assert_called_once_with(path.resolve(),source_id=data['source_id'])
            self.assertEqual(before,{p.name:work.digest(p) for p in run.iterdir()})
            manifest=work.read_json(base/'report/report_manifest.json')
            self.assertEqual(manifest['spectroscopy']['sha256'],work.digest(path))
            self.assertFalse(manifest['fit_executed'])
            html=(base/'report/report.html').read_text(encoding='utf-8')
            self.assertIn('2022-05-06T10:00:00',html);self.assertIn('1512',html)
            self.assertEqual(html.count('src="data:image/png;base64,'),4)
