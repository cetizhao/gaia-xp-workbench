---
name: gaia-xp-fit
description: Select Gaia targets, download and calibrate DR3 mean XP spectra, fit accretion continua in young stars, compare survey photometry and archival spectra, or generate an English report from a saved fit.
---

# Fitting and interpreting Gaia XP spectra

English · [简体中文](SKILL.zh-CN.md)

Use the local `gaia-xp` executable for numerical work. Answer in the user's language and generate scientific reports in English. When asked about an existing fit, use its saved posterior. Assess numerical convergence, how well the model describes this spectrum, and the independent physical calibration of the inferred accretion separately.

## Find the fitter in a new session

Use the executable recorded in the project instructions or `gaia-xp` on PATH. A project-local installation can also be called at `.venv-gaia-xp/bin/gaia-xp` on macOS/Linux or `.venv-gaia-xp/Scripts/gaia-xp.exe` on Windows, relative to the research project root. If the virtual environment is in the fitter checkout, use its `.venv`. Verify the executable with `--version` and use its full path for subsequent commands. Resolve the reference links below relative to this skill directory.

If the user requests setup and only the skill is installed, create a Python 3.12 virtual environment in the research project. From the fitter checkout, use that environment's Python to install the package. For XP calibration and ESO FITS support, run `python -m pip install ".[gaia,spectroscopy]"`. If the client runs commands in a container or on a remote host, set up Python, inputs and model files in that environment. [Public repository and installation guide](https://github.com/cetizhao/gaia-xp-workbench)

## Choose the operation

- **Interpret an existing fit.** Use `gaia-xp review --run RUN` to read the saved result.
- **Make a source overview or an HTML report.** Use `gaia-xp report --run RUN --output NEW_DIRECTORY`. It reads the saved observation, predictions, posterior and diagnostics.
- **Explore spectra of one star at different epochs.** The first report panel supports selection by observation time, overlays and zoom. Use `report --epochs EPOCHS_DIRECTORY` to display additional verified, calibrated spectra. [Epoch spectra](references/epochs.md)
- **Query survey photometry.** Use `gaia-xp photometry --source-id GAIA_DR3_ID --output NEW_DIRECTORY`. Combine it with a saved fit using `gaia-xp report --run RUN --photometry PHOTOMETRY_DIRECTORY --output NEW_REPORT_DIRECTORY`.
- **Select and acquire Gaia spectra.** Use `gaia-select` to save candidates, then `gaia-fetch` for each explicitly selected source. Downloaded spectra are checked when the required inputs are available. Preserve existing fits. [Selection and download](references/gaia_download.md)
- **Find archival spectra.** Use `spectra-search`, then `spectra-fetch` for suitable products. Display them with `report --run RUN --spectra SPECTRA_DIRECTORY --output NEW_REPORT_DIRECTORY`. Include `--photometry` in the same command if needed. [Archival spectroscopy](references/spectroscopy.md)
- **Check a new spectrum.** Run `gaia-xp inspect --input SPECTRUM.npz --metadata METADATA.json`.
- **Fit a source.** When the user asks for a fit and the input passes inspection, run `gaia-xp fit --input SPECTRUM.npz --metadata METADATA.json --output NEW_DIRECTORY`.
- **Summarize selected results.** Run `gaia-xp summarize --run RUN_A --run RUN_B --output NEW_DIRECTORY`. Keep the sample as selected. Combining posteriors or studying population correlations is a separate analysis.

Prefer absolute paths. Selection by sky region or brightness yields candidates whose membership and youth need separate evidence. For a named target, confirm the Gaia release, exact source identifier and stellar component. Keep to the requested sources. Consult the input format when first handling a spectrum, and the method description when interpreting the posterior. Both references travel with the skill. [Single-spectrum input](references/input_format.md) · [Scientific scope](references/scientific_scope.md)

## Runtime and model files

Use Python 3.12 with access to the working directories. The `gaia` extra provides XP calibration and `spectroscopy` provides archival FITS support. Archive queries need network access. Reports read local files.

Starting with 0.7.0, the public package supplies the 1,620 FRAPPE slab spectra and both photospheric calibration tables. Run `gaia-xp assets check` before a new fit. If only the Fang template is missing, use `gaia-xp assets import --from-dir DIR` with an authorized local copy of `Gaia_template_final_new_final.sav`. The SAV may be directly inside `DIR`. Confirm that all 1,623 files pass verification. If `GAIA_XP_ASSETS` or the top-level `--assets-dir` option is set, the complete set must be in that directory. Download, spectrum inspection and reporting on saved fits can proceed without the model files.

On Windows, set `$env:PYTHONUTF8='1'` for terminal output. The numerical entry point uses the Agg plotting backend, two integration workers and single-threaded BLAS. Run one intensive computation at a time. Use new directories for new fits, photometry acquisitions, reports and summaries. On failure, read the error and saved status. Incomplete files do not establish success. Keep grid refinements within the requested computation.

## Inspect and interpret a fit

New fits accept externally calibrated Gaia DR3 mean XP spectra with an external spectral type of K0–M8. Use the 336–1020 nm grid at 2 nm spacing. Require the full covariance or its factor, explicit units, and sources for the spectral type, visual extinction and effective temperature. Retain negative fluxes and masks and treat Gaia identifiers as exact decimal strings. Report missing information. Substituting independent errors or guessing priors changes the inference.

After a fit, verify that `status.json` says `complete`, read `review.json`, and inspect `spectrum_fit.png` and `corner_positive.png`. Explain the data, method, main constraints, residuals, degeneracies and missing evidence at the requested length. Interpret the quantiles including the zero branch, any upper limits and the zero-branch posterior probability `P0` together. The corner plot is conditional on positive accretion. Its spectral-type bins align with the saved nodes. Keep samples at their original coordinates and probabilities. Changing integration density or the sampler requires a new inference run. [Grid integration and sampling](references/inference.md)

Distinguish `r`, the 700–900 nm optical excess-to-photosphere ratio, from `Facc`, the intrinsic slab flux integrated over 50–2477.47 nm, and `q = Facc/Fstar`, its ratio to bolometric photospheric flux. Converting to `Lacc` needs a distance. Converting to `Mdot` also needs a stellar mass, radius and inner truncation radius assumption. The optional luminosity and mass accretion rate conversions hold the supplied stellar parameters fixed. Their uncertainties are absent from the reported intervals. New runs do not automatically test sensitivity to the priors.

Numerical convergence, small `P0` and a large Bayes factor describe the inference under the adopted model. Independent observations are needed to assess the physical accretion scale. Report when external blending information is unknown. A fit to the DR3 mean spectrum describes the mean observation and supplies no time series.

## Make the report and compare observations

Preserve the original run and write the report into a new directory. Deliver `overview.png` and the offline `report.html`, and keep the provenance in `report_manifest.json`. Figures are embedded in the HTML. Check the main quantities, full spectrum, blue enlargement, residuals and posterior for readability. Use the saved quantiles and any saved `Lacc` or `Mdot`. If required results are missing, identify them and leave the fit untouched. For an older run without an original spectrum or prediction hash, a hash calculated during reporting identifies the file that was read. Its earlier history remains unverified.

Generate HTML, Markdown reports, sample summaries, figures, tables and interactive controls in English. Prefer English for user-supplied provenance or observation captions while preserving the original records in their original language. Write for astronomers. Present the main result and comparisons first, with technical details and full tables available on demand. Describe what the figures show in short sentences.

For photometry, retain the original tables, units, magnitude systems, quality flags, match candidates and angular separations. Check proper motion and observation epochs. Resolve competing identifications from the evidence. Angular proximity alone is insufficient when several candidates remain. Distinguish nondetections, upper limits, low-quality measurements and service failures. When comparing photometry with XP, consider the different observation times, filter widths and infrared emission from the disk. The comparison omits filter integration and independent accretion calibration. Keep the XP posterior and treat upper limits as censored measurements.

Place the multi-epoch panel first. Keep the time and original sampling of every spectrum. Display the multi-year DR3 mean as a reference. Count multiple arms and slit widths from one observation together. Plot only downloaded spectra and identify archive-only records as such. When assessing external evidence for candidates, count reliable spectra, accretion-continuum coverage and near-contemporaneous observations separately. [External observational evidence](references/external_evidence.md)

Keep instruments, dates and spectral resolving powers distinct. Check absolute or relative flux calibration, slit width, air or vacuum wavelengths and the spectral reference frame. Prefer wide-slit, absolutely calibrated spectra for the continuum and narrow-slit, high-resolution spectra for lines. Keep different dates and components separate. Binning for display does not reproduce the Gaia response. A difference between observations at different times has several possible causes, including calibration, extinction and accretion.

Label each comparison spectrum with instrument and arm, slit category, date, time to seconds and time scale where known. Retain full time precision and the exposure start, midpoint or interval definition in the table. Mark missing times explicitly. Label every future DR4 epoch spectrum with the official value, format and scale. The epoch attached to a sky position cannot supply an observation time. A TCB or TDB time requires an explicit conversion before it can be labelled UTC. [Time conventions](references/gaia_download.md)

For DR4, run `gaia-xp gaia-probe --release dr4` and distinguish a failed query from unavailable data. Identify unverified products, DR3–DR4 cross-identifications and calibrations. DR4 processing requires verified identifiers and calibration for that release. Keep the original release metadata when checking eligibility.
