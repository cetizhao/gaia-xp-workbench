# Viewing spectra by epoch

English · [简体中文](epochs.zh-CN.md)

The first panel of each source report shows spectra from individual observations. Select observation groups to overlay, step through them, switch between the full spectrum, the blue continuum and Hα, or drag across a wavelength range to zoom in. The initial view compares wide-slit archival spectra with the Gaia DR3 mean XP spectrum in the blue, where the continuum carries information about accretion. Select a narrow-slit spectrum to inspect lines at their original sampling. The vertical axis adjusts to the visible wavelength range while preserving the absolute flux scale.

Each curve identifies the instrument, arm, slit type, observation time and time scale. The panel preserves the original sampling and masks, leaves gaps across missing data, and displays the spectra without smoothing or fitting. Check the wavelength medium (air or vacuum), velocity reference frame and instrumental response before interpreting offsets between narrow lines as velocities. Slit losses and calibration differences can also affect the flux.

The panel counts independent epochs by observation group. For example, the four X-shooter spectra of V721 CrA belong to one group: two arms and two slit widths. This gives one observation for comparison with XP. The ESPRESSO archive entries describe candidate observations, and the panel plots only spectra loaded from local files. Gaia DR3 contributes a mean spectrum as a reference. If there are no actual DR4 epoch spectra, the panel shows their availability and leaves their curves empty.

## Add calibrated epoch spectra

Pass a directory containing `epochs.json` to `report --epochs DIRECTORY`, or pass the JSON file itself. This local format adds spectra to an existing report. Official DR4 products will need their own verified source identities, time definitions, units, quality checks and calibration before use.

```json
{
  "schema_version": 1,
  "source_id": "6719035052475592576",
  "wavelength_unit": "nm",
  "flux_unit": "W m-2 nm-1",
  "records": [
    {
      "epoch_id": "PRODUCT_ID",
      "group_id": "OBSERVATION_GROUP",
      "instrument": "INSTRUMENT",
      "time": {
        "value": "OFFICIAL_TIME_VALUE",
        "format": "MJD",
        "scale": "OFFICIAL_TIME_SCALE",
        "definition": "Exposure start, midpoint or time range"
      },
      "calibration_reference": "Verified calibration source",
      "arrays_file": "PRODUCT_ID.npz",
      "sha256": "SHA256_OF_ARRAY_FILE"
    }
  ]
}
```

The example illustrates the fields. Supply an NPZ file for each real spectrum with a one-dimensional, strictly increasing `wave_nm` array, a `flux_w_m2_nm` array of the same length, and a Boolean `mask`. You can also include an exact string `source_id`. Each file must be inside the data directory and match its SHA256 checksum. Give every record a unique `epoch_id`. Arms from one observation can share a `group_id`. Optional fields include `arm`, `label`, `release`, `resolving_power`, `wavelength_medium` and `spectral_frame`.

At the top level and inside the NPZ files, `source_id` links the spectra to the report's target, currently identified in DR3. For an external data release, also record `native_source_id`, `release` and `identity_reference`. These preserve the original identifier, release and basis for the match. A record labelled `Gaia DR4` requires its native identifier and the match evidence. Verify the cross-release association when preparing the data.

Keep the original observation time as a string. Supported formats are `ISO 8601`, `JD`, `MJD` and `offset days`. For the last format, include `time.zero_point`. Supply the time scale and what the value measures. The panel performs no time-scale conversions, so TCB and TDB values keep those labels. A position reference epoch is a separate quantity. Order the observation groups by their verified observing sequence before import, since the panel follows input order. Add a mean spectrum as a reference.

The report records the SHA256 of the JSON and each array file. These checks establish which files it read and whether their declared units match the display format. The physical calibration and suitability for fitting require separate assessment.
