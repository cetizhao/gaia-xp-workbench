# Gaia XP Accretion Fitter

English · [简体中文](README.zh-CN.md)

How much of a young star’s optical continuum comes from accretion? This fitter models the Gaia DR3 mean BP/RP (XP) spectrum of a K0–M8 star using a Fang photospheric template and a hydrogen accretion continuum. An English report shows the blue excess, the uncertainty in the accretion flux and any survey photometry or dated archival spectra you add for comparison.

**Already have `report.html`?** Open it in a browser. The figures and interactive spectra work offline. You can also rebuild a report from a saved fit. Only a new fit needs the model files.

## Use it through conversation on a Mac

Open your research folder in a local agent such as Codex, Claude Code, Cursor, Gemini CLI, GitHub Copilot or OpenCode. The agent needs a shell to run the fitter and an internet connection for initial installation and archive queries.

> Install `cetizhao/gaia-xp-workbench` with the Gaia and ESO extras in a Python 3.12 environment called `.venv-gaia-xp` in my research folder on this Mac. Use the repository’s skill installer for the agent I’m using. Check that a fresh shell can run the fitter, run the repository tests locally and tell me the Mac architecture, Python version and test results. If I supplied model files, verify them.

In a new chat, describe the observation or result you want.

> Download and calibrate the Gaia DR3 mean XP spectrum for source 6719035052475592576. Tell me what is still needed for a fit. Stop after checking the inputs.

> Make an English HTML report from the saved fit in `runs/target`. Show me where the model fits the blue continuum well and where the residuals are large.

If your client can run local commands but has no skill discovery, tell it to read `skills/gaia-xp-fit/SKILL.md` in the checkout and follow it. Use the release and full source ID when asking for photometry or archival spectra. The fitter can display calibrated epoch spectra and check DR4 availability. Download, calibration and fitting currently support **DR3 mean XP**. [Client setup](docs/agent-clients.md) · [Agent skill](skills/gaia-xp-fit/SKILL.md) · [Gaia data guide](docs/gaia_download.md)

## Install from a terminal

On macOS or Linux, use Git and **Python 3.12**.

```sh
git clone https://github.com/cetizhao/gaia-xp-workbench.git
cd gaia-xp-workbench
python3.12 -m venv .venv
.venv/bin/python -m pip install ".[gaia,spectroscopy]"
.venv/bin/python -m pip check
.venv/bin/gaia-xp --help
.venv/bin/python -m unittest discover -s tests
```

The `gaia` extra adds GaiaXPy for flux calibration. The `spectroscopy` extra adds Astropy for ESO FITS spectra. On Intel Macs, pip builds the pinned `extinction` library from source and may need Apple's Command Line Tools. PyPI provides a prebuilt Python 3.12 package for Apple silicon. For local fitting or reporting alone, install `.`. Run the examples below from the checkout, or call the executable by its absolute path. [extinction release files](https://pypi.org/project/extinction/0.4.8/#files)

On Windows, follow the same `git clone` and `cd` steps, then run these PowerShell commands.

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install ".[gaia,spectroscopy]"
.\.venv\Scripts\gaia-xp.exe --help
```

To make the skill available in another research folder, run the installer from this checkout. For example, to use Claude Code and Cursor on the same Mac project, substitute the folder you open in those clients.

```sh
python3.12 scripts/install_skill.py --project "/path/to/research" --agent claude-code cursor
```

Use `--agent all` to install for every listed client. The installer copies the skill and its references locally. Clients can share the same `gaia-xp` executable. If you installed the fitter in the checkout’s `.venv` as above, give each client its absolute executable path or make it available on `PATH`.

## Model files for a new fit

Version 0.7.0 ships the 1,620 FRAPPE hydrogen slab spectra and both photospheric calibration tables with the Python package. For a new fit, the one file to bring to your Mac is your authorized copy of the Fang template, `Gaia_template_final_new_final.sav`. Put it in a folder such as `~/astro-data/fang` and import it once.

```sh
.venv/bin/gaia-xp assets import --from-dir "$HOME/astro-data/fang"
.venv/bin/gaia-xp assets check
```

A complete installation reports `"status": "complete"` and `"checked_files": 1623`. The check lists the location of each group and any missing files. The default on macOS is to combine the installed grid and tables with the Fang template in `~/.cache/gaia-xp-workbench/assets/fang25-v1` (or under `XDG_CACHE_HOME`). On Windows the cache starts at `%LOCALAPPDATA%\gaia-xp-workbench\assets\fang25-v1`. If you already have a complete asset directory with `fang/`, `slab_grid/` and `calibration/`, point `GAIA_XP_ASSETS` or the top-level `--assets-dir` at it to use that directory for every group. [Bundled model files](src/gaia_accretion/resources/models/fang25-v1) · [Asset checksums](src/gaia_accretion/resources/assets.json) · [Sources and redistribution](third_party/NOTICE.md)

## Fit one star

The Fang grid spans B2–M8. The fitter accepts external spectral types from K0 through the M8 grid edge. In Corona Australis, the main analysis used 41 K/M stars, with three A stars treated separately as exploratory cases. Hotter photospheres emit more blue light and have intrinsic Balmer absorption, which complicates the separation of accretion emission. Earlier types can still be downloaded, calibrated and compared with other observations.

Use `spectrum.npz` for the calibrated spectrum and its covariance or covariance factor. In `metadata.json`, give the source ID as a decimal string, the external spectral type, visual extinction (`A_V`, mag), effective temperature (`teff_k`, K) and their source. You can download and calibrate XP before adopting those stellar parameters. [Input format](docs/input_format.md)

```sh
.venv/bin/gaia-xp inspect --input spectrum.npz --metadata metadata.json
```

Read `ready_for_fit`, `blockers` and `notes`. Once the checks pass, fit into a new directory.

```sh
.venv/bin/gaia-xp fit --input spectrum.npz --metadata metadata.json --output runs/target
```

In `runs/target/report.md`, `r` is the accretion-to-photosphere flux density ratio over 700–900 nm. `Facc` is the intrinsic model accretion flux integrated over 50–2477.47 nm (W m⁻²). Its ratio to the bolometric photospheric flux is `q = Facc/Fstar`. The uncertainty intervals depend on the assumed photosphere, extinction and slab spectra. [Posterior guide](docs/inference.md) · [Scientific limitations](docs/scientific_scope.md)

**Why two calibration tables?** To estimate `Fstar`, the fitter divides the dereddened model photospheric flux density near 751 nm by a temperature-dependent coefficient from the bolometric correction table. The second table relates spectral type to temperature. For this correction the fitter uses the `teff_k` you supplied throughout the fit, even as it explores nearby spectral types. Gaia’s instrumental flux calibration takes place earlier, when preparing the spectrum.

## Make a report from a saved fit

Point `--run` at a complete fit and choose a new report directory.

```sh
.venv/bin/gaia-xp report --run runs/target --output reports/target
```

Open `reports/target/report.html` or share `overview.png` from the same folder. The overview shows the full spectrum, the blue end, residuals and the joint posterior conditional on positive accretion. The report also gives the posterior probability of the model with no excess continuum.

Add `--photometry`, `--spectra` or `--epochs` with a prepared directory for the same star. Epoch spectra carry their observation times, with the DR3 mean spectrum shown as a reference. A difference between observations taken years apart can reflect extinction or calibration as well as accretion. [Reports](docs/report.md) · [Photometry](docs/photometry.md) · [Spectroscopy](docs/spectroscopy.md) · [Epochs](docs/epochs.md) · [Interpreting external observations](docs/external_evidence.md)

The project has recorded a Windows single-source comparison with the original fit. Project-authored code currently has no specified open-source license. [Validation records](validation/README.md) · [Third-party credits and licenses](third_party/NOTICE.md)
