# The fitting method, physical quantities and limitations

English · [简体中文](scientific_scope.zh-CN.md)

The fitter uses the low-resolution continuum of a young star’s Gaia DR3 mean XP spectrum to constrain its photosphere, extinction and additional accretion continuum. The portable Fang broad-band method accepts externally calibrated spectra of K0–M8 stars with correlated flux uncertainties. Software checks establish whether a calculation runs and converges. Establishing the accuracy of a physical accretion measurement requires independent observations.

## What enters the fit

The Fang & Herczeg (2025) photospheric templates are already at XP resolution. The code uses them without further broadening. It applies an approximate XP response to 1,620 hydrogen slab spectra from the authors’ grid and 24 additional optically thick slabs. Fluxes in 16 broad bands enter a Student-t likelihood with four degrees of freedom and the full propagated band covariance. The mean flux density over 700–900 nm defines the scale and the optical excess ratio. It does not contribute a seventeenth independent observation.

The external spectral type sets the centre of a prior with standard deviation 0.5 subtype and support within ±2 subtypes, truncated at the template boundaries. The visual-extinction prior has standard deviation 0.25 mag and extends ±0.6 mag around the external value, with total extinction constrained to be nonnegative. The extinction law uses `Rv=3.1`. The positive-accretion branch has a log-uniform prior on the red excess ratio `r` from 10⁻⁴ to 3. The other branch has exactly zero excess. Each has prior weight 0.5. The 5% feature-mismatch term and 1% red-flux error floor are adopted model settings. Their sizes have not been measured as empirical template uncertainties.

The fitter obtains the posterior by evidence-weighted numerical integration and joint sampling. The corner plot shows degeneracies among model parameters. Chain convergence is a separate question for MCMC. This version runs no automatic prior-sensitivity comparison, so an apparently narrow interval may owe part of its width to the adopted priors.

## Reported quantities

| Field | Physical meaning |
|---|---|
| `r_red` | Reddened slab-to-photosphere ratio of mean flux densities over 700–900 nm, dimensionless. |
| `facc_w_m2` | Intrinsic model slab flux integrated over 50–2477.47 nm, in W m⁻². Energy outside the observed band depends on the model. |
| `q_model_facc_over_fstar` | `Facc` divided by the model bolometric photospheric flux, dimensionless. This refers to the integrated fluxes, whereas `r` refers to the red optical band. |
| `p_zero` | Posterior weight of the zero-accretion branch under the adopted model and priors. Its calibration as a probability of truly absent accretion is unknown. |
| `ln_bayes_factor` | Natural logarithm of the evidence for the positive branch divided by that for the zero branch. |

Reported accretion quantiles include the exact-zero branch. A zero median can reflect substantial probability in that branch even when the data allow a positive upper limit. A 95% posterior upper limit refers to the fitted model and its priors. The instrumental detection threshold requires a separate calibration. Interpret the corner plot, conditional on the positive branch, alongside `P0`. Accretion luminosity (`Lacc`) also requires a distance. Mass accretion rate (`Mdot`) additionally requires stellar mass, radius and a truncation-radius assumption. The intervals hold those inputs fixed.

## Reading the fit and diagnostics

Inspect the full spectrum and the enlargement around the blue end and Balmer jump. Then examine the residuals in the 16 fitted bands and the joint posterior. The plotted model intervals come from saved joint samples. Observed samples and fitted bands have correlated errors, so these plotted residuals do not support a conventional reduced χ² calculated by assuming independence. The wavelength-by-wavelength medians of the components need not sum to the median of the total model.

The numerical checks require changes below 0.05 in each branch’s log evidence and below 0.02 subtype in mean spectral type. They also check convergence of the integration over `r` and `Av`. Diagnostic thresholds include a blue signal-to-noise ratio of 3, a red residual threshold of 0.1 and a parameter-boundary probability of 0.1. Their detection efficiencies have not been calibrated. Report missing external blending information as unknown. A source with no diagnostic flags still needs independent physical validation.

The identities of the stars contributing to the Fang templates and the templates’ full wavelength covariance are incompletely known. Independence from the science sample needs a separate check. Blue calibration errors, chromospheric emission, photospheric mismatch, the approximate response, extrapolation beyond XP wavelengths, geometry and observations taken at different times can all affect the interpretation. A close fit, small `P0` or stable integration alone cannot establish universal calibration.

## Samples and time variability

Count each star once when reporting the number of independent sources, even if it has several fits, observing epochs or noise realizations. `summarize` collects the selected runs, retaining upper limits and diagnostics. It leaves their posteriors separate and does not infer population correlations.

A nonlinear fit to a DR3 mean spectrum measures neither an individual epoch nor necessarily the true time-averaged accretion rate. Using DR4 requires a separate adapter verified against the official products, identities across releases, time definitions, flux calibration, response and covariance. Keep the correct release in the metadata. Resolution-degraded X-shooter spectra and prerelease epoch astrometry cannot serve as observed Gaia DR4 XP epochs.
