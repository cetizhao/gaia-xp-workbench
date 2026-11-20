# 第三方来源与发布状态

此仓库包含从 GaiaAccretion 提取的传统拟合实现。项目自有部分尚未指定开源许可证。下面的原始许可分别适用对应第三方材料，不能合并改写。

- **Fang & Herczeg (2025)** provided the photospheric template used in the fit. The asset manifest records the SHA-256 of `Gaia_template_final_new_final.sav`. Redistribution terms for this specific SAV file have not been independently verified. The published machine-readable Table 1 contains stellar catalogue entries. [Paper](https://doi.org/10.3847/1538-4357/ae0f9a) · [Table 1](https://doi.org/10.3847/1538-4357/ae0f9a/data1).
- **Rik Claes / FRAPPE** supplies the 1,620 hydrogen slab spectra and both photospheric calibration tables distributed with the fitter. The files are unchanged from commit `f2bebaa6a477c6f9a1c830ab4aad52947a3eecc2`, copyright © 2026 RikClaes. See the [full MIT license](FRAPPE_MIT.txt) and [original model files](https://github.com/RikClaes/FRAPPE/tree/f2bebaa6a477c6f9a1c830ab4aad52947a3eecc2/src/frappe/models_grid). The slab models follow [Rigliaco et al. (2012)](https://doi.org/10.1051/0004-6361/201219832) and [Manara et al. (2013)](https://doi.org/10.1051/0004-6361/201321866). The tables draw on [Herczeg & Hillenbrand (2014)](https://doi.org/10.1088/0004-637X/786/2/97), with the 751 nm correction adopted by [Claes et al. (2024)](https://doi.org/10.1051/0004-6361/202450885).
- **Lauren Willett 等 / nuts-for-ysos**：本地修订 slab 内核的公式参考代码来自提交 `a845122269921f2b6eaf9ba4f71b130588756ad5`，原 CC BY 4.0 文本见 [nuts_for_ysos_CC_BY_4_0.txt](nuts_for_ysos_CC_BY_4_0.txt)。修订包括 H⁻/Gaunt 公式核对和短波段外推处理；本次只提取此前核验实现，没有重新设计公式。来源：https://github.com/laurenwillett/nuts-for-ysos 。

科学核心的逐函数提取来源及原文件哈希在安装包 `resources/extraction.json`。本地验证输入与旧后验仅用于迁移回归，保存在忽略目录，不作为可公开分发的实测示例。
