# Single-source overview and offline HTML report

English · [简体中文](report.zh-CN.md)

`report` builds a summary of one completed Gaia XP continuum fit. It uses the saved spectrum, model predictions and posterior, optionally with survey photometry and archival spectra for the same star. Generating a report requires no new fit, posterior sampling or archive download.

## Inputs and outputs

Use version 0.2.0 or a later compatible release. Supply a complete, readable fit directory as `RUN` and choose a new directory for `NEW_DIRECTORY`. You can generate a report on a computer without a model template cache.

```text
gaia-xp report --run RUN --output NEW_DIRECTORY
```

From version 0.3.0, `--photometry PHOTOMETRY_DIRECTORY` adds previously queried photometry. Collect the data first, as the report uses local files and leaves missing data unfilled. [Photometry guide](photometry.md)

From version 0.4.0, `--spectra SPECTRA_DIRECTORY` adds downloaded archival spectra and their instruments and observing times. [Archival spectra guide](spectroscopy.md)

From version 0.5.0, an interactive epoch panel appears first. It includes downloaded archival spectra automatically. Use `--epochs EPOCHS_DIRECTORY` to add other verified, calibrated epoch data. Even without epoch spectra, the panel distinguishes the DR3 mean reference, external spectra available to plot, and archive records awaiting download. The panel supports display of verified data. Official DR4 downloads and fits require a separate adapter. [Epoch guide](epochs.md)

The fit directory must contain `status.json`, `summary.json`, `review.json`, `run_contract.json`, `spectrum.npz`, `prediction.npz` and `posterior.npz`. If any required file is missing, recover it from the original run before generating the report.

| Output | Contents |
|---|---|
| `overview.png` | Main quantities, full-spectrum fit, blue enlargement, band residuals and posterior conditional on positive accretion. |
| `spectrum.png` | Standalone spectrum and fit diagnostics. |
| `posterior.png` | Standalone joint parameter posterior. |
| `photometry.png` | XP and broadband flux densities when photometry is supplied. |
| `spectroscopy.png` | Absolute fluxes, blue continuum and Hα at the original sampling when archival spectra are supplied. |
| `report.html` | Offline report with text, values, diagnostics and embedded figures. The HTML file can be copied and opened on its own. |
| `report_manifest.json` | Input files, integrity checks and origin of the report outputs. |

## Read the fit

The main numbers use the stored posterior quantiles. Accretion quantiles include the exact-zero branch. The separately reported `P0` gives that branch’s posterior weight under the assumed model and priors. Its calibration as a probability of physically absent accretion is unknown. The corner plot shows degeneracies conditional on the positive branch. For intervals and upper limits, use the quantiles including both branches.

Spectral-type (SpT) bins align with the stored grid nodes to avoid artificial empty columns. The figure preserves the saved samples without jitter or posterior interpolation. A finer numerical integration would require a new calculation. [Grid and posterior guide](inference.md)

- `r` measures the ratio of mean reddened accretion-continuum and photospheric flux densities over 700–900 nm.
- `Facc` is the intrinsic model slab flux integrated over 50–2477.47 nm, in W m⁻².
- `q` is `Facc` divided by the model bolometric photospheric flux.

The report lists `Lacc` or `Mdot` only if the original fit saved the conversion and the sources of its stellar parameters. Missing conversions appear as unavailable. No default distance, mass or radius is supplied. The intervals condition on any fixed stellar parameters and omit their uncertainties.

The full-spectrum plot shows the observation, the total model and its photospheric and slab components. Inspect the blue enlargement for low signal-to-noise regions and the shape near the Balmer jump. Prediction intervals are read from the summaries of the saved plotting samples. The wavelength-by-wavelength component medians need not sum to the median total spectrum. Residuals use the original fitted bands and their marginal noise scales. Band errors remain correlated, so treating these points as independent measurements in a conventional reduced χ² would give a misleading diagnostic.

The report distinguishes numerical convergence, flags about the fit’s applicability and the status of physical calibration. A visually good fit, a low `P0` or passed numerical checks cannot by themselves establish an independently calibrated accretion measurement. [Scientific scope](scientific_scope.md)

## Compare other observations

The photometry plot shows wavelength and flux density Fν in Jy. A broadband point represents a filter bandpass. Plotting it at the representative wavelength does not turn it into a narrowband measurement that can be compared directly with a single XP sample to score the fit. Surveys generally observe at different epochs, and infrared measurements may include disk emission. The XP fit uses no survey photometry and does not extrapolate its model into the infrared.

Archival spectra and XP are shown in common units, preserving absolute fluxes. The static full-spectrum plot averages data for display in 0.5 nm bins, and the blue view uses 0.2 nm bins. Hα retains its original sampling. The interactive panel can zoom in on the original samples. Display spacing is distinct from instrumental resolving power. The red flux ratio still uses the original 5 nm band integrations over wavelengths valid in both spectra. It describes an observed difference without corrections for extinction, epoch or slit loss.

Each archival spectrum’s legend gives the instrument, arm, wide or narrow slit, observing date, time down to seconds and time scale. The table keeps the original time precision and specifies whether a time is an exposure start, midpoint or range. Missing information is marked as unavailable. The Gaia DR3 mean spectrum represents multiple years and has no single observing time. When DR4 epochs become available, the legend for each must carry the official time value, format and scale. A positional reference epoch cannot stand in for an observing time, and a TCB or TDB value requires conversion before it can be labelled UTC.

The HTML opens with the epoch panel, followed by the XP fit and external comparisons. Detailed measurements, matching records and sources can be expanded. Each figure keeps the main limitations beside the relevant observation.

## What the integrity checks establish

The program checks that `status.json` records `complete`. It verifies the summary, diagnostics, posterior and run contract against the original run’s checksum records. It also records hashes of the files actually read to produce the report.

Some older runs have no original checksum for `spectrum.npz`, `prediction.npz` or the status file itself. A hash calculated while making a report identifies the exact file used on that occasion. Establishing that the file has remained unchanged since the fit requires an earlier checksum for comparison. The new report manifest preserves that distinction.
