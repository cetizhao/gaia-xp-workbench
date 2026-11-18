"""单谱输入的身份、误差和适用范围回归。"""

import unittest

import numpy as np

import tempfile

from pathlib import Path

from gaia_accretion.classical import xp_workbench as work

def fixture():
    wave = np.arange(336., 1021., 2.)
    meta = dict(source_id="6719035052475592576", release="Gaia DR3", product="mean_xp",
                calibration="externally_calibrated", calibration_version="test fixture",
                wavelength_unit="nm", flux_unit="W m-2 nm-1", input_reference="unit test",
                prior_reference="unit test", spt_num=73., av_mag=.2, teff_k=3400.)
    return wave, np.full(len(wave), 1e-15), np.ones(len(wave), bool), np.full((len(wave), 1), 1e-17), meta

class SpectrumInputTests(unittest.TestCase):
    def test_identity_never_roundtrips_through_float(self):
        for value in [6719035052475592576, 6.719035052475592e18, "6.719035e18", "00123"]:
            with self.subTest(value=value), self.assertRaises(ValueError):
                work.exact_id(value)
        self.assertEqual(work.exact_id("6719035052475592576"), "6719035052475592576")

    def test_common_mode_noise_does_not_average_down(self):
        spectrum = work.validate_spectrum(*fixture())
        info = work.inspect(spectrum)
        self.assertTrue(info["ready_for_fit"])
        for band in info["bands"]:
            self.assertAlmostEqual(band["error"]/1e-17, 1., places=12)
        self.assertGreater(info["bands"][0]["error"], 5*spectrum.error[0]/np.sqrt(101))

    def test_negative_flux_and_masked_nan_are_handled_separately(self):
        wave, flux, mask, factor, meta = fixture()
        flux[0] = -1e-17
        flux[1] = np.nan; mask[1] = False
        spectrum = work.validate_spectrum(wave, flux, mask, factor, meta)
        self.assertEqual(spectrum.flux[0], -1e-17)
        self.assertTrue(np.isfinite(spectrum.flux).all())
        self.assertEqual(work.inspect(spectrum)["negative_valid_fluxes"], 1)

    def test_dr4_and_early_types_are_not_silently_fitted(self):
        values = list(fixture())
        values[-1]["release"] = "Gaia DR4"; values[-1]["product"] = "epoch_xp"
        spectrum = work.validate_spectrum(*values)
        self.assertFalse(work.inspect(spectrum)["ready_for_fit"])
        with tempfile.TemporaryDirectory() as d, self.assertRaises(ValueError):
            work.fit(spectrum, Path(d)/"unstarted")
        values[-1]["release"] = "Gaia DR3"; values[-1]["product"] = "mean_xp"; values[-1]["spt_num"] = 30.
        self.assertFalse(work.inspect(work.validate_spectrum(*values))["ready_for_fit"])

    def test_missing_blue_coverage_is_not_hidden(self):
        wave, flux, mask, factor, meta = fixture()
        mask[(wave >= 340) & (wave < 364)] = False
        self.assertFalse(work.inspect(work.validate_spectrum(wave, flux, mask, factor, meta))["ready_for_fit"])

    def test_covariance_input_preserves_correlations_and_rejects_non_psd(self):
        wave, flux, mask, factor, meta = fixture()
        covariance = factor@factor.T
        with tempfile.TemporaryDirectory() as d:
            base = Path(d); metadata = base/"metadata.json"; work.write_json(metadata, meta)
            path = base/"input.npz"
            np.savez(path, source_id=np.array(meta["source_id"]), wave=wave, flux=flux, mask=mask, covariance=covariance)
            loaded = work.load_input(path, metadata)
            np.testing.assert_allclose(loaded.factor@loaded.factor.T, covariance, rtol=1e-10, atol=1e-44)
            covariance[0, 0] = -1e-34
            np.savez(path, source_id=np.array(meta["source_id"]), wave=wave, flux=flux, covariance=covariance)
            with self.assertRaises(ValueError):
                work.load_input(path, metadata)

    def test_errors_alone_cannot_replace_covariance(self):
        wave, flux, mask, factor, meta = fixture()
        with tempfile.TemporaryDirectory() as d:
            base = Path(d); work.write_json(base/"metadata.json", meta)
            np.savez(base/"input.npz", source_id=np.array(meta["source_id"]), wave=wave, flux=flux, error=np.full(len(wave),1e-17))
            with self.assertRaises(ValueError):
                work.load_input(base/"input.npz", base/"metadata.json")
