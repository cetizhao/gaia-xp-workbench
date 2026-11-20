# 第三方来源与发布状态

此仓库包含从 GaiaAccretion 提取的传统拟合实现。项目自有部分尚未指定开源许可证。下面的原始许可分别适用对应第三方材料，不能合并改写。

- **Fang & Herczeg 2025 光球模板**（arXiv:2509.19693）：SAV 的 SHA256 在资产清单中。本地记录没有可核实的下载 URL 或再分发授权；文件只放本地缓存，未加入仓库。
- **Rik Claes / FRAPPE**：作者 slab 网格和两张 HH14 光度/温度校准表，来自提交 `f2bebaa6a477c6f9a1c830ab4aad52947a3eecc2`；原 MIT 文本见 [FRAPPE_MIT.txt](FRAPPE_MIT.txt)。每个资产的 URL 与 SHA256 随程序清单保存。引用 Claes et al. 2024，DOI 10.1051/0004-6361/202450885。
- **Lauren Willett 等 / nuts-for-ysos**：本地修订 slab 内核的公式参考代码来自提交 `a845122269921f2b6eaf9ba4f71b130588756ad5`，原 CC BY 4.0 文本见 [nuts_for_ysos_CC_BY_4_0.txt](nuts_for_ysos_CC_BY_4_0.txt)。修订包括 H⁻/Gaunt 公式核对和短波段外推处理；本次只提取此前核验实现，没有重新设计公式。来源：https://github.com/laurenwillett/nuts-for-ysos 。

科学核心的逐函数提取来源及原文件哈希在安装包 `resources/extraction.json`。本地验证输入与旧后验仅用于迁移回归，保存在忽略目录，不作为可公开分发的实测示例。
