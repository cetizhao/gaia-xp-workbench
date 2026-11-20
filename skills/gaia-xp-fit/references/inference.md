# Spectral-type grid and posterior plots

English · [简体中文](inference.zh-CN.md)

The model varies spectral type (SpT), with K0 = 60 and M0 = 70. It can linearly interpolate photospheric templates between adjacent nodes, including fractional subtypes. Numerical integration evaluates a finite set of spectral types, so posterior draws occupy only those evaluated nodes.

For source `6719035052475592576`, the calculation used 33 nodes from SpT = 64 to 68, separated by 0.125 subtype. The 8,000 saved draws from the positive-accretion branch occupied 27 of those nodes. The older corner plot divided the sampled range into 32 equal bins, each about 0.102 subtype wide. Some bins fell entirely between grid nodes, leaving the appearance of gaps in spectral type.

The plot now puts each bin boundary halfway between regularly spaced nodes. Each column shows the probability mass associated with its node. A node between populated nodes can still have no samples. The plot uses the saved samples without jitter or density interpolation, preserving the reported intervals and spectral-type precision.

To refine the integration from 0.125 to 0.0625 subtype or finer, evaluate the likelihood and integrate at the additional nodes. Then check how much the accretion-flux interval and zero-branch weight change. The fitter already checks successively finer grids. This source met the convergence criteria at 33 nodes. Drawing more samples for the figure alone cannot measure integration error or supply additional template information. The plotting change used the existing fit.

## Grid integration, MCMC and nested sampling

For the same likelihood and priors, the choice depends on the number of parameters, the shape of the posterior and whether the analysis needs a model evidence. A smooth-looking corner plot is insufficient to assess numerical accuracy.

| Method | Strength in this application | Checks and costs |
|---|---|---|
| Grid integration | With few continuous parameters, one can sum explicitly over slab spectra and over the zero and positive branches, obtaining their marginal likelihoods. | The cost multiplies with each extra dimension. Check convergence under refinement, parameter boundaries and narrow peaks. |
| Markov chain Monte Carlo (MCMC) | Can explore a joint posterior with additional continuous parameters without evaluating a full grid. | Draws are correlated. Check effective sample size and whether chains cover all modes. Ordinary posterior sampling does not directly yield the model evidence. |
| Nested sampling | Estimates both the posterior and model evidence, including for branch comparisons and multimodal models. | Narrow modes can be missed. Check sampling error with enough live points and independent repeats. |

For MCMC, the autocorrelation time helps quantify the number of effectively independent draws. For nested sampling, the number of live points affects the ability to locate narrow modes. [emcee autocorrelation guide](https://emcee.readthedocs.io/en/stable/tutorials/autocorr/) · [Speagle 2020](https://arxiv.org/abs/1904.02180) · [dynesty FAQ](https://dynesty.readthedocs.io/en/stable/faq.html)

The current grid provides a calculation that can be checked by direct refinement. If future analyses add continuous slab parameters, stellar parameters shared across epochs, or additional calibration parameters, compare MCMC and nested sampling against the grid using the same priors and likelihood. Compare both accuracy and runtime. Physical calibration of an accretion measurement still requires observational evidence independent of the sampling algorithm.
