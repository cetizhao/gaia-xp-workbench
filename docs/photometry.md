# Survey photometry for one star

English · [简体中文](photometry.zh-CN.md)

Survey photometry extends the observed spectral energy distribution of a young star. The optical points can be compared with Gaia XP, while near- and mid-infrared measurements show emission at longer wavelengths. The measurements leave the saved XP fit intact. The fitter does not derive an accretion rate from an infrared excess.

## Query and display

Use version 0.3.0 or a later compatible release. Supply the exact Gaia DR3 source ID and choose new output directories.

```text
gaia-xp photometry --source-id 6719035052475592576 --output PHOTOMETRY_DIRECTORY
gaia-xp report --run RUN --photometry PHOTOMETRY_DIRECTORY --output NEW_REPORT_DIRECTORY
```

The first command queries the catalogues online for this star. The second reads the saved data and can run offline. To move the observations to another computer, copy the whole photometry directory, including the catalogue responses in `raw/`, the prepared `photometry.json` and the file inventory `manifest.json`. The report shows the spectrum and photometry together and retains the band measurements, match candidates and sources.

## Catalogues and matching

The query uses VizieR/CDS first. Gaia DR3 provides the position and proper motion. [Gaia DR3, I/355/gaiadr3](https://cdsarc.cds.unistra.fr/viz-bin/cat/I/355)

| Catalogue | Bands shown | Magnitude system | What to check |
|---|---|---|---|
| [APASS DR9, II/336/apass9](https://cdsarc.cds.unistra.fr/viz-bin/cat/II/336) | g′, r′, i′ | AB | The large aperture can blend neighbours. The catalogue does not supply a per-source observing epoch. |
| [2MASS, II/246/out](https://cdsarc.cds.unistra.fr/viz-bin/cat/II/246) | J, H, Ks | Vega | Distinguish reliable photometry, poor-quality measurements and upper limits. |
| [AllWISE, II/328/allwise](https://cdsarc.cds.unistra.fr/viz-bin/cat/II/328) | W1–W4 | Vega | Check blending, contamination and extended-source flags at the survey’s lower angular resolution. |

The default search radius is 3″. Set `--radius-arcsec` to change it, up to 10″. A match is adopted only if a single candidate falls within the radius. Multiple candidates remain available for inspection. For 2MASS and AllWISE, the Gaia position is propagated by proper motion to the approximate survey epoch. For 2MASS the candidate’s observation date provides a further check on the angular separation. APASS lacks per-source epochs, so the comparison uses the Gaia 2016 position and records that limitation. J2000 denotes the coordinate equinox and supplies no observation date.

The output retains search positions, candidates and angular separations. It records no match, inadequate measurement quality and failed network requests separately. A failed catalogue query gives no evidence for a survey nondetection. Measurements flagged for contamination or saturation remain visible, distinguished from those passing the quality cuts.

## Units and interpretation

The catalogue magnitudes and their uncertainties are preserved. Using the zero point for the appropriate magnitude system, the conversion to flux density is Fν = Fν,0 × 10^(−0.4m) in Jy, where 1 Jy = 10⁻²⁶ W m⁻² Hz⁻¹. Magnitude errors are propagated to flux errors. The record includes the zero point, representative wavelength and reference. Upper limits are marked separately from detections, and a missing error remains unknown.

AllWISE uses a 95% upper limit. For 2MASS the CDS description specifies 95% and the survey FAQ gives 97%. The report retains the 2MASS upper-limit flag without assigning a common confidence level. [CDS description](https://vizier.cfa.harvard.edu/ftp/cats/II/246/ReadMe) · [2MASS FAQ](https://www.ipac.caltech.edu/2mass/releases/allsky/faq.html)

Read each APASS error with its `u_e_*mag` flag. A value of 0 denotes the standard deviation of repeated observations. A value of 1 denotes the Poisson error for a single observation. The standard deviation describes the scatter and is distinct from the standard error of the mean. [APASS table description](https://vizier.cfa.harvard.edu/ftp/cats/II/336/ReadMe)

The plot places each photometric measurement at its filter’s representative wavelength and converts XP from Fλ to the same Fν units. The display uses no filter integration of XP, colour correction or extinction correction. Variability between epochs, aperture size, blending and calibration can all produce offsets. An offset alone does not establish a change in accretion. Infrared photometry does not extend the fitted XP continuum model.

The photometry directory records catalogue identifiers, query URLs, retrieval times, field units, quality flags and checksums of the retrieved files. The HTML shows the comparison first. Expand the photometry and cross-match tables for details. When adding higher-quality spectroscopy, verify the observing time, instrumental resolution, and wavelength and flux calibration before interpreting it as independent evidence about accretion.
