# Input format for a single Gaia XP spectrum

English · [简体中文](input_format.zh-CN.md)

Provide the externally calibrated **Gaia DR3 mean XP spectrum** in an NPZ file and its metadata in a JSON file. The NPZ contains flux densities and their correlated uncertainties. The JSON identifies the observation, its calibration and the external stellar parameters used as priors. Run `gaia-fetch` to download and calibrate a DR3 spectrum in this format, or prepare the two files yourself. The fitter uses the DR3 product definition and calibration. Relabelling a DR4 product would invalidate the fit.

## NPZ arrays

| Field | Type, shape and units |
|---|---|
| `source_id` | Scalar Unicode string, e.g. `np.array("6719035052475592576")`. Preserve the exact decimal digits. Floating-point numbers and scientific notation can lose the identity. |
| `wave` | `[343]`, in nm, from 336 to 1020 nm in steps of 2 nm. |
| `flux` | `[343]`, in W m⁻² nm⁻¹. Retain measured negative flux densities. |
| `noise_factor` | `[343, k]`, in the same units as the flux density. The factor `B` represents covariance `C = B Bᵀ`. |
| `covariance` | Alternative to `noise_factor`. A symmetric positive semidefinite `[343,343]` matrix in squared flux-density units. |
| `mask` | Optional Boolean `[343]` array. True marks a valid sample. All samples are valid by default. |
| `error` | Optional `[343]` array of marginal standard deviations. Its values must agree with the covariance. |

Supply exactly one of `noise_factor` and `covariance`. Pointwise errors alone omit the wavelength correlations. At valid wavelengths the flux must be finite and the marginal error positive. Missing values outside the quality mask are excluded. Keep valid negative fluxes as measured, even where the signal is weak. If you change units, convert both the flux and its covariance.

## JSON metadata

The following example illustrates the file format. Replace the example stellar parameters and descriptions with values and sources appropriate to the observation. Choose the priors independently of the accretion result you hope to test.

```json
{
  "source_id": "6719035052475592576",
  "name": "Target name",
  "release": "Gaia DR3",
  "product": "mean_xp",
  "epoch_time": null,
  "calibration": "externally_calibrated",
  "calibration_version": "Calibration software version and corrections applied",
  "wavelength_unit": "nm",
  "flux_unit": "W m-2 nm-1",
  "input_reference": "Location of the archive product, download and calibration records",
  "prior_reference": "Source of the adopted spectral type, Av and Teff",
  "spt_num": 73.75,
  "av_mag": 0.3,
  "teff_k": 3300
}
```

The `source_id` must match the NPZ exactly and refers to the stated Gaia release. Spectral type is encoded as K0 = 60 and M0 = 70. For example, M3.75 is 73.75. New fits accept external spectral types from 60 to 78 (K0–M8). `av_mag` is nonnegative V-band extinction in magnitudes. Convert a K-band extinction before entering it here. `teff_k` is a positive effective temperature in kelvin, used in the bolometric correction for the model photosphere. Give the calibration and the sources of the priors in the reference fields.

## Optional luminosity and mass accretion rate

A `stellar_parameters` object can provide `distance_pc` and its `reference`. To derive a mass accretion rate, also supply `mass_msun` and `radius_rsun`. Distance is in parsecs, mass in solar masses and radius in solar radii. All values must be finite and positive.

The conversions are `Lacc = 4πd²Facc` and `Mdot = 1.25 Lacc Rstar/(G Mstar)`. The second assumes an inner truncation radius of `5 Rstar`. The reported posterior intervals hold the adopted distance, mass, radius and geometry fixed. Without a distance, the absolute accretion result is a flux. The report can give a mass accretion rate only when it also has both stellar mass and radius.

## Inspect, fit and review

```text
gaia-xp inspect --input spectrum.npz --metadata metadata.json
gaia-xp fit --input spectrum.npz --metadata metadata.json --output new_run
gaia-xp review --run new_run
```

Read the reasons for any failed input checks and correct the input at its source. Keep the actual release, covariance and valid negative fluxes. `new_run` must be a new directory. A completed run contains copies of the inputs, `run_contract.json`, `posterior.npz`, `summary.json`, `review.json`, `report.md`, `spectrum_fit.png` and `corner_positive.png`. Check `status.json` for completion and integrity information.
