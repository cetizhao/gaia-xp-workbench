# Gaia XP 传统吸积拟合工作台

本工具使用年轻恒星的光球模板、消光和氢吸积连续谱，拟合已经完成外部标定的 Gaia DR3 平均 BP/RP（XP）光谱。目标是让研究者在独立 Python 环境中检查输入、完成单源拟合，并复查数值结果与方法局限。当前支持 K/M 型至 M8、336–1020 nm 且步长为 2 nm 的光谱；需要完整协方差或其因子，以及来源明确的外部光谱型、消光和有效温度。

本地迁移版本 0.1.0 已在 Windows / Python 3.12 的全新环境中通过 wheel 安装和单源运行验证，详见[验证记录](validation/README.md)。macOS/Linux 提供安装步骤，尚未在这些系统实测。

当前方法采用 Fang+25 原生 XP 光球、16 个宽波段、1620 个作者氢 slab 和 24 个厚 slab 扩展。拟合输出是模型条件下的吸积约束，尚未完成普适物理标定。先阅读[输入格式](docs/input_format.md)和[方法与科学限制](docs/scientific_scope.md)。本版提供 `inspect`、`fit`、`review`、`summarize`；多巡天下载、统一单源 HTML 报告和 DR4 历元适配不在本版能力内。

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

迁移到另一台电脑时，安装相同软件版本，复制或重新准备同版本资产缓存，设置新路径并执行 `assets check`。无需复制原研究项目的全部数据或历史结果。资产及第三方代码的许可应分别处理，不能将仓库代码的许可自动扩展到它们。当前是本地迁移版本，尚未指定整个项目的开源许可证；公开发布前须确认自有代码授权与资产再分发条件。已有第三方授权文本在 `third_party/` 保留。

## 检查、拟合与复查

下列 `example/spectrum.npz` 和 `example/metadata.json` 是**用户自备文件的路径示例**，仓库没有将它们作为可再分发的实测样本提供。数据格式见[输入格式](docs/input_format.md)。路径可换成绝对路径。

```text
gaia-xp inspect --input example/spectrum.npz --metadata example/metadata.json
gaia-xp fit --input example/spectrum.npz --metadata example/metadata.json --output results/target_run1
gaia-xp review --run results/target_run1
gaia-xp summarize --run results/target_run1 --run results/target_run2 --output results/selected_summary
```

`fit` 与 `summarize` 要求输出目录尚不存在。`inspect` 用于确认波段覆盖、单位、误差和方法适用范围；`review` 读取已保存结果，不重拟合。只有明确要求重新计算时才再次运行 `fit`。处理多个对象时，一次运行一个数值进程；入口采用 Agg 绘图、两个积分工作线程与单线程 BLAS。

成功拟合保存输入副本、方法配置与文件哈希、后验、摘要、诊断、简短报告、谱拟合图和条件正分支 corner 图。首先检查 `status.json` 为 `complete`，再阅读 `review.json` / `report.md`。失败会留下原因和中间文件，不能把局部输出当作完整结果；重试使用新目录。

主要物理量分别是光学超额比 `r`、模型积分通量 `Facc` 和模型总通量比 `q`。提供有来源的距离后可换算 `Lacc`，再提供质量和半径后可换算 `Mdot`。本版将这些恒星参数视为固定值，区间不包含其误差。图形贴合和数值积分通过都不等于吸积量已独立校准。

## 给 agent 使用

可将仓库的 `skills/gaia-xp-fit/` 整个目录复制到所用 agent 支持的 skill 目录。该目录包含自足的使用说明和参考资料；agent 还须能运行已安装的 `gaia-xp`，并访问输入、缓存和输出目录。不同 agent 的 skill 安装位置由各自产品决定，复制 skill 不会自动安装 Python 包或模型资产。

示例请求：

> 使用 gaia-xp-fit 检查这组 NPZ/JSON；如果适用于当前方法，在指定的新目录完成一次拟合，展示谱图，并解释后验、数值检查和科学局限。

`.local/` 中可能存在本机验证缓存、单源输入及新结果，它们不属于 Git 仓库的分发内容。本地回归输入采用的参数仅用于检验迁移前后结果；它不构成公开标定样本。可复现科学比较还需要保持输入、软件版本、模型资产、先验和随机种子一致。
