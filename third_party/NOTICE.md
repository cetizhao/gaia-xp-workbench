# Third-party materials

English · [简体中文](NOTICE.zh-CN.md)

The fitter includes the classical fitting implementation extracted from GaiaAccretion. No open-source license has been specified for the project's own code. Each third-party license applies to the material identified below.

**Fang & Herczeg photospheric templates.** The asset manifest identifies the exact `Gaia_template_final_new_final.sav` used in these fits by its SHA-256. Public redistribution of that file is awaiting authorization. Users can import an authorized copy. The paper describes how the templates were constructed, and its published Table 1 is a catalogue of Sco-Cen stars. [Fang & Herczeg (2025)](https://doi.org/10.3847/1538-4357/ae0f9a) · [Published Table 1](https://doi.org/10.3847/1538-4357/ae0f9a/data1)

**FRAPPE spectra and calibration tables.** The package distributes the 1,620 hydrogen slab spectra and two photospheric calibration tables exactly as provided by Rik Claes' FRAPPE repository at commit `f2bebaa6a477c6f9a1c830ab4aad52947a3eecc2`. Copyright © 2026 RikClaes. The asset manifest records the upstream URL and SHA-256 for each file. The slab models follow Rigliaco et al. and Manara et al. The tables use the Herczeg & Hillenbrand temperature scale and the 751 nm bolometric correction adopted by Claes et al. [MIT license](FRAPPE_MIT.txt) · [Original files](https://github.com/RikClaes/FRAPPE/tree/f2bebaa6a477c6f9a1c830ab4aad52947a3eecc2/src/frappe/models_grid) · [Rigliaco et al. (2012)](https://doi.org/10.1051/0004-6361/201219832) · [Manara et al. (2013)](https://doi.org/10.1051/0004-6361/201321866) · [Herczeg & Hillenbrand (2014)](https://doi.org/10.1088/0004-637X/786/2/97) · [Claes et al. (2024)](https://doi.org/10.1051/0004-6361/202450885)

**Lauren Willett and contributors, nuts-for-ysos.** The local slab calculation follows reference code at commit `a845122269921f2b6eaf9ba4f71b130588756ad5`. The local implementation includes checks of the H⁻ opacity and Gaunt-factor formulae and a treatment of short-wavelength extrapolation. The fitter incorporates this previously checked implementation. [CC BY 4.0 license](nuts_for_ysos_CC_BY_4_0.txt) · [Reference code](https://github.com/laurenwillett/nuts-for-ysos)

The package's `resources/extraction.json` records the origins and file hashes of the scientific functions. Local validation spectra and saved posteriors reside in the ignored `.local/` directory and are used for regression checks.
