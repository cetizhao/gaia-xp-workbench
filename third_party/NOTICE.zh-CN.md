# 第三方材料与来源

[English](NOTICE.md) · 简体中文

本程序包含从 GaiaAccretion 提取的传统拟合实现。项目自有代码尚未指定开源许可证，各项第三方材料按下列许可使用。

**Fang & Herczeg 光球模板。** 资产清单用 SHA-256 标识当前拟合采用的 `Gaia_template_final_new_final.sav`。该文件的公开再分发尚待授权，用户可导入自己有权使用的副本。原论文介绍模板的构建方法，论文公开的表 1 为天蝎–半人马星协的恒星目录。[Fang & Herczeg (2025)](https://doi.org/10.3847/1538-4357/ae0f9a) · [期刊表 1](https://doi.org/10.3847/1538-4357/ae0f9a/data1)

**FRAPPE 光谱与校准表。** 安装包中的 1,620 个氢连续谱模型和两张光球校准表与 Rik Claes 的 FRAPPE 仓库提交 `f2bebaa6a477c6f9a1c830ab4aad52947a3eecc2` 逐字节一致。版权为 © 2026 RikClaes，资产清单列出了每个文件的上游地址和 SHA-256。网格采用 Rigliaco、Manara 等工作的模型，校准表采用 Herczeg & Hillenbrand 的温标及 Claes 等使用的 751 nm 总通量修正。[原 MIT 许可](FRAPPE_MIT.txt) · [上游文件](https://github.com/RikClaes/FRAPPE/tree/f2bebaa6a477c6f9a1c830ab4aad52947a3eecc2/src/frappe/models_grid) · [Rigliaco 等（2012）](https://doi.org/10.1051/0004-6361/201219832) · [Manara 等（2013）](https://doi.org/10.1051/0004-6361/201321866) · [Herczeg & Hillenbrand（2014）](https://doi.org/10.1088/0004-637X/786/2/97) · [Claes 等（2024）](https://doi.org/10.1051/0004-6361/202450885)

**Lauren Willett 等的 nuts-for-ysos。** 本地 slab 实现参考提交 `a845122269921f2b6eaf9ba4f71b130588756ad5` 的代码。修订包括核对 H⁻ 和 Gaunt 因子公式，以及处理短波段外推。本程序沿用此前已经核验的实现。[原 CC BY 4.0 许可](nuts_for_ysos_CC_BY_4_0.txt) · [参考代码](https://github.com/laurenwillett/nuts-for-ysos)

随包的 `resources/extraction.json` 记录了各科学函数的提取来源及原文件哈希。验证输入和已有后验保存在忽略目录 `.local/`，用于回归检查。
