# Select Gaia sources and download XP spectra

English · [简体中文](gaia_download.zh-CN.md)

Download the continuous basis-function coefficients of a Gaia DR3 mean XP spectrum by source identifier, then calibrate them into the format used by the fitter. A position, magnitude or colour cut selects candidates. Membership in an association and stellar youth require additional evidence. When starting from a name, verify the Gaia release, source identifier and stellar component before choosing a positional or name match.

## Select, download and inspect DR3 spectra

The selection query runs without GaiaXPy. For calibration, install `pip install ".[gaia]"` in the fitter’s environment.

```text
gaia-xp gaia-select --source-id 6719035052475592576 --output NEW_SELECTION
gaia-xp gaia-select --ra 287.44 --dec -37.07 --radius-arcmin 2 --g-max 15 --limit 20 --output NEW_SELECTION
gaia-xp gaia-fetch --source-id 6719035052475592576 --metadata PRIORS.json --output NEW_XP
```

Repeat `--source-id` to select several identifiers. For a cone search, use `--bp-rp-min` and `--bp-rp-max` to set colour limits. The maximum search radius is 60′ and the maximum number of candidates is 100. A result that exceeds the requested limit is marked as truncated. Candidates without published XP remain in the selection so that you can assess completeness. Run `gaia-fetch` once per chosen source.

The download preserves the Gaia source table, original responses for the XP continuous coefficients, requests, retrieval date and checksums. By default GaiaXPy 2.1.2 calibrates the full coefficient set without truncation and samples 336–1020 nm at 2 nm intervals. Flux density is in W m⁻² nm⁻¹. The full coefficient covariance of each arm is propagated into the spectrum and stored as `noise_factor` (B), with spectral covariance C = BBᵀ. Gaia does not publish the BP/RP cross-covariance. The fitter records the assumption that it is zero. The flux and marginal uncertainties must agree with GaiaXPy, and the saved covariance factor retains the wavelength correlations for fitting.

If ESA DataLink is unavailable, the downloader tries the same DR3 continuous-spectrum table at Gaia@AIP once. It records the provider, failed response and original VOTable. Conversion from XML to CSV preserves the coefficient and uncertainty values. [Gaia@AIP DR3 continuous-spectrum table](https://gaia.aip.de/metadata/gaiadr3/xp_continuous_mean_spectrum/)

The calibrated download writes `spectrum.npz`, `metadata.json`, `calibration.json` and `download.json`. If `PRIORS.json` provides a spectral type, visual extinction (Av), effective temperature (Teff) and their sources, the program runs `inspect` and writes `inspection.json`. With priors missing, you can still download and view the spectrum. The calibration record lists the missing inputs and marks the spectrum as awaiting priors. Downloading does not start a fit. Use `--no-calibrate` to save the original coefficients only.

## Check DR4 products and source identity

```text
gaia-xp gaia-probe --release dr4 --output NEW_CHECK
```

This command queries the publicly visible TAP schemas and distinguishes an unavailable release from a failed query. On 2026-11-19 the archive returned no DR4 schema. The original response was kept in the local validation directory. The current version supports the availability check. A request with `--release dr4` records whether the release is unavailable or the adapter still needs verification. Official DR4 XP downloads, calibration and epoch fitting require a verified adapter.

When the official products become available, verify the DR3-to-DR4 source identification, mean and epoch XP formats, covariances and calibration tools. A visible table on its own does not establish cross-release identities or justify using DR3 calibration matrices on DR4 spectra.

Preserve each epoch product’s official time value, format (such as JD or MJD, including its zero point), time scale, and definition (exposure start, midpoint or coverage interval). Label each epoch spectrum with its observation time in the legend. Give the original precision in the table and identify missing fields. If you convert a time to a calendar date, retain the original and specify the scale used after conversion. TCB and TDB require conversion before labelling a date UTC. The Gaia position field `reference_epoch` serves astrometry. Identify a DR3 mean XP spectrum as a mean over multiple visits.

Successful download and calibration make a spectrum available for input inspection. Physical calibration of the accretion model requires independent evidence. [ESA Gaia Archive](https://gea.esac.esa.int/archive/) · [Archive and DataLink services](https://www.cosmos.esa.int/web/gaia-users/archive) · [GaiaXPy](https://gaia-dpci.github.io/GaiaXPy-website/)
