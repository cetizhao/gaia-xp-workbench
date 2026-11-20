# Compare archival spectra with Gaia XP

English · [简体中文](spectroscopy.zh-CN.md)

Start with a Gaia DR3 source identifier to search the ESO archive for reduced one-dimensional spectra and check MAST for spectral coverage. Select products from the search results for download. Install `pip install ".[spectroscopy]"` to read ESO FITS files. Once the spectra are prepared, the core package can generate the report offline.

```text
gaia-xp spectra-search --source-id 6719035052475592576 --output DISCOVERY
gaia-xp spectra-fetch --discovery DISCOVERY --output SPECTRA
gaia-xp report --run RUN --spectra SPECTRA --output REPORT
```

The search radius defaults to 5″ and can be increased to 10″. The initial query is centred on the Gaia reference position. The fitter then uses the observation date and proper motion to check the angular separation. A high-proper-motion source can fall outside the initial search radius. Agreement in pointing and target name still leaves the possibility of a companion or blending in the slit. ESO candidates come from ObsCore, and the download uses the primary product link returned by DataLink. MAST support currently covers discovery only. [ESO programmatic access](https://www.eso.org/cms/eso-data/programmatic-access.html)

By default the fitter recommends the latest X-shooter observation group with both UVB and VIS coverage and keeps its optical settings, up to six products. If there is no suitable group, inspect the candidates. Repeat `--product-id` to select specific products returned by the query. The converter accepts standard one-dimensional ESO tables with explicit absolute flux units. Products in counts or continuum-normalized units do not meet this requirement. The download saves the original FITS files, accompanying documentation, query responses, observation dates, slit widths, nominal resolving powers, units and checksums.

Each spectrum’s legend gives the instrument and arm, wide or narrow slit, observation date and time down to seconds, and time scale. The table retains the full recorded precision. For the worked example, ESO `DATE-OBS` gives the start of the exposure, and the product uses UTC. Check the time definition and scale for other products and mark any missing values. Gaia DR3 appears as a mean spectrum over several years. Its astrometric reference epoch does not date the spectrum.

## V721 CrA

The Gaia source in the command above has wide- and narrow-slit X-shooter UVB and VIS spectra on 2022-05-06. The example uses four optical products. The NIR products and later ESPRESSO observations remain in the candidate list. The 5″ wide-slit spectra are the more suitable comparison for the spectral energy distribution. The 0.5″/0.4″ narrow slits give higher resolution for inspecting Balmer line profiles, but substantial slit losses complicate any inference about changes in absolute brightness.

The original X-shooter flux density is in erg s⁻¹ cm⁻² Å⁻¹. Multiply flux and uncertainty by 0.01 to obtain W m⁻² nm⁻¹. The converter preserves negative flux values, and the plot uses valid pixels with `QUAL=0`. These products use air wavelengths in the ground-based observer’s frame and have no telluric absorption correction. The FITS field `SPEC_RES` gives the nominal resolving power from arc lamps. It is not a measurement for each exposure. The wide-slit products do not specify a quantitative uncertainty for the absolute flux calibration. [ESO product description](https://www.eso.org/rm/api/v1/public/releaseDescriptions/70)

Compare these spectra with mean XP to check the broad continuum, blue excess and emission lines. Simple wavelength bins do not reproduce the Gaia instrumental response, so point-by-point subtraction of narrow lines at different resolutions is inappropriate. Differences between dates can reflect stellar variability, extinction, slit losses or calibration. This comparison uses the saved XP fit and does not infer a new accretion rate.

Version 0.5.0 introduced display averages of 0.5 nm across the full spectrum and 0.2 nm at the blue end of the static figures. Hα retains the original sampling, and the red flux ratio still uses 5 nm band integrals. Use the epoch panel to select and zoom in on the original samples. Finer display sampling preserves the instrumental resolution and the original observations and fit.
