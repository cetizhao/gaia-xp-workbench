# 选择 Gaia 源并取得 XP 光谱

DR3 平均 XP 可以按源编号下载连续基函数系数，并校准成与现有拟合入口相容的光谱。位置、亮度或颜色选出的只是候选，不能自动当作星协成员或年轻星。以名称选源时，agent 应先核实对应的 Gaia 发布版本与源编号；不把最近的同名或位置候选默认为同一分量。

## DR3：选源、下载与检查

校准需要附加依赖；独立环境安装 `pip install ".[gaia]"`。选源查询本身不需要 GaiaXPy。

```text
gaia-xp gaia-select --source-id 6719035052475592576 --output NEW_SELECTION
gaia-xp gaia-select --ra 287.44 --dec -37.07 --radius-arcmin 2 --g-max 15 --limit 20 --output NEW_SELECTION
gaia-xp gaia-fetch --source-id 6719035052475592576 --metadata PRIORS.json --output NEW_XP
```

源编号可重复指定；天区选择也可用 `--bp-rp-min`、`--bp-rp-max`。最多返回 100 个候选、天区半径最多 60′，超过结果上限会明确标为截断。没有已公开 XP 的候选仍保留，避免将产品可用性当成科学选样条件。按已选清单逐源调用 `gaia-fetch`，不隐式下载整个天区。

下载保留 ESA Archive 的源表与 XP 连续系数原响应、请求、获取日期和校验值。默认采用 GaiaXPy 2.1.2、不截断系数，在 336–1020 nm 每 2 nm 采样；通量密度单位为 W m⁻² nm⁻¹。BP、RP 各自的完整系数协方差传播到光谱，保存 `noise_factor`，满足 C=BBᵀ；跨 BP/RP 协方差未发布，采用零并明确记录。输出逐源通量与边缘误差须和 GaiaXPy 一致，不能只用逐点误差代替相关性。

ESA DataLink 服务不可用时，只尝试一次 [Gaia@AIP 的同版连续谱表](https://gaia.aip.de/metadata/gaiadr3/xp_continuous_mean_spectrum/)；提供方、失败响应和原始 VOTable 均保留。XML 转 CSV 只改变存储格式，系数及误差不变，不以另一版本或采样谱代替连续系数。

输出 `spectrum.npz`、`metadata.json`、`calibration.json` 和 `download.json`。若 `PRIORS.json` 提供来源明确的光谱型、Av、Teff，程序自动调用已有 `inspect`，生成 `inspection.json`；没有先验时仍可下载和看谱，但标为等待先验。不会编造参数，也不会自动执行 XP 拟合。`--no-calibrate` 只保存原系数，不生成拟合输入。

## DR4：先确认产品和对应源

```text
gaia-xp gaia-probe --release dr4 --output NEW_CHECK
```

该命令查询实时公开的 TAP schema，并区分“尚不可用”和“查询失败”。2026 年 11 月 19 日的实查未返回 DR4 schema，原响应保留在本地验证目录。当前尚不能实际下载、校准 DR4 XP；`--release dr4` 会记录未可用或适配未验证的原因，不偷偷改用 DR3 产品。

正式开放后还需核验 DR3→DR4 对应源、实际 XP 平均/历元产品及其协方差和校准工具。即使公开表已经可见，也不能把 DR3 编号直接当作 DR4 编号，或把 DR3 的校准矩阵用于 DR4。此版本提供检查入口，不宣称已完成 DR4 历元分析。

未来历元产品的下载与展示必须保留官方时间值、格式（如 JD/MJD 及其零点）、时标和时间定义（曝光起点、中点或覆盖范围）。每条历元光谱的图例直接标出时间，表格保留原精度；未知字段写明未提供。若另作日历日期转换，应保留原值并注明转换后的时标，不能直接把 TCB/TDB 写为 UTC。`reference_epoch` 是位置参考历元，不能代替光谱观测时间；DR3 平均 XP 则明确标为多年平均谱。

官方入口：[ESA Archive](https://gea.esac.esa.int/archive/)、[DataLink 与服务说明](https://www.cosmos.esa.int/web/gaia-users/archive)、[GaiaXPy](https://gaia-dpci.github.io/GaiaXPy-website/)。下载与校准成功只说明数据能够进入检查，不代表吸积模型已独立标定。
