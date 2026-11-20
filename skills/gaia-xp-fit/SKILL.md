---
name: gaia-xp-fit
description: Download and calibrate Gaia DR3 mean XP spectra, fit young-star accretion continua, compare survey photometry and archival spectra, or make an English report from a saved fit. 用于 Gaia XP 选源、吸积拟合、档案光谱对照和单源报告。
---

# Gaia XP 拟合与解读

Use the local `gaia-xp` executable for the numerical work. Answer in the user's language and generate the scientific report in English. For a request about an existing result, start with `review` or `report` and use the saved posterior. 区分数值积分稳定、模型对该谱的适用性，以及吸积量是否完成独立物理标定。

## Find the fitter in a new session

Use the project's recorded executable or `gaia-xp` on PATH. A project-local installation can also be called directly at `.venv-gaia-xp/bin/gaia-xp` on macOS/Linux or `.venv-gaia-xp/Scripts/gaia-xp.exe` on Windows, relative to the research project root. For an installation in the fitter checkout, use its `.venv` instead. Verify the executable with `--version` and use its full path in subsequent commands. Resolve the references below relative to this SKILL.md.

If the user requests setup and only the skill is installed, create a Python 3.12 virtual environment in the research project and use **that environment's Python** to install the fitter from the checkout. For XP calibration and ESO FITS use `python -m pip install ".[gaia,spectroscopy]"` from the checkout. The code and installation guide are in the [public repository](https://github.com/cetizhao/gaia-xp-workbench). When the client runs commands in a container or on a remote host, set up Python, inputs and any needed model files in that execution environment.

## 选择操作

- 看已有结果或解释可靠性：`gaia-xp review --run RUN`，不重拟合。
- 为已有结果制作一源一图或 HTML：`gaia-xp report --run RUN --output NEW_DIRECTORY`，只读保存的观测、模型预测、后验和诊断。
- 查看同源多历元光谱：报告首位窗口可按时间选择、叠加和放大已有谱；读[多历元窗口](references/epochs.md)，可用 `report --epochs EPOCHS_DIRECTORY` 加入经核验的校准资料，不自动拟合。
- 查询指定源的巡天测光：`gaia-xp photometry --source-id GAIA_DR3_ID --output NEW_DIRECTORY`；再用 `gaia-xp report --run RUN --photometry PHOTOMETRY_DIRECTORY --output NEW_REPORT_DIRECTORY` 联合展示。
- 按研究条件取得 Gaia XP：先读[选源与下载](references/gaia_download.md)，用 `gaia-select` 保存候选，再按明确选定的源逐个 `gaia-fetch`；下载后自动检查输入，不自动重拟合已有运行。
- 取得高质量档案光谱：读[档案光谱](references/spectroscopy.md)，依次 `spectra-search`、`spectra-fetch`，再用 `report --run RUN --spectra SPECTRA_DIRECTORY --output NEW_REPORT_DIRECTORY` 联合展示；可同时带 `--photometry`。
- 收到新光谱：`gaia-xp inspect --input SPECTRUM.npz --metadata METADATA.json`。
- 明确要求拟合：检查通过后使用 `gaia-xp fit --input SPECTRUM.npz --metadata METADATA.json --output NEW_DIRECTORY`。
- 整理选定结果：`gaia-xp summarize --run RUN_A --run RUN_B --output NEW_DIRECTORY`；不自动扩样、合并后验或做群体相关性分析。

命令中的路径优先用绝对路径。以天区或亮度选出的只是候选，不等于成员或年轻恒星；用户给名称时先核对发布版本、源编号与分量身份。不要自动扩大样本。首次处理输入时阅读[单谱格式](references/input_format.md)；解释科学量与后验时阅读[方法和限制](references/scientific_scope.md)。这些说明随本 skill 分发，不依赖原研究项目。

## 环境与资产

需要 Python 3.12、工作台 0.6.0 或后续兼容版本及目录访问权限；无需 MCP。先确认 `gaia-xp --help` 可用。XP 校准另需安装包的 `gaia` 附加依赖，档案 FITS 处理需 `spectroscopy` 附加依赖。查询需联网，报告只读本地资料。新拟合另需模型资产缓存；下载、`review` 和 `report` 无需缓存。资产位置由 `GAIA_XP_ASSETS` 或顶层 `--assets-dir DIR` 指定。已有合法来源可用 `gaia-xp --assets-dir CACHE assets import --from-dir SOURCE` 复制并校验，不伪造资产、不改校验值。Fang 模板公开来源与再分发许可未确认，不能宣称安装后必然自动取得全部模板。

Windows 终端宜设置 `$env:PYTHONUTF8='1'`。数值入口采用 Agg 绘图、两个积分线程与单线程 BLAS；一次只运行一个重计算进程。新拟合、测光下载、报告与汇总使用不存在的新目录。失败时读错误和已有状态记录，不把局部输出当作成功，也不为通过检查无限增加网格。

## 输入和解读规则

新拟合仅支持已外部标定的 Gaia DR3 平均 XP、K/M 至 M8、336–1020 nm 且步长 2 nm。必须有完整协方差或其因子、明确单位及光谱型/Av/Teff 来源。保留负通量与掩码，源编号使用精确十进制字符串。缺信息时明确指出，不用逐点独立误差或猜测先验静默代替。

成功运行先确认 `status.json` 为 complete，再读 `review.json`，打开 `spectrum_fit.png` 和 `corner_positive.png`。按用户所需篇幅说明数据、方法、主要约束、残差、退化和仍缺的证据。含零分支分位数、上限与 P0 一起解释；corner 仅表示条件正分支。

制作报告时保留原运行，只写新目录。交付 `overview.png` 与可离线打开的 `report.html`，并保留 `report_manifest.json` 的来源记录；HTML 图片已内嵌，不需要联网。核对总览的主要量、全谱、蓝端、残差和 posterior 均可读。报告中的数值来自已保存结果，不能因画图重估分位数或填补未保存的 Lacc/Mdot。旧运行没有为光谱或预测文件预存哈希时，本次记录的哈希只说明读取了哪个版本，不证明文件自拟合后从未改变。若必需结果缺失，报告具体缺项，不自动重跑拟合补齐。

测光查询限用户选定的源。保留原表、单位、星等制、质量旗标、候选源和匹配距离；检查自行改正与观测历元，多个候选时不擅自选最近者。区分未检出、质量不足和服务查询失败。对测光与 XP 的比较，应说明非同期、滤光片宽度及盘红外辐射的影响；本版未做滤光片积分或吸积交叉标定。不能把上限当检出，也不能用测光替换 XP 后验。

所有生成的 HTML、Markdown 报告、样本汇总、图表与交互控件使用英文。用户自定义的来源与观测说明优先提供英文，原始记录保留原文。报告面向天文学研究者：主要结果与比较图放前面，技术细节和完整数据表按需展开。用简短完整的句子说明图中看到了什么，不堆砌程序术语或重复限制。

多历元光谱是报告首要窗口。保留每条谱的时间与原采样，DR3 平均谱不计作单历元；同一观测组的多臂、多缝宽产品不计作多个独立历元。仅有档案记录的产品不能画成已下载谱。讨论候选星外部证据时，分别统计可靠光谱、吸积连续谱覆盖和近同期观测；见[外部观测证据](references/external_evidence.md)。

档案光谱按仪器、观测时间和分辨率分别保留，核对绝对或相对通量、缝宽、空气/真空波长及参考系。优先用宽缝绝对通量谱检查连续谱，窄缝高分辨率谱检查谱线；不将不同日期或不同分量直接拼接。为展示而取波段平均不等于模拟 Gaia 响应。非同期差异不能自动解释为吸积变化。

每条比较光谱的图例直接注明仪器／臂、宽／窄缝及观测日期和时分秒、时标；完整精度和曝光起点／中点／范围的定义留在表格。缺失时间信息写明未提供。DR3 明确标为多年平均谱；未来 DR4 的每条历元谱须标官方时间值、格式和时标，不用位置参考历元替代，不将 TCB/TDB 未经转换标成 UTC。详细时间要求见[选源与下载](references/gaia_download.md)。

后验图的光谱型分箱与保存节点对齐，不为消掉空列抖动样本或插值概率。若用户要求加密积分或更换采样器，先说明这需要重新计算，并保持本次计算范围；方法解释见[网格与采样](references/inference.md)。

DR4 先运行 `gaia-probe --release dr4`，区分服务失败与未公开。正式产品、DR3→DR4 对应关系和校准尚未核验时，明确列出缺项，不将 DR3 编号或校准矩阵直接套用到 DR4。

r 是 700–900 nm 光学超额比，Facc 是模型 50–2477.47 nm 的积分通量，q 是模型 Facc/Fstar，三者不可混称。Lacc 需要距离，Mdot 还需要质量、半径和截断半径假设；此版可选换算采用固定恒星参数，未传播它们的误差。新运行没有自动执行先验敏感性试验。

数值通过、较小 P0、较大 Bayes 因子或漂亮谱图都不能升级为普适已校准测量。外部混叠信息未知时照实报告。DR3 平均谱拟合不能称作时间变化；DR4 产品不能通过改元数据绕过适用性检查。
