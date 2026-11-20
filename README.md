# Gaia XP Workbench

Fit the optical accretion continuum of young stars in Gaia XP spectra and explore each source in an offline English report.

这套工作台用 Fang 年轻星光球模板和氢吸积连续谱拟合 Gaia DR3 平均光谱。你可以从拟合中查看光学超额有多强、消光与光谱型有多大退化，也可以把同一颗星的不同历元、档案光谱和巡天测光放在一份英文 HTML 报告里比较。

- **手上已有 `report.html`**：用浏览器直接打开，离线也能切换光谱和放大波段。
- **已有完整拟合结果，想重画图或加入外部观测**：安装工作台后直接[生成报告](#生成报告)。这一步只读取保存的结果。
- **要给一颗星做新拟合**：先安装工作台，然后[准备模型资产](#准备模型资产)。当前拟合适用于 K0–M8 的 Gaia DR3 平均 XP。DR4 历元光谱的展示窗口已就绪，正式产品的下载与校准仍待验证。

## 安装

先克隆仓库，再进入项目目录。

```sh
git clone https://github.com/cetizhao/gaia-xp-workbench.git
cd gaia-xp-workbench
```

使用 **Python 3.12**。在 Windows PowerShell 中运行：

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install .
gaia-xp --help
```

在 macOS 或 Linux 终端中运行：

```sh
python3.12 -m venv .venv
source .venv/bin/activate
python -m pip install .
gaia-xp --help
```

基础安装可以检查输入、拟合和生成报告。若还要下载并校准 Gaia XP，或读取下载的 ESO FITS 光谱，在上面的安装命令中分别用 `".[gaia]"` 或 `".[spectroscopy]"` 替换 `.`。两者都需要时运行 `python -m pip install ".[gaia,spectroscopy]"`。Windows 上已有[安装与单源运行验证](validation/README.md)。

## 准备模型资产

**换电脑时，最省事的是把已有资产目录整个复制过去。** 选一个长期保存数据的位置，例如 Windows 上的 `D:\astro-data\gaia-xp-assets`。打开这个目录，应当直接看到下面三个子目录：

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

让程序指向这三个目录的**上一层**。例如，在 Windows PowerShell 中：

```powershell
$env:GAIA_XP_ASSETS = 'D:\astro-data\gaia-xp-assets'
gaia-xp assets check
```

macOS / Linux 可设置 `export GAIA_XP_ASSETS="$HOME/astro-data/gaia-xp-assets"`，然后运行同一条检查命令。这些设置对当前终端有效。看到 `"status": "complete"` 和 `"checked_files": 1623` 就说明文件齐全且校验通过。只有一次运行需要指定位置时，可用 `gaia-xp --assets-dir "D:\astro-data\gaia-xp-assets" assets check`。

**也可以使用默认目录。** 先保持 `GAIA_XP_ASSETS` 未设置，将下面的路径换成已有资产备份的根目录或原 GaiaAccretion 项目的根目录，然后运行：

```sh
gaia-xp assets import --from-dir "/path/to/your/asset-backup"
```

程序会从已有副本中逐项校验文件并复制到默认位置。Windows 的默认位置是 `%LOCALAPPDATA%\gaia-xp-workbench\assets\fang25-v1`。macOS / Linux 默认是 `~/.cache/gaia-xp-workbench/assets/fang25-v1`，设置过 `XDG_CACHE_HOME` 时使用它代替 `~/.cache`。

GitHub 仓库提供[文件清单及校验值](src/gaia_accretion/resources/assets.json)。氢连续谱网格和两张表的上游文件位于 [FRAPPE 模型目录](https://github.com/RikClaes/FRAPPE/tree/f2bebaa6a477c6f9a1c830ab4aad52947a3eecc2/src/frappe/models_grid)。Fang 模板请使用有权使用的副本，其公开下载地址与再分发授权仍待确认。

### 两张光球校准表做什么？

Fang 模板给出光球在 XP 波段内的谱形。要比较吸积辐射与**整个光球**的辐射，还需要估计光球在所有波长上的积分通量 `Fstar`。工作台为此读取 FRAPPE 提供的两张表：

| 文件 | 记录的量 | 在当前拟合中的作用 |
|---|---|---|
| `BolCorr_hh14_myCorr_wInteroplationOverVO.txt` | 不同有效温度下，751 nm 附近光球通量密度与光球总通量之比，单位 Å⁻¹ | 程序按输入温度插值，把系数换成 nm⁻¹，再用去消光的模型光球在 751 nm 附近的通量密度除以该系数，得到 `Fstar`，用于计算 `q = Facc/Fstar`。 |
| `SpT_Teff_relation_hh14_short_codes.dat` | 光谱型对应的有效温度（K） | 例如，表中 K6 对应 4115 K。当前 Fang 入口会读取这张参照表，但用于总通量换算的是你在元数据中给出的 `teff_k`，拟合中改变光谱型不会改写这个温度。 |

这里的换算作用于**恒星光球模型**。Gaia XP 的仪器通量标定在准备观测光谱时完成。低分辨率 XP 对 751 nm 附近连续谱的估计会影响 `Fstar` 和 `q`。[方法与局限](docs/scientific_scope.md)

## 拟合一颗星

准备同一源的 `spectrum.npz` 和 `metadata.json`。前者保存已标定的 XP 光谱及协方差或其因子，后者记录精确的源编号、外部光谱型、消光、有效温度和出处。可按[输入格式](docs/input_format.md)自备这两个文件，也可以从 [Gaia DR3 下载并校准 XP](docs/gaia_download.md)。

```sh
gaia-xp inspect --input spectrum.npz --metadata metadata.json
gaia-xp fit --input spectrum.npz --metadata metadata.json --output runs/target
```

先看 `inspect` 的检查结果，确认波段覆盖、误差和恒星参数适合拟合，再执行第二条命令。为每次拟合和报告选择新的输出目录。拟合完成后，`runs/target/report.md` 给出光学超额 `r`、模型吸积通量 `Facc`、通量比 `q` 及后验区间。[后验解读](docs/inference.md)

## 生成报告

把下面的 `runs/target` 换成完整的拟合结果目录：

```sh
gaia-xp report --run runs/target --output reports/target
```

打开 `reports/target/report.html` 即可看图。报告内嵌光谱、拟合残差和后验图，可以单独复制到另一台电脑。多历元窗口会标出每条观测的时间，Gaia DR3 平均谱单列为参照。[报告说明](docs/report.md)

**要一起看其他观测**，可以添加 `--spectra`、`--photometry` 或 `--epochs`，分别指向已经准备好的同源资料目录。[档案光谱](docs/spectroscopy.md) · [巡天测光](docs/photometry.md) · [多历元资料格式](docs/epochs.md) · [哪些外部观测适合检验吸积](docs/external_evidence.md)

## 在另一台电脑上交给 agent 使用

安装工作台，并把 [`skills/gaia-xp-fit/`](skills/gaia-xp-fit/SKILL.md) 整个目录复制到 agent 的 skills 目录。先在该环境确认 `gaia-xp --help` 可运行。如果要做新拟合，再配置同一套模型资产。然后就可以说：

> 用 gaia-xp-fit 读取 runs/target 的已有结果，生成英文 HTML 报告，并解释蓝端拟合和吸积通量的后验区间。

第三方材料的来源与许可见[归属说明](third_party/NOTICE.md)。项目自有代码尚未指定开源许可证。
