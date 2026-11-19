# 档案光谱与 XP 对照

先按 Gaia DR3 源编号查询 ESO 已归约一维光谱，并补查 MAST 光谱覆盖；再下载指定产品。读取 FITS 需要 `pip install ".[spectroscopy]"`，已有整理结果的报告可只用核心依赖离线生成。

```text
gaia-xp spectra-search --source-id 6719035052475592576 --output DISCOVERY
gaia-xp spectra-fetch --discovery DISCOVERY --output SPECTRA
gaia-xp report --run RUN --spectra SPECTRA --output REPORT
```

搜索半径默认 5″、最大 10″。查询以 Gaia 参考位置为中心，再按观测日期和自行核对角距离；初查范围外的高自行源可能漏检。指向位置与名称相符不等于已排除伴星或狭缝混叠。ESO 目录来自 [ObsCore 服务](https://www.eso.org/cms/eso-data/programmatic-access.html)，下载地址取返回的 DataLink 主产品，不根据文件名猜测。MAST 当前只记录覆盖，未实现其下载转换。

默认建议最近一次同时具有 UVB/VIS 的 X-shooter 观测，并保留该组各光学设置，最多六个产品；没有适合的组时需检查候选表。可以重复 `--product-id` 指定查询中已有的产品。当前转换器只接收具有明确绝对通量单位的 ESO 标准一维表；不把计数或连续谱归一化值冒充物理通量。产品的原始 FITS、附带说明、查询响应、观测日期、狭缝、名义分辨率、单位和校验值一并保存。

2022-05-06 的 V721 CrA（同一 Gaia 源）有 X-shooter 宽缝和窄缝 UVB/VIS。本次采用四个光学产品；NIR 与后来的 ESPRESSO 观测保留在候选记录中。宽缝 5″ 产品适合比较光谱能量分布；窄缝 0.5″/0.4″ 产品分辨率更高，可检查 Balmer 线形，但狭缝通量损失明显，不能直接当作绝对亮度变化。

X-shooter 原通量单位为 erg s⁻¹ cm⁻² Å⁻¹，换成 W m⁻² nm⁻¹ 乘 0.01；误差同步转换，保留负通量，绘图采用有效且 `QUAL=0` 的像素。[ESO 产品说明](https://www.eso.org/rm/api/v1/public/releaseDescriptions/70)指出其波长为空气、地面观测者参考系，未作大气吸收改正；`SPEC_RES` 是弧灯确定的名义分辨率，不能作为逐次实测值。宽缝产品也未给出定量绝对通量标定误差。

与平均 XP 的比较可检查大尺度连续谱形状、蓝端及发射线是否相容。简单分箱不是 Gaia 仪器响应卷积，不能将分辨率不同的窄线逐点相减；非同期差异还可能来自恒星变化、消光、狭缝损失和标定。本版不据此重新拟合 XP 或推导新的吸积率。
