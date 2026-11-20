# Gaia XP Workbench

Python 3.12 tools and an agent skill for fitting Gaia XP spectra of young stars. The workbench generates offline English reports with epoch spectra, archival spectroscopy, photometry and accretion posteriors. Install with `python -m pip install .` after cloning. See [installation](#安装) and [the agent skill](skills/gaia-xp-fit/SKILL.md).

本工具使用年轻恒星的光球模板、消光和氢吸积连续谱，拟合已经完成外部标定的 Gaia DR3 平均 BP/RP（XP）光谱。目标是让研究者在独立 Python 环境中检查输入、完成单源拟合，并复查数值结果与方法局限。当前支持 K/M 型至 M8、336–1020 nm 且步长为 2 nm 的光谱；需要完整协方差或其因子，以及来源明确的外部光谱型、消光和有效温度。

本地迁移版本 0.1.0 已在 Windows / Python 3.12 的全新环境中通过 wheel 安装和单源运行验证，详见[验证记录](validation/README.md)。macOS/Linux 提供安装步骤，尚未在这些系统实测。

当前方法采用 Fang+25 原生 XP 光球、16 个宽波段、1620 个作者氢 slab 和 24 个厚 slab 扩展。拟合输出是模型条件下的吸积约束，尚未完成普适物理标定。先阅读[输入格式](docs/input_format.md)和[方法与科学限制](docs/scientific_scope.md)。0.4.0 增加 Gaia DR3 选源、XP 下载与校准，以及 ESO 档案光谱查询、下载和联合展示。DR4 提供在线可用性检查，正式下载和校准尚待验证。

## 安装

需要 Python **3.12**。核心依赖仅为 NumPy、SciPy、Matplotlib、extinction 和 threadpoolctl，版本由 `pyproject.toml` 约束。安装位置、数据缓存和结果目录可以分别选择；安装后无需在仓库目录执行命令。

Windows PowerShell，在仓库根目录执行：

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
$env:PYTHONUTF8 = '1'
python -m pip install .
gaia-xp --help
```

macOS / Linux，在仓库根目录执行：

```bash
python3.12 -m venv .venv
source .venv/bin/activate
python -m pip install .
gaia-xp --help
```

也可以安装已构建的 wheel：`python -m pip install /path/to/gaia_xp_workbench-VERSION-py3-none-any.whl`，替换为实际文件名。开发时可用 `python -m pip install -e .`。无需安装 Torch、学习模型权重、MCP 服务或特定 agent 才能使用命令行。

下载并校准 Gaia XP 时安装 `python -m pip install ".[gaia]"`；解析档案 FITS 光谱时安装 `python -m pip install ".[spectroscopy]"`，两者可合并为 `".[gaia,spectroscopy]"`。这两个附加依赖不用于重画已有报告。

## 准备模型资产

程序与观测数据分开安装。Fang 光球、作者 slab 网格和两张光球校准表由随包资产清单记录具体文件、版本、来源和 SHA256，共 1623 个文件、134,881,831 字节。清单不是资产本身；安装包默认不包含这些科学数据。

```text
gaia-xp assets list
gaia-xp --assets-dir CACHE assets import --from-dir SOURCE
gaia-xp --assets-dir CACHE assets check
```

将 `SOURCE` 替换为已有资产的目录，其中保留清单规定的相对路径；它可以是原研究项目根目录，也可以是已经导出的资产缓存。本机已有研究项目可作为导入来源；导入只复制并核对所需文件，不写回来源。将 `CACHE` 替换为独立缓存目录。资产导入和检查不执行拟合，也不自动联网下载。Fang 模板的公开获取地址和再分发许可尚未确认；缺少该资产时应先取得合法可用副本，不能换用未经记录的模板继续拟合。

可以在当前终端设置缓存路径，省去每次传入 `--assets-dir`：

```powershell
# Windows PowerShell：示例位置，请按实际缓存目录修改。
$env:GAIA_XP_ASSETS = 'D:\astro-data\gaia-xp-assets'
```

```bash
# macOS / Linux：示例位置，请按实际缓存目录修改。
export GAIA_XP_ASSETS=/path/to/gaia-xp-assets
```

迁移到另一台电脑时，安装相同软件版本，复制或重新准备同版本资产缓存，设置新路径并执行 `assets check`。无需复制原研究项目的全部数据或历史结果。资产及第三方代码的许可应分别处理，不能将仓库代码的许可自动扩展到它们。项目自有代码尚未指定开源许可证。已有第三方授权文本在 `third_party/` 保留。

## 检查、拟合与复查

下列 `example/spectrum.npz` 和 `example/metadata.json` 是**用户自备文件的路径示例**，仓库没有将它们作为可再分发的实测样本提供。数据格式见[输入格式](docs/input_format.md)。路径可换成绝对路径。

```text
gaia-xp inspect --input example/spectrum.npz --metadata example/metadata.json
gaia-xp fit --input example/spectrum.npz --metadata example/metadata.json --output results/target_run1
gaia-xp review --run results/target_run1
gaia-xp report --run results/target_run1 --output reports/target_run1
gaia-xp summarize --run results/target_run1 --run results/target_run2 --output results/selected_summary
```

各下载、拟合、报告与汇总命令使用尚不存在的输出目录。`inspect` 用于确认波段覆盖、单位、误差和方法适用范围；`review` 读取已保存结果，不重拟合。只有明确要求重新计算时才再次运行 `fit`。处理多个对象时，一次运行一个数值进程；入口采用 Agg 绘图、两个积分工作线程与单线程 BLAS。

成功拟合保存输入副本、方法配置与文件哈希、后验、摘要、诊断、简短报告、谱拟合图和条件正分支 corner 图。首先检查 `status.json` 为 `complete`，再阅读 `review.json` / `report.md`。失败会留下原因和中间文件，不能把局部输出当作完整结果；重试使用新目录。

主要物理量分别是光学超额比 `r`、模型积分通量 `Facc` 和模型总通量比 `q`。提供有来源的距离后可换算 `Lacc`，再提供质量和半径后可换算 `Mdot`。本版将这些恒星参数视为固定值，区间不包含其误差。图形贴合和数值积分通过都不等于吸积量已独立校准。

## 从已有结果生成单源报告

0.5.0 将可交互的多历元光谱窗口放在报告首位：按观测时间选择、叠加和放大已保存光谱，并将 DR3 平均谱单独作为参考。已有档案谱可直接进入窗口；`--epochs EPOCHS_DIRECTORY` 可接入经核验的校准历元资料。没有 DR4 历元时明确显示待接入，不合成观测。资料格式及操作见[多历元窗口](docs/epochs.md)。

`report` 直接读取完整运行目录中的观测、模型预测、后验及诊断，不调用拟合器，也不读取模型资产缓存。报告目录保存 `overview.png`、`spectrum.png`、`posterior.png`、`report.html` 和 `report_manifest.json`。总览图集中展示主要结果、全谱拟合、蓝端放大、波段残差与条件正分支 posterior；HTML 将图片内嵌，可单独复制后离线打开。

报告保留原结果的分位数和上限，不因重新绘图改写科学结果。缺少距离、质量或半径时，未保存的 `Lacc` / `Mdot` 显示为未提供。已有校验链与本次读取哈希分别记录，尤其不能把旧运行没有预存哈希的光谱/预测文件称作已验证历史完整性。具体文件要求和图的解释见[单源报告说明](docs/report.md)。

光谱型后验按原节点分箱，避免比积分步长更细的绘图分箱产生空列；没有插值或重算后验。加密网格与改用 MCMC／嵌套采样的区别见[积分方法说明](docs/inference.md)。

## 选择 Gaia 源与下载 XP

```text
gaia-xp gaia-select --ra 287.44 --dec -37.07 --radius-arcmin 2 --g-max 15 --limit 20 --output selection
gaia-xp gaia-fetch --source-id 6719035052475592576 --metadata PRIORS.json --output data/target_xp
gaia-xp gaia-probe --release dr4 --output dr4_check
```

天区和亮度条件选出候选；也可直接提供精确源编号。DR3 下载保留连续系数与完整相关误差，校准后自动接入输入检查。缺少有来源的恒星参数时明确保留缺项，不编造先验或自动拟合。DR4 必须先确认发布与跨版本身份，不能沿用同值 DR3 编号。详见[Gaia 下载说明](docs/gaia_download.md)。

## 加入档案光谱

```text
gaia-xp spectra-search --source-id 6719035052475592576 --output data/spectra_search
gaia-xp spectra-fetch --discovery data/spectra_search --output data/target_spectra
gaia-xp report --run results/target_run1 --spectra data/target_spectra --photometry data/target_photometry --output reports/target_joint
```

查询清单与实际下载分开保存。报告注明仪器、时间、缝宽、名义分辨率、单位和匹配依据；宽缝连续谱与窄缝谱线分别解释。非同期光谱不能直接给出吸积变化或校准吸积率。支持的产品与选择规则见[档案光谱说明](docs/spectroscopy.md)。

候选清单确定后，应分别核查外部光谱质量、吸积连续谱覆盖和观测时间；仪器波长重合不代表候选源都有档案观测。ESPRESSO、X-shooter 与 Gaia 的互补用途见[外部观测证据](docs/external_evidence.md)。

## 加入巡天测光

先为一个明确的 Gaia DR3 源查询测光，再将保存的测光资料加入报告：

```text
gaia-xp photometry --source-id 6719035052475592576 --output data/target_photometry
gaia-xp report --run results/target_run1 --photometry data/target_photometry --output reports/target_with_photometry
```

查询从 VizieR 获取位置和测光，记录候选源、匹配距离、单位、质量旗标及原表。报告只读本地结果，可离线生成，不改变 XP 后验。不同巡天通常并非同期；红外辐射也可能来自盘，测光比较不能单独验证吸积率。支持的目录及匹配规则见[测光说明](docs/photometry.md)。

## 给 agent 使用

可将仓库的 `skills/gaia-xp-fit/` 整个目录复制到所用 agent 支持的 skill 目录。该目录包含自足的使用说明和参考资料；agent 还须能运行已安装的 `gaia-xp`，并访问输入、缓存和输出目录。不同 agent 的 skill 安装位置由各自产品决定，复制 skill 不会自动安装 Python 包或模型资产。

示例请求：

> 使用 gaia-xp-fit 检查这组 NPZ/JSON；如果适用于当前方法，在指定的新目录完成一次拟合，展示谱图，并解释后验、数值检查和科学局限。

`.local/` 中可能存在本机验证缓存、单源输入及新结果，它们不属于 Git 仓库的分发内容。本地回归输入采用的参数仅用于检验迁移前后结果；它不构成公开标定样本。可复现科学比较还需要保持输入、软件版本、模型资产、先验和随机种子一致。
