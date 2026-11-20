# What can archival spectra tell us about Gaia XP?

English · [简体中文](external_evidence.zh-CN.md)

An external spectrum can test the XP continuum shape, reveal emission associated with accretion or help identify contamination. The wavelength coverage and flux calibration determine which comparisons an instrument can support.

| Instrument | Wavelength coverage and resolving power | Main use |
|---|---|---|
| Gaia XP | About 330–1050 nm at low, wavelength-dependent resolution. The fitter uses 336–1020 nm. | Continuum shape and, with future epoch products, changes between visits |
| X-shooter | About 300–2500 nm. Common slit configurations give R ≈ 4,000–17,000, depending on arm and slit width. | Balmer jump, continuum and emission lines. Prefer wide-slit spectra for absolute flux comparisons. |
| ESPRESSO | 380–788 nm. HR, UHR and MR modes give R ≈ 140,000, 190,000 and 70,000, respectively. | Resolved line profiles, radial velocities and changes in line shape |

Resolving power is R = λ/Δλ, where Δλ is the width of a resolution element. Pixel sampling is a separate property. For a particular product, check the usable wavelengths, slit width, data quality and units. [Gaia DR3 instrument paper](https://doi.org/10.1051/0004-6361/202243940) · [ESO X-shooter](https://www.eso.org/public/teles-instr/paranal-observatory/vlt/vlt-instr/x-shooter/) · [ESO ESPRESSO operating modes](https://www.eso.org/sci/facilities/paranal/instruments/espresso/overview.html)

The full X-shooter range spans XP. ESPRESSO overlaps about 60% of the fitter’s wavelength interval (408/684 nm). This fraction describes wavelength span. It says nothing about the fraction of candidate stars observed or how much information two spectra share. ESPRESSO starts redward of the Balmer jump at 364.6 nm, so its main contribution is line spectroscopy. Variable fibre losses also limit its use as an absolute continuum flux reference. [ESO ESPRESSO reduction manual](https://ftp.eso.org/pub/dfs/pipelines/espresso/espdr-pipeline-manual-3.3.10.pdf)

## Measure coverage for a defined candidate list

Use the number of distinct stars in the candidate list as the denominator for each of three fractions:

1. Stars with a securely matched external spectrum of usable quality.
2. Stars with sufficient wavelength coverage and flux calibration to test the accretion continuum.
3. Stars with observations close in time to an actual DR4 spectral epoch.

Multiple exposures, arms and reductions of one star count once in each fraction. Query the archive metadata first, then download suitable products. Record the match separation, proper motion, component identity and any failed queries or non-detections. Check the identity of a nearby positional candidate before associating it with the Gaia source.

The observing period announced for DR4 runs from **2014-07-25 to 2020-01-20**. For the worked example, the X-shooter observations (2022) and ESPRESSO observations (2024–2025) all fall outside that interval. They provide comparisons at other dates. Once the actual Gaia epochs are available, calculate the time separations and define “close” using the timescale of the variability under study. A spectral difference alone cannot identify accretion as its cause. The archive search was verified for one source. A defined candidate list is still needed to estimate sample coverage. [Gaia partner data centre](https://gaia.aip.de/cms/data/gdr4/)
