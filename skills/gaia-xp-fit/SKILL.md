---
name: gaia-xp-fit
description: 使用 Gaia XP 传统拟合工作台检查和拟合年轻恒星光谱，复查吸积约束，查询单源巡天测光，并生成总览图与离线 HTML 报告。支持已外部标定的 DR3 平均 XP、K/M 至 M8；不用于外部光谱下载、学习模型或 DR4 历元拟合。
---

# Gaia XP 拟合与解读

根据用户目标调用确定的 Python 程序，再以保存的数值和图解释结果。区分数值积分稳定、模型对该谱的适用性，以及吸积量是否完成独立物理标定。

## 选择操作

- 看已有结果或解释可靠性：`gaia-xp review --run RUN`，不重拟合。
- 为已有结果制作一源一图或 HTML：`gaia-xp report --run RUN --output NEW_DIRECTORY`，只读保存的观测、模型预测、后验和诊断。
- 查询指定源的巡天测光：`gaia-xp photometry --source-id GAIA_DR3_ID --output NEW_DIRECTORY`；再用 `gaia-xp report --run RUN --photometry PHOTOMETRY_DIRECTORY --output NEW_REPORT_DIRECTORY` 联合展示。
- 收到新光谱：`gaia-xp inspect --input SPECTRUM.npz --metadata METADATA.json`。
- 明确要求拟合：检查通过后使用 `gaia-xp fit --input SPECTRUM.npz --metadata METADATA.json --output NEW_DIRECTORY`。
- 整理选定结果：`gaia-xp summarize --run RUN_A --run RUN_B --output NEW_DIRECTORY`；不自动扩样、合并后验或做群体相关性分析。

命令中的路径优先用绝对路径。`photometry` 可按精确 Gaia DR3 编号取测光，但不会下载 XP 或其他光谱；拟合仍需要用户提供完整光谱输入。首次处理输入时阅读[单谱格式](references/input_format.md)；解释科学量与后验时阅读[方法和限制](references/scientific_scope.md)。这些说明随本 skill 分发，不依赖原研究项目。

## 环境与资产

需要 Python 3.12、已安装的 `gaia-xp` 命令及输入和输出目录访问权限；无需 MCP。先确认 `gaia-xp --help` 可用；测光查询与联合报告需要 0.3.0 或后续兼容版本。查询需联网，生成报告只读本地资料。新拟合另需模型资产缓存；`review`、`report` 和测光查询无需缓存。Python 包、skill 和模型资产是分开安装的。资产位置由 `GAIA_XP_ASSETS` 或顶层 `--assets-dir DIR` 指定；例如 `gaia-xp --assets-dir CACHE assets check`。缺资产时读取清单和错误；已有来源可用 `gaia-xp --assets-dir CACHE assets import --from-dir SOURCE` 复制并校验，不伪造资产、不改校验值。Fang 模板公开来源与再分发许可未确认，不能宣称安装后必然能自动下载全部资产。

Windows 终端宜设置 `$env:PYTHONUTF8='1'`。数值入口采用 Agg 绘图、两个积分线程与单线程 BLAS；一次只运行一个重计算进程。新拟合、测光下载、报告与汇总使用不存在的新目录。失败时读错误和已有状态记录，不把局部输出当作成功，也不为通过检查无限增加网格。

## 输入和解读规则

新拟合仅支持已外部标定的 Gaia DR3 平均 XP、K/M 至 M8、336–1020 nm 且步长 2 nm。必须有完整协方差或其因子、明确单位及光谱型/Av/Teff 来源。保留负通量与掩码，源编号使用精确十进制字符串。缺信息时明确指出，不用逐点独立误差或猜测先验静默代替。

成功运行先确认 `status.json` 为 complete，再读 `review.json`，打开 `spectrum_fit.png` 和 `corner_positive.png`。按用户所需篇幅说明数据、方法、主要约束、残差、退化和仍缺的证据。含零分支分位数、上限与 P0 一起解释；corner 仅表示条件正分支。

制作报告时保留原运行，只写新目录。交付 `overview.png` 与可离线打开的 `report.html`，并保留 `report_manifest.json` 的来源记录；HTML 图片已内嵌，不需要联网。核对总览的主要量、全谱、蓝端、残差和 posterior 均可读。报告中的数值来自已保存结果，不能因画图重估分位数或填补未保存的 Lacc/Mdot。旧运行没有为光谱或预测文件预存哈希时，本次记录的哈希只说明读取了哪个版本，不证明文件自拟合后从未改变。若必需结果缺失，报告具体缺项，不自动重跑拟合补齐。

测光查询限用户选定的源。保留原表、单位、星等制、质量旗标、候选源和匹配距离；检查自行改正与观测历元，多个候选时不擅自选最近者。区分未检出、质量不足和服务查询失败。对测光与 XP 的比较，应说明非同期、滤光片宽度及盘红外辐射的影响；本版未做滤光片积分或吸积交叉标定。不能把上限当检出，也不能用测光替换 XP 后验。

报告面向天文学研究者：主要结果与比较图放前面，技术细节和完整数据表按需展开。用简短完整的句子说明图中看到了什么，不堆砌程序术语或重复限制。

r 是 700–900 nm 光学超额比，Facc 是模型 50–2477.47 nm 的积分通量，q 是模型 Facc/Fstar，三者不可混称。Lacc 需要距离，Mdot 还需要质量、半径和截断半径假设；此版可选换算采用固定恒星参数，未传播它们的误差。新运行没有自动执行先验敏感性试验。

数值通过、较小 P0、较大 Bayes 因子或漂亮谱图都不能升级为普适已校准测量。外部混叠信息未知时照实报告。DR3 平均谱拟合不能称作时间变化；DR4 产品不能通过改元数据绕过适用性检查。
