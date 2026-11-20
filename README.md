# Gaia XP Accretion Fitter

English · [简体中文](README.zh-CN.md)

How much of a young star’s optical continuum comes from accretion? This fitter models the Gaia DR3 mean BP/RP (XP) spectrum of a K0–M8 star using a Fang photospheric template and a hydrogen accretion continuum. An English report shows the blue excess, the uncertainty in the accretion flux and any survey photometry or dated archival spectra you add for comparison.

**Already have `report.html`?** Open it in a browser. The figures and interactive spectra work offline. You can also rebuild a report from a saved fit. Only a new fit needs the model files.

## Use it through conversation on a Mac

Open your research folder in Codex and send this setup request. The agent needs shell access and an internet connection for installation and archive queries.

> Install `cetizhao/gaia-xp-workbench` from GitHub in a Python 3.12 virtual environment on this Mac, including Gaia downloads and ESO spectroscopy. Install the `skills/gaia-xp-fit` folder where Codex can discover it for this project. Record the absolute path to its `gaia-xp` executable in the project instructions and verify that it works in a fresh shell. If I have supplied a model folder, check it too.

In a new chat, describe the observation or result you want.

> Download and calibrate the Gaia DR3 mean XP spectrum for source 6719035052475592576. Tell me what is still needed for a fit. Stop after checking the inputs.

> Make an English HTML report from the saved fit in `runs/target`. Show me where the model fits the blue continuum well and where the residuals are large.

For a project-local installation, copy the whole `skills/gaia-xp-fit/` folder into the research project's `.agents/skills/` directory. Use the release and full source ID when asking for photometry or archival spectra. The fitter can display calibrated epoch spectra and check DR4 availability. Download, calibration and fitting currently support **DR3 mean XP**. [Agent skill](skills/gaia-xp-fit/SKILL.md) · [Gaia data guide, in Chinese](docs/gaia_download.md)

## Install from a terminal

On macOS or Linux, use Git and **Python 3.12**.

```sh
git clone https://github.com/cetizhao/gaia-xp-workbench.git
cd gaia-xp-workbench
python3.12 -m venv .venv
.venv/bin/python -m pip install ".[gaia,spectroscopy]"
.venv/bin/python -m pip check
.venv/bin/gaia-xp --help
```

The `gaia` extra adds GaiaXPy for flux calibration. The `spectroscopy` extra adds Astropy for ESO FITS spectra. For local fitting or reporting alone, install `.`. Run the examples below from the checkout, or call the executable by its absolute path.

On Windows, follow the same `git clone` and `cd` steps, then run these PowerShell commands.

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install ".[gaia,spectroscopy]"
.\.venv\Scripts\gaia-xp.exe --help
```

## Model files for a new fit

Copy a model folder you have permission to use. Its layout should be

```text
gaia-xp-assets/
├── fang/Gaia_template_final_new_final.sav
├── slab_grid/                              # 1,620 hydrogen continuum spectra (*.out)
└── calibration/
    ├── BolCorr_hh14_myCorr_wInteroplationOverVO.txt
    └── SpT_Teff_relation_hh14_short_codes.dat
```

To make the files available in future chats, import them once. Replace the example folder with yours.

```sh
.venv/bin/gaia-xp assets import --from-dir "$HOME/astro-data/gaia-xp-assets"
.venv/bin/gaia-xp assets check
```

Look for `"status": "complete"` and `"checked_files": 1623`. The default cache is `~/.cache/gaia-xp-workbench/assets/fang25-v1` on macOS and Linux (`XDG_CACHE_HOME` overrides `~/.cache`), or `%LOCALAPPDATA%\gaia-xp-workbench\assets\fang25-v1` on Windows. To use your files in place, point `GAIA_XP_ASSETS` at the folder containing the three directories, or pass `--assets-dir /path/to/gaia-xp-assets` before a subcommand.

The Fang template requires your own authorized copy. The slab grid and both calibration tables come from FRAPPE. [Asset checksums](src/gaia_accretion/resources/assets.json) · [Upstream FRAPPE files](https://github.com/RikClaes/FRAPPE/tree/f2bebaa6a477c6f9a1c830ab4aad52947a3eecc2/src/frappe/models_grid)

## Fit one star

The Fang grid spans B2–M8. The fitter accepts external spectral types from K0 through the M8 grid edge. In Corona Australis, the main analysis used 41 K/M stars, with three A stars treated separately as exploratory cases. Hotter photospheres emit more blue light and have intrinsic Balmer absorption, which complicates the separation of accretion emission. Earlier types can still be downloaded, calibrated and compared with other observations.

Use `spectrum.npz` for the calibrated spectrum and its covariance or covariance factor. In `metadata.json`, give the source ID as a decimal string, the external spectral type, visual extinction (`A_V`, mag), effective temperature (`teff_k`, K) and their source. You can download and calibrate XP before adopting those stellar parameters. [Input format, in Chinese](docs/input_format.md)

```sh
.venv/bin/gaia-xp inspect --input spectrum.npz --metadata metadata.json
```

Read `ready_for_fit`, `blockers` and `notes`. Once the checks pass, fit into a new directory.

```sh
.venv/bin/gaia-xp fit --input spectrum.npz --metadata metadata.json --output runs/target
```

In `runs/target/report.md`, `r` is the accretion-to-photosphere flux density ratio over 700–900 nm. `Facc` is the intrinsic model accretion flux integrated over 50–2477.47 nm (W m⁻²). Its ratio to the bolometric photospheric flux is `q = Facc/Fstar`. The uncertainty intervals depend on the assumed photosphere, extinction and slab spectra. [Posterior guide](docs/inference.md) · [Scientific limitations](docs/scientific_scope.md) (both in Chinese)

**Why two calibration tables?** To estimate `Fstar`, the fitter divides the dereddened model photospheric flux density near 751 nm by a temperature-dependent coefficient from the bolometric correction table. The second table relates spectral type to temperature. For this correction the fitter uses the `teff_k` you supplied throughout the fit, even as it explores nearby spectral types. Gaia’s instrumental flux calibration takes place earlier, when preparing the spectrum.

## Make a report from a saved fit

Point `--run` at a complete fit and choose a new report directory.

```sh
.venv/bin/gaia-xp report --run runs/target --output reports/target
```

Open `reports/target/report.html` or share `overview.png` from the same folder. The overview shows the full spectrum, the blue end, residuals and the joint posterior conditional on positive accretion. The report also gives the posterior probability of the model with no excess continuum.

Add `--photometry`, `--spectra` or `--epochs` with a prepared directory for the same star. Epoch spectra carry their observation times, with the DR3 mean spectrum shown as a reference. A difference between observations taken years apart can reflect extinction or calibration as well as accretion. The detailed guides are in Chinese. [Reports](docs/report.md) · [Photometry](docs/photometry.md) · [Spectroscopy](docs/spectroscopy.md) · [Epochs](docs/epochs.md) · [Interpreting external observations](docs/external_evidence.md)

The project has recorded a Windows single-source comparison with the original fit. Project-authored code currently has no specified open-source license. [Validation records, in Chinese](validation/README.md) · [Third-party credits and licenses](third_party/NOTICE.md)
