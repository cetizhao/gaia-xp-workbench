# Installation and result validation

English · [简体中文](README.zh-CN.md)

These checks establish that the fitter runs outside the original research directory and that moving the numerical code preserves its results. Testing the physical accretion scale across stars or regions requires independent observations. The example inputs and posterior are stored locally under `.local/` and are excluded from Git.

## First extraction from the research project

On Windows x64 with Python 3.12.14, a new virtual environment was created without system site-packages, and the built wheel was installed in ordinary, non-editable mode. `pip check` passed. Nine tests covered exact source IDs, correlated errors, missing inputs, the supported scientific range and detection of altered model files. The full dependency versions were verified on Windows. [Environment record](environment.json) · [Windows requirements](../requirements-windows-py312.txt)

For Gaia DR3 source `6719035052475592576`, the original mean XP spectrum, priors and seed 20853506 gave a new fit in about 54 seconds. All 20 posterior arrays matched the historical results element for element. The input omitted the research group's additional stellar parameters, so this run did not produce `Lacc` or `Mdot`. The effective temperature of 4300 K reproduces the historical test setup and has no independent calibration from this check. For 34 key functions and classes, the Python abstract syntax trees matched the original implementation. [Single-source check](single_source.json) · [Numerical code comparison](core_extraction.json)

The single-source run used `python -I` and imported the installed modules from the new environment's `site-packages`. A file-access audit hook blocked access to the original research project outside the new checkout. No such accesses occurred. In a separate read-only check from a working directory outside the repository, the help command and an example spectrum inspection both exited with code 0. The installed skill's reference documents were readable independently. The spectrum and corner plots were examined, and `review` passed. Summarizing the same run twice returned two records for one distinct star.

The new cache was populated from existing files. All 1,623 entries matched the manifest sizes and SHA-256 checksums. This extraction introduced no new astronomical sample downloads, model training or batch fits. At the time of the initial check the repository was local, without a GitHub remote, and redistribution rights for the Fang template were unresolved. Public version 0.7.0 ships the 1,620 FRAPPE slab spectra and two calibration tables. New fits also require an authorized local Fang template. [File-by-file preservation check](original_preservation.json)

## 0.2.0 — Single-source reports

The saved fit above was used to generate one overview, two detail figures and an offline HTML report. The new wheel produced the report in an isolated environment with a nonexistent model path, without refitting. Thirteen tests passed. After the final HTML figure layout change, four report tests passed again. The SHA-256 values of all 13 original fit files remained identical. Metadata for existing research files and checksums of key files were unchanged.

The HTML embedded three PNGs and had no external resources. A copy of just the HTML file was opened offline in Edge and the full page, overview, spectrum and corner plots were checked. In-page link targets existed. Interactive navigation was not tested separately at this stage. The report retained the zero-branch weight, parameter units, missing stellar conversions, correlated residuals and limitations on physical calibration. [Validation and output hashes](report_v020.json) · [Report guide](../docs/report.md)

## 0.3.0 — Survey photometry in the report

A live VizieR query for the same source returned ten bands from APASS (g′, r′, i′), 2MASS (J, H, Ks) and AllWISE (W1–W4). Each catalogue had one positional candidate. The angular separations at the adopted epochs were 0.407″, 0.058″ and 0.060″, respectively. Eight measurements passed the quality selection. W1 and W2 retained their contamination flags, with additional saturated pixels in W1, and both were plotted with open symbols. These observations at different epochs were not used to infer accretion variability.

The installed wheel passed `pip check` and 23 tests. The report was generated from the existing XP run and saved photometry tables without using model assets or rerunning the fit. The 13 original fit files, the 0.2.0 report and the original research project were unchanged. The standalone HTML embedded four figures. The main page, expanded photometry table and comparison plot were checked in Edge. [Photometry validation](photometry_v030.json) · [Query rules and units](../docs/photometry.md)

## 0.4.0 — Gaia downloads, archival spectra and posterior plots

DR3 source selection, acquisition of continuous-spectrum coefficients, GaiaXPy calibration and automatic input inspection succeeded for the same source. ESA DataLink returned HTTP 503 on this attempt. The program retrieved the verified same-release coefficients from Gaia@AIP and retained both request records. The new calibrated flux matched the original input element for element, and the full covariance agreed to numerical precision. The official Gaia TAP query returned no public DR4 schema at the time. This tested DR4 availability only. Downloading and calibrating official DR4 products remained unverified.

ESO returned six X-shooter and ten ESPRESSO products. The MAST query returned no spectra. Four wide- and narrow-slit optical products from one X-shooter visit on 2022-05-06 were downloaded. Units, observing times, positions, slit widths and nominal resolving powers were checked. The combined report retained absolute fluxes and displayed spectra averaged over 5 nm. The red-end wide-slit to XP flux ratio was about 0.56. With these data alone, the difference could not be attributed to accretion variability. The spectral-type posterior was plotted with bins aligned to its original nodes, using the saved posterior and the original grid.

The wheel was installed both in a base environment and in a new environment with the optional observing dependencies. Forty-two tests passed. After final wording changes, three spectroscopy report tests passed again. A report made from saved data required neither GaiaXPy, Astropy nor a model cache. Its five embedded figures and expanded HTML were inspected. All 13 original fit files, previous reports and the research project were preserved. This particular pinned set of observing dependencies was verified on Windows. [Acquisition and comparison record](acquisition_v040.json) · [Windows observing dependencies](../requirements-observations-windows-py312.txt)

## 0.5.0 — Multi-epoch spectra

An offline interactive panel was added at the top of the report. It retained the original sampling of the four X-shooter products from a single observation group and displayed the DR3 mean as a separate reference. The panel drew no curves for unloaded ESPRESSO or DR4 products. The static full-spectrum and blue-end plots used 0.5 nm and 0.2 nm display averages, respectively. The red-end ratio retained the original 5 nm integration and was numerically unchanged.

After 49 tests passed, a further set of five tests covering the new epoch input and existing report behavior passed, bringing the total distinct tests covered to 50. The new wheel produced the same source's report in the base environment. In Edge, wavelength selection, observation-group browsing, the reference-spectrum toggle, drag-to-zoom and the narrow-screen layout all worked, with no page errors or network requests. The original inputs, previous reports and comparison values were checked and remained unchanged. This run involved no new downloads or refit. The panel accepts verified, calibrated spectra. An adapter for official DR4 epoch products was outside this validation. [Multi-epoch validation](epochs_v050.json)

## 0.7.0 — Model files and agent clients

A clean Windows Python 3.12.14 wheel contained the 1,620 FRAPPE spectra and both calibration tables. Their combined 134,568,399 bytes matched all the file sizes and SHA-256 values in the asset manifest. The package contained no Fang SAV. With an empty cache, the installed CLI reported exactly the missing Fang template. Importing that file alone brought the count to 1,623 verified files. The three FRAPPE groups continued to load from the package. No XP fit was run for these checks.

The project installer covers 12 clients using four project skill directories. Native discovery was exercised with Codex, Claude Code 2.1.263 and DeepSeek Harness 0.2.2-rc.1. The shared CLI generated the overview and English HTML from the existing fit for source `6719035052475592576`. The Windows regression suite passed all 59 tests. macOS installation is documented for verification on the user's own machine. [Client setup and checks](../docs/agent-clients.md)
