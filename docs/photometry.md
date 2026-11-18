# 单源巡天测光

测光查询用于补充年轻恒星的光谱能量分布：光学点与 Gaia XP 对照，近红外和中红外点显示更长波段的辐射。它不改变已有 XP 拟合，也不由红外超额推导吸积率。

## 查询和展示

安装 0.3.0 或后续兼容版本后，给出精确的 Gaia DR3 源编号，并使用尚不存在的输出目录：

```text
gaia-xp photometry --source-id 6719035052475592576 --output PHOTOMETRY_DIRECTORY
gaia-xp report --run RUN --photometry PHOTOMETRY_DIRECTORY --output NEW_REPORT_DIRECTORY
```

第一步联网查询单源资料；第二步只读已保存的资料，可以离线运行。迁移时保留整个测光目录：`raw/` 中的查询原表、整理后的 `photometry.json` 和文件清单 `manifest.json`。报告显示光谱与测光比较图，并保留逐波段数值、匹配候选和出处。

## 目录与匹配

查询优先使用 VizieR/CDS。Gaia 位置和自行来自 [Gaia DR3（I/355/gaiadr3）](https://cdsarc.cds.unistra.fr/viz-bin/cat/I/355)，测光采用：

| 目录 | 展示波段 | 星等制 | 读图时注意 |
|---|---|---|---|
| [APASS DR9（II/336/apass9）](https://cdsarc.cds.unistra.fr/viz-bin/cat/II/336) | g′、r′、i′ | AB | 口径较大，需注意邻星混叠；单源观测历元未提供 |
| [2MASS（II/246/out）](https://cdsarc.cds.unistra.fr/viz-bin/cat/II/246) | J、H、Ks | Vega | 分开处理可靠测光、质量不足与上限 |
| [AllWISE（II/328/allwise）](https://cdsarc.cds.unistra.fr/viz-bin/cat/II/328) | W1–W4 | Vega | 分辨率较低，需检查混叠、污染与延展源旗标 |

默认搜索半径为 3″，可用 `--radius-arcsec` 调整，最大 10″。只有一个候选落入半径内才采用；多个候选保留为待核对。Gaia 位置按自行传播到 2MASS 和 AllWISE 的近似历元，其中 2MASS 再用候选的观测日期核对角距离。APASS 缺少逐源历元，使用 Gaia 2016 位置并记录这一限制；坐标的 J2000 分点不等于观测历元。

查询中心、候选及角距离均保留。未匹配、测光质量不足和网络查询失败分别记录；部分目录访问失败时，不将其解释为该巡天未检出。存在污染或饱和旗标的点仍可查看，但与通过筛选的测光分开显示。

## 单位与比较

保留目录星等和误差，按星等制及零点换算通量密度：Fν = Fν,0 × 10^(−0.4m)，单位 Jy；1 Jy = 10⁻²⁶ W m⁻² Hz⁻¹。星等误差换算为通量误差，零点、代表波长和参考来源随测光记录保存。上限与检出分开标记，不能把缺失误差当作零误差。

AllWISE 上限沿用目录的 95% 定义；2MASS 的 [CDS 说明](https://vizier.cfa.harvard.edu/ftp/cats/II/246/ReadMe)与[官方 FAQ](https://www.ipac.caltech.edu/2mass/releases/allsky/faq.html)分别写 95% 和 97%，因此本版保留其上限标记，暂不指定统一置信度。

APASS 的误差须结合 `u_e_*mag` 解读：0 表示多次观测的标准差，1 表示单次观测的 Poisson 误差；前者不是均值的标准误。定义见 [CDS 表说明](https://vizier.cfa.harvard.edu/ftp/cats/II/336/ReadMe)。

测光点放在滤光片的代表波长处，XP 则由原有 Fλ 换算成同一 Fν 单位；本版未对 XP 做滤光片积分、颜色改正或消光改正。两者的差异可能来自非同期变化、口径、混叠或标定，不能直接当作吸积变化。红外点也不用于延伸 XP 连续谱模型。

目录号、查询网址、获取时间、字段单位、质量旗标和原文件校验值保留在测光目录中。HTML 主文只显示科学比较所需内容，完整测光表与交叉匹配记录按需展开。后续若加入高质量光谱，还需另行核验波长/通量标定、观测时间和仪器分辨率，不能仅凭同源就称作吸积测量的独立验证。
