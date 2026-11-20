# Gaia XP Accretion Fitter

**English** · [简体中文](README.zh-CN.md)

How much of a young star’s blue light can be explained by accretion? The fitter combines a Fang photospheric template with a hydrogen accretion continuum, applies extinction and fits 16 broad bands of the Gaia DR3 mean BP/RP (XP) spectrum. It accepts young stars with an external spectral type of **K0–M8**. For each star, `report` produces an overview figure and an English HTML report that can include survey photometry and dated archival spectra.

**Already have `report.html`?** Open it in a browser, even offline. If you have the saved fit directory, you can rebuild the report or add observations using the saved posterior. Only a new fit needs the Fang template.

## Start on a Mac

Open your research folder in an agent that can read files and run terminal commands. You can paste this request into the chat.

> Install `cetizhao/gaia-xp-workbench` from GitHub in this research folder. Use Python 3.12 in `.venv-gaia-xp` and include Gaia XP calibration and ESO spectrum support. Use the repository’s skill installer for all supported clients in this folder. Run the version check and tests on this Mac. Tell me the chip architecture, test result and which model files I still need for a new fit.

Start a new chat in the same folder. The installer supports 12 clients, all of which can share one Python environment. Codex, Claude Code and DeepSeek Harness have been tested for automatic skill discovery. Other clients with a terminal can also read `skills/gaia-xp-fit/SKILL.md` directly from the checkout. The guides and skill instructions open in English and link to their Chinese editions. [Client setup and compatibility](docs/agent-clients.md) · [Agent skill](skills/gaia-xp-fit/SKILL.md)

<details>
<summary>Terminal installation and local checks</summary>

Start in the **research folder you will open in your agent**. These commands use Git and Python 3.12 on macOS or Linux.

```sh
git clone https://github.com/cetizhao/gaia-xp-workbench.git
python3.12 -m venv .venv-gaia-xp
.venv-gaia-xp/bin/python -m pip install "./gaia-xp-workbench[gaia,spectroscopy]"
.venv-gaia-xp/bin/python ./gaia-xp-workbench/scripts/install_skill.py --project . --agent all
.venv-gaia-xp/bin/python -m pip check
.venv-gaia-xp/bin/gaia-xp --version
.venv-gaia-xp/bin/python -m unittest discover -s gaia-xp-workbench/tests
```

On Windows, clone the repository as above and run these commands in PowerShell from the same research folder.

```powershell
py -3.12 -m venv .venv-gaia-xp
.\.venv-gaia-xp\Scripts\python.exe -m pip install "./gaia-xp-workbench[gaia,spectroscopy]"
.\.venv-gaia-xp\Scripts\python.exe .\gaia-xp-workbench\scripts\install_skill.py --project . --agent all
.\.venv-gaia-xp\Scripts\python.exe -m pip check
.\.venv-gaia-xp\Scripts\gaia-xp.exe --version
.\.venv-gaia-xp\Scripts\python.exe -m unittest discover -s gaia-xp-workbench/tests
```

To install the skill for selected clients, replace `--agent all` with their names, for example `--agent claude-code cursor`. The `gaia` extra installs GaiaXPy to calibrate XP spectra. The `spectroscopy` extra installs Astropy to read ESO FITS products. For local fitting or reporting alone, install `./gaia-xp-workbench` without extras. On Intel Macs, building the pinned `extinction` dependency may require Apple’s Command Line Tools. A Python 3.12 wheel is available for Apple silicon. [extinction release files](https://pypi.org/project/extinction/0.4.8/#files)

</details>

## Ask about a star

- “Download and calibrate the Gaia DR3 mean XP spectrum for source `6719035052475592576`. Which stellar parameters do I still need before fitting?”
- “Fit this spectrum with the spectral type, extinction and effective temperature in my metadata. Show me how well the model fits the blue continuum and how uncertain the accretion flux is.”
- “Use the saved fit in `runs/target`. Find photometry and archival spectra of the same star and add them to an English report. For each spectrum, give the match, observing time, instrument, resolution and flux units.”

You can also select DR3 candidates by sky position, magnitude or colour. The report can display calibrated spectra by epoch, with the DR3 mean as a separate reference. For official DR4 XP, version 0.7.0 can check archive availability. Downloading, calibrating and fitting DR4 epochs still require a verified adapter. [Gaia selection and download](docs/gaia_download.md) · [Epoch spectra](docs/epochs.md)

## Prepare a new fit

**Model files.** The Python package includes the 1,620 FRAPPE hydrogen slab spectra and both photospheric calibration tables. Supply your authorized copy of the Fang photospheric template, `Gaia_template_final_new_final.sav`. For example, put the file in `~/astro-data/fang` and run these commands from the research folder.

```sh
.venv-gaia-xp/bin/gaia-xp assets import --from-dir "$HOME/astro-data/fang"
.venv-gaia-xp/bin/gaia-xp assets check
```

A complete set reports `"status": "complete"` and `"checked_files": 1623`. The check lists the actual paths. On a Mac with default settings, the grid and tables come from the package and the imported template goes in `~/.cache/gaia-xp-workbench/assets/fang25-v1/fang/`. If you already have a complete directory with `fang/`, `slab_grid/` and `calibration/`, point `GAIA_XP_ASSETS` or the top-level `--assets-dir` option at it. [Grid and calibration files](src/gaia_accretion/resources/models/fang25-v1) · [File checksums](src/gaia_accretion/resources/assets.json) · [Sources and permissions](third_party/NOTICE.md)

**Stellar inputs.** Downloading XP needs no stellar priors. For a fit, supply the calibrated flux and its covariance or covariance factor in `spectrum.npz`. In `metadata.json`, record the exact Gaia source ID as a string, the external spectral type, visual extinction (`A_V`, mag), effective temperature (`teff_k`, K) and their sources. Run `inspect` first. When `ready_for_fit` is true, choose a new output directory for `fit`. [Input format and example](docs/input_format.md)

```sh
.venv-gaia-xp/bin/gaia-xp inspect --input spectrum.npz --metadata metadata.json
.venv-gaia-xp/bin/gaia-xp fit --input spectrum.npz --metadata metadata.json --output runs/target
```

**Why K0–M8?** The Fang templates span B2–M8. K0 is the earliest external spectral type accepted for a new fit. The main Corona Australis analysis used 41 K/M stars and treated three A stars as exploratory. Hotter photospheres are brighter in the blue and have intrinsic Balmer absorption, making a weak excess harder to separate. Their DR3 spectra can still be downloaded and compared. [Scientific scope](docs/scientific_scope.md)

## Read an accretion result

To make a report from a completed fit, choose a new report directory.

```sh
.venv-gaia-xp/bin/gaia-xp report --run runs/target --output reports/target
```

Open `reports/target/report.html` or share `overview.png` from the same folder. Start with the full spectrum, the blue enlargement and the residuals in the fitted bands. The corner plot shows the joint posterior conditional on positive accretion. Read it alongside `P0`, the posterior probability assigned to the model with zero excess. [Report guide](docs/report.md) · [Posterior guide](docs/inference.md)

- `r` is the ratio of the mean accretion and photospheric flux densities over 700–900 nm, after extinction.
- `Facc` is the intrinsic model accretion flux integrated over 50–2477.47 nm, in W m⁻². Its value outside the XP wavelength range depends on the slab model.
- `q = Facc/Fstar` compares accretion with the bolometric photospheric flux. To obtain `Fstar`, the fitter divides the dereddened photospheric flux density near 751 nm by a temperature-dependent coefficient. The correction uses the supplied `teff_k` throughout, even as the fit explores nearby spectral types. The second calibration table records the spectral type–temperature relation. [Method and limitations](docs/scientific_scope.md)

Add `--photometry`, `--spectra` or `--epochs` to the report command, each with a prepared directory for the same star. Matching records, units and observing times help you interpret differences. Extinction and slit losses can also change the observed flux between visits. [Survey photometry](docs/photometry.md) · [Archival spectra](docs/spectroscopy.md) · [Interpreting external observations](docs/external_evidence.md)

Version 0.7.0 passed 59 tests on Windows and generated an English report from a saved single-source fit. A macOS test result is still pending. The project’s own code has no specified open-source license. [Validation records](validation/README.md) · [Third-party licenses](third_party/NOTICE.md)
