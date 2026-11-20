# 外部光谱证据与 Gaia DR4 对照

[English](external_evidence.md) · 简体中文

外部光谱用于检查 XP 的连续谱形、吸积活动和可能的污染。不同仪器提供的证据不同；高分辨率本身不代表能够校准吸积光度。

| 仪器 | 波长范围与分辨率 | 主要用途 |
|---|---|---|
| Gaia XP | 约 330–1050 nm，低分辨率且随波长变化；本工作台使用 336–1020 nm | 连续谱形与未来逐历元变化 |
| X-shooter | 约 300–2500 nm；常用狭缝 R≈4000–17000，实际取决于臂和缝宽 | Balmer 跳跃、连续谱和发射线；宽缝谱优先检查绝对通量 |
| ESPRESSO | 380–788 nm；HR/UHR/MR 模式 R≈140000/190000/70000 | 精细谱线、视向速度及线形变化 |

R=λ/Δλ，不是波长采样间隔。范围与性能见 [Gaia DR3 团队论文](https://doi.org/10.1051/0004-6361/202243940)、[X-shooter](https://www.eso.org/public/teles-instr/paranal-observatory/vlt/vlt-instr/x-shooter/) 和 [ESPRESSO 科学运行页](https://www.eso.org/sci/facilities/paranal/instruments/espresso/overview.html)；具体产品仍须核对有效波段、缝宽、质量与单位。

X-shooter 全波段覆盖 XP；ESPRESSO 覆盖本工作台波长跨度的约 60%（408/684 nm）。这是线性波长长度比例，不是信息量或候选源覆盖率。ESPRESSO 不含 364.6 nm 的 Balmer 跳跃，适合提供谱线证据；其绝对通量还受可变光纤损失影响，不能直接替代蓝端连续谱标定。[ESO 归约说明](https://ftp.eso.org/pub/dfs/pipelines/espresso/espdr-pipeline-manual-3.3.10.pdf)

## 对明确候选清单逐源统计

分别统计：①有身份可靠、质量可用的外部光谱；②有波段和通量标定足以检查吸积连续谱的资料；③有时间接近实际 DR4 历元的观测。各项分母均为同一候选清单中的独立恒星数；同源不同曝光、光谱臂或归约版本不增加恒星数。先查档案元数据，再下载合适产品，保留匹配距离、自行、分量身份和失败／未检出状态，不将最近位置候选自动当作同源。

DR4 预告的观测范围为 **2014-07-25 至 2020-01-20**。[官方合作档案中心](https://gaia.aip.de/cms/data/gdr4/) 当前示例源的 X-shooter（2022）与 ESPRESSO（2024–2025）均不在此范围，只能提供非同期证据。以后按实际历元计算时间差，并根据所研究的变化时间尺度说明“接近”的标准；光谱差异不能直接归因为吸积变化。当前仅验证单源，候选清单和样本覆盖率尚未确定。
