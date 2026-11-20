# Gaia XP Accretion Fitter

[English](README.md) · **简体中文**

用 Gaia DR3 的 BP/RP（XP）平均光谱研究年轻恒星的吸积。程序把 Fang 年轻星光球模板和氢吸积连续谱一起拟合到观测，估计光学超额及其不确定性。每颗星可生成一张总览图和一份英文离线 HTML，查看蓝端谱形、残差、参数后验，并与同一颗星的档案光谱和巡天测光比较。

当前拟合适用于**外部光谱型在 K0–M8 之间的年轻恒星**。手中已有 `report.html` 时，直接用浏览器打开即可。报告可按时间展示已有的校准历元谱。DR4 官方 XP 的下载、校准和历元拟合仍待适配。

## 在 Mac 上用自然语言开始

如果使用能运行本地命令的 Codex，可以把下面这段话发给它。

> 请从 GitHub 仓库 `cetizhao/gaia-xp-workbench` 在这台 Mac 上安装 Gaia XP Accretion Fitter。用 Python 3.12 创建可在以后对话中继续使用的虚拟环境，装上 Gaia XP 校准和 ESO 光谱读取依赖，并把仓库里的 `skills/gaia-xp-fit` 安装为本项目的 Codex skill。请记下 `gaia-xp` 的绝对路径，验证在新终端里也能运行。如果还缺模型文件，请告诉我需要提供哪个目录。

装好后可以直接描述研究任务。

- “下载 Gaia DR3 源 `6719035052475592576` 的平均 XP 并校准，告诉我做吸积拟合还缺哪些恒星参数。”
- “用我提供的光谱型、消光和有效温度拟合这颗星，生成英文报告，解释蓝端是否支持光学超额。”
- “我已有这颗星的拟合目录。请查同源的测光和档案光谱，把合适的观测加入报告，注明观测时间和匹配依据。保留原拟合。”

首次安装需要同时准备 Python 程序和 skill。可将整个 `skills/gaia-xp-fit/` 复制到希望开展分析的项目的 `.agents/skills/`，让 Codex 在该项目中找到它。若以后从其他目录调用程序，可直接使用虚拟环境中 `gaia-xp` 的绝对路径。[Skill 使用说明](skills/gaia-xp-fit/SKILL.md)

## 手动安装

在有 Git 和 Python 3.12 的 Mac 上运行以下命令。Linux 也可使用同一组命令。

```sh
git clone https://github.com/cetizhao/gaia-xp-workbench.git
cd gaia-xp-workbench
python3.12 -m venv .venv
.venv/bin/python -m pip install ".[gaia,spectroscopy]"
.venv/bin/python -m pip check
.venv/bin/gaia-xp --help
```

这里安装了 GaiaXPy 和 Astropy，以便校准 Gaia XP 系数和读取 ESO 的 FITS 光谱。仅用本地输入拟合或为已有结果生成报告时，安装 `.` 即可。下文的 macOS 示例从仓库根目录运行，打开新终端后同样适用。

在 Windows 上，改用仓库根目录下的 PowerShell。

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install ".[gaia,spectroscopy]"
.\.venv\Scripts\python.exe -m pip check
.\.venv\Scripts\gaia-xp.exe --help
```

## 新拟合需要哪些模型文件？

换电脑时，把你有权使用的模型目录整体复制过去。下载 XP、检查输入或用已有结果制作报告时，可以跳过这一步。模型目录应直接包含以下三个子目录。

```text
gaia-xp-assets/
├── fang/
│   └── Gaia_template_final_new_final.sav
├── slab_grid/
│   └── *.out                              （1,620 个氢连续谱模型）
└── calibration/
    ├── BolCorr_hh14_myCorr_wInteroplationOverVO.txt
    └── SpT_Teff_relation_hh14_short_codes.dat
```

例如，把目录复制到 Mac 的 `~/astro-data/gaia-xp-assets` 后，可逐次使用顶层选项 `--assets-dir` 指定位置。以下命令会按清单逐一核验文件。完整时显示 `"status": "complete"` 和 `"checked_files": 1623`。

```sh
.venv/bin/gaia-xp --assets-dir "$HOME/astro-data/gaia-xp-assets" assets check
```

如希望不同对话都能自动找到资产，可在没有设置 `GAIA_XP_ASSETS` 的终端中运行以下命令，将校验过的副本放入默认缓存。

```sh
.venv/bin/gaia-xp assets import --from-dir "$HOME/astro-data/gaia-xp-assets"
```

macOS 和 Linux 默认读取 `~/.cache/gaia-xp-workbench/assets/fang25-v1`，若设置了 `XDG_CACHE_HOME` 则用其代替 `~/.cache`。Windows 默认读取 `%LOCALAPPDATA%\gaia-xp-workbench\assets\fang25-v1`。也可让 `GAIA_XP_ASSETS` 直接指向包含上述三个子目录的位置。仓库提供文件名、大小和校验值。Fang 模板的公开下载地址与再分发授权仍待确认。氢连续谱网格和两张表来自 FRAPPE。[资产清单](src/gaia_accretion/resources/assets.json) · [FRAPPE 模型文件](https://github.com/RikClaes/FRAPPE/tree/f2bebaa6a477c6f9a1c830ab4aad52947a3eecc2/src/frappe/models_grid)

**光球校准表用在哪里？** Fang 模板给出 XP 波段内的光球谱形。要计算吸积辐射与整个恒星光球辐射的比值 `q = Facc/Fstar`，程序先按输入的有效温度 `teff_k` 查询 751 nm 附近光球通量密度与光球总通量之比，再将去消光的模型光球通量密度除以这个系数，得到 `Fstar`。系数表的单位为 Å⁻¹，计算时换成 nm⁻¹。第二张表记录光谱型与有效温度的对应关系。当前版本在拟合光谱型时，用于光球总通量换算的温度始终取自输入记录。[方法与局限](docs/scientific_scope.md)

## 拟合一颗星，或重画已有结果

**为什么是 K0–M8？** Fang 模板覆盖 B2–M8，M8 是模板的晚型端点，K0 则是当前程序接受的光谱型先验中心的早型界限。南冕座样本的主分析包括 41 颗 K/M 型星，另 3 颗 A 型星仅作探索，因为较亮的蓝端光球和巴耳末吸收让吸积超额更难分离。更早型恒星的 DR3 XP 仍可下载、校准并与档案光谱比较。

为新拟合准备同一源的 `spectrum.npz` 和 `metadata.json`。前者保存已标定的 DR3 平均 XP 及完整协方差或其因子，后者记录 Gaia 源编号的精确十进制字符串、标定过程，以及外部光谱型、V 波段消光（mag）、有效温度（K）和出处。也可以先下载并校准 XP，待先验齐备后再拟合。[单谱输入格式](docs/input_format.md) · [选源与下载](docs/gaia_download.md)

```sh
.venv/bin/gaia-xp inspect --input spectrum.npz --metadata metadata.json
.venv/bin/gaia-xp fit --input spectrum.npz --metadata metadata.json --output runs/target
```

先查看 `inspect` 的 `ready_for_fit`、`blockers` 和 `notes`，确认光谱和先验适用，再执行 `fit`。示例采用默认资产缓存，每次拟合和制图均使用新的输出目录。拟合摘要给出 700–900 nm 吸积连续谱与光球的通量密度比 `r`、去消光模型在 50–2477.47 nm 积分所得的吸积通量 `Facc`（W m⁻²），以及 `q`。这些量的后验区间取决于光球模板、消光和蓝端光谱的约束。[后验解读](docs/inference.md)

若已拿到一颗星的完整拟合目录，从这里开始即可。

```sh
.venv/bin/gaia-xp report --run runs/target --output reports/target
```

打开 `reports/target/report.html` 查看全谱、蓝端放大、残差和后验，单页总览图是 `overview.png`。报告只读取已有拟合结果。要加入同源资料，可给报告命令添加 `--photometry`、`--spectra` 或 `--epochs`，各自指向已准备好的目录。每条历元谱保留观测时间，DR3 多年平均谱单列为参照。比较非同期光谱时，通量差异也可能来自消光、光球变化或狭缝损失。[报告说明](docs/report.md) · [巡天测光](docs/photometry.md) · [档案光谱](docs/spectroscopy.md) · [多历元光谱](docs/epochs.md) · [外部观测能检验什么](docs/external_evidence.md)

仓库保留了安装、单源拟合和档案对照的验证记录。第三方材料各有来源和许可，项目自有代码尚未指定开源许可证。[验证记录](validation/README.md) · [第三方材料](third_party/NOTICE.md)
