# Gaia XP Accretion Fitter

[English](README.md) · **简体中文**

一颗年轻恒星的蓝端辐射中，有多少可以用吸积解释？程序将 Fang 光球模板与氢吸积连续谱叠加并施加消光，在 16 个宽波段内拟合 Gaia DR3 的 BP/RP（XP）平均光谱，适用于**外部光谱型为 K0–M8** 的年轻星。每颗星可生成一张总览图和一份英文 HTML 报告，还可以加入巡天测光和标有观测时间的档案光谱，与 XP 拟合比较。

**已经有 `report.html`？** 直接用浏览器打开，离线也能看。如果你有保存完整的拟合目录，可以用已有后验重画报告或补充其他观测。只有做新拟合才需要 Fang 模板。

## 在 Mac 上从对话开始

在能读取文件和运行终端命令的 agent 里打开你的研究目录，把下面这段话发给它。

> 请从 GitHub 把 `cetizhao/gaia-xp-workbench` 安装到这个研究目录。用 Python 3.12 建立 `.venv-gaia-xp` 环境，装上 Gaia XP 校准和 ESO 光谱读取依赖。用仓库自带的脚本为这个目录中所有受支持的客户端安装 skill。在这台 Mac 上检查程序版本并运行测试，告诉我芯片架构、测试结果，以及做新拟合还缺哪些模型文件。

装好后，在同一研究目录新开一次对话。各客户端共用一套 Python 环境。安装脚本覆盖 12 种客户端，已在 Codex、Claude Code 和 DeepSeek Harness 中实际确认能识别这个 skill。其他能使用终端的客户端也可以直接读取下载仓库里的 `skills/gaia-xp-fit/SKILL.md`。指南和 skill 使用说明默认英文，每篇都可切换到中文版。[客户端安装与兼容性](docs/agent-clients.zh-CN.md) · [Skill 使用说明](skills/gaia-xp-fit/SKILL.zh-CN.md)

<details>
<summary>查看终端安装命令和本机检查步骤</summary>

先进入**平时用 agent 打开的研究目录**。在已安装 Git 和 Python 3.12 的 macOS 或 Linux 上运行以下命令。

```sh
git clone https://github.com/cetizhao/gaia-xp-workbench.git
python3.12 -m venv .venv-gaia-xp
.venv-gaia-xp/bin/python -m pip install "./gaia-xp-workbench[gaia,spectroscopy]"
.venv-gaia-xp/bin/python ./gaia-xp-workbench/scripts/install_skill.py --project . --agent all
.venv-gaia-xp/bin/python -m pip check
.venv-gaia-xp/bin/gaia-xp --version
.venv-gaia-xp/bin/python -m unittest discover -s gaia-xp-workbench/tests
```

Windows 用户同样先用 `git clone` 下载仓库，再在同一研究目录的 PowerShell 中运行以下命令。

```powershell
py -3.12 -m venv .venv-gaia-xp
.\.venv-gaia-xp\Scripts\python.exe -m pip install "./gaia-xp-workbench[gaia,spectroscopy]"
.\.venv-gaia-xp\Scripts\python.exe .\gaia-xp-workbench\scripts\install_skill.py --project . --agent all
.\.venv-gaia-xp\Scripts\python.exe -m pip check
.\.venv-gaia-xp\Scripts\gaia-xp.exe --version
.\.venv-gaia-xp\Scripts\python.exe -m unittest discover -s gaia-xp-workbench/tests
```

只想为部分客户端安装时，把 `--agent all` 换成所需名称，例如 `--agent claude-code cursor`。`gaia` 安装 GaiaXPy，用于校准 XP 光谱。`spectroscopy` 安装 Astropy，用于读取 ESO 的 FITS 光谱。只拟合本地光谱或重画报告时，可直接安装 `./gaia-xp-workbench`，省去这两个依赖。Intel Mac 编译项目指定版本的 `extinction` 时可能需要安装苹果命令行开发工具。Apple 芯片有可直接安装的 Python 3.12 版本。[extinction 发布文件](https://pypi.org/project/extinction/0.4.8/#files)

</details>

## 用对话分析一颗星

- “下载并校准 Gaia DR3 源 `6719035052475592576` 的平均 XP 光谱。开始拟合前，还需要哪些恒星参数？”
- “用我在元数据中给出的光谱型、消光和有效温度拟合这条光谱。模型能否解释蓝端连续谱？得到的吸积通量有多大不确定性？”
- “我已经有 `runs/target` 的拟合结果。请查这颗星的测光和档案光谱，加入英文报告，注明每条光谱的匹配依据、观测时间、仪器、分辨率和通量单位。”

也可以按天区、星等或颜色选择 DR3 候选源。报告能逐历元展示已有的校准光谱，另列 DR3 平均谱供对照。对于官方 DR4 XP，0.7.0 版可以检查档案可用性。下载、校准和拟合 DR4 历元谱仍需适配并验证官方产品。[Gaia 选源与下载](docs/gaia_download.zh-CN.md) · [多历元光谱](docs/epochs.zh-CN.md)

## 做一次新拟合

**准备模型文件。** 1,620 个 FRAPPE 氢连续谱网格文件和两张光球校准表随 Python 程序安装。你只需另行提供有权使用的 Fang 光球模板 `Gaia_template_final_new_final.sav`。例如，将文件放入 `~/astro-data/fang`，然后从研究目录运行以下命令。

```sh
.venv-gaia-xp/bin/gaia-xp assets import --from-dir "$HOME/astro-data/fang"
.venv-gaia-xp/bin/gaia-xp assets check
```

文件齐全时会显示 `"status": "complete"` 和 `"checked_files": 1623`。检查结果会列出每组文件的实际位置。Mac 默认从安装包读取网格和校准表，导入的模板放在 `~/.cache/gaia-xp-workbench/assets/fang25-v1/fang/`。如果已有含 `fang/`、`slab_grid/` 和 `calibration/` 的完整模型目录，可将 `GAIA_XP_ASSETS` 或顶层参数 `--assets-dir` 指向该目录。[网格和校准表](src/gaia_accretion/resources/models/fang25-v1) · [文件校验清单](src/gaia_accretion/resources/assets.json) · [来源与分发许可](third_party/NOTICE.zh-CN.md)

**准备这颗星的输入。** 下载 XP 时无需先给恒星参数。拟合时，`spectrum.npz` 提供校准通量及其协方差或协方差因子。`metadata.json` 以字符串记录精确的 Gaia 源编号，并给出外部光谱型、V 波段消光（`A_V`，mag）、有效温度（`teff_k`，K）及其出处。先运行 `inspect`，确认 `ready_for_fit` 为真后，再为 `fit` 指定一个新的输出目录。[输入格式与示例](docs/input_format.zh-CN.md)

```sh
.venv-gaia-xp/bin/gaia-xp inspect --input spectrum.npz --metadata metadata.json
.venv-gaia-xp/bin/gaia-xp fit --input spectrum.npz --metadata metadata.json --output runs/target
```

**为什么是 K0–M8？** Fang 模板覆盖 B2–M8。K0 是当前拟合接受的最早外部光谱型。南冕座的主分析包括 41 颗 K/M 型星，另有 3 颗 A 型星仅作探索。更热的光球在蓝端更亮，还有本征巴耳末吸收，弱吸积超额更难分离。这些星的 DR3 光谱也可以下载并与其他观测比较。[方法适用范围](docs/scientific_scope.zh-CN.md)

## 怎样读吸积结果

从一个已完成的拟合生成报告时，选一个新的报告目录。

```sh
.venv-gaia-xp/bin/gaia-xp report --run runs/target --output reports/target
```

打开 `reports/target/report.html`，或分享同一目录里的总览图 `overview.png`。先看全谱、蓝端放大图和拟合波段的残差。角图（corner plot）显示吸积连续谱为正时的联合后验，应结合零超额模型的后验概率 `P0` 一起读。[报告说明](docs/report.zh-CN.md) · [后验解读](docs/inference.zh-CN.md)

- `r` 是施加消光后，700–900 nm 范围内吸积连续谱与光球各自的平均通量密度之比。
- `Facc` 是模型在 50–2477.47 nm 积分得到的本征吸积通量，单位为 W m⁻²。XP 覆盖范围以外的贡献依赖氢连续谱模型。
- `q = Facc/Fstar` 比较吸积和光球的总辐射通量。为得到 `Fstar`，程序把 751 nm 附近去消光的光球通量密度除以随温度变化的校正系数。拟合会尝试邻近光谱型，总通量校正始终采用你提供的 `teff_k`。第二张表记录光谱型与有效温度的关系。[物理量与方法局限](docs/scientific_scope.zh-CN.md)

要加入同一颗星的其他资料，可在报告命令中添加 `--photometry`、`--spectra` 或 `--epochs`，各自指向已准备好的目录。结合匹配记录、单位和观测时间解读差异。消光和狭缝损失也可能造成不同观测之间的通量变化。[巡天测光](docs/photometry.zh-CN.md) · [档案光谱](docs/spectroscopy.zh-CN.md) · [外部观测能检验什么](docs/external_evidence.zh-CN.md)

0.7.0 版在 Windows 上通过了 59 项测试，并用已有单源拟合结果重画了英文报告。macOS 的实机测试结果尚待补充。项目自有代码尚未指定开源许可证。[验证记录](validation/README.zh-CN.md) · [第三方材料许可](third_party/NOTICE.zh-CN.md)
