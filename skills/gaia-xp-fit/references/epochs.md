# 单源多历元光谱窗口

报告首先展示逐次光谱窗口。它读取本地已保存的真实光谱，可叠加选定观测组、逐组浏览、切换全谱／蓝端／Hα，并拖选波长区间。默认在用于吸积诊断的蓝端显示宽缝档案谱和 Gaia DR3 平均谱参考；点选窄缝谱可查看原采样谱线。通量始终保留绝对尺度，纵轴只随可见波段调整，不重新归一化。

每条曲线旁标出仪器、臂、狭缝类型、观测时间及其时标。原采样和掩码保留，缺测区不连线；图中没有降分辨率或拟合。不同仪器的波长介质、速度参考系和响应尚未统一，不能直接用窄线位置差测速。狭缝与标定差异也可能改变通量。

独立历元按资料中的观测组统计，不能把同组不同臂和宽／窄缝重复计数。本例四条 X-shooter 光谱只有一个观测组，尚不足以构成时间序列；ESPRESSO 的档案候选记录不等于已经载入光谱。Gaia DR3 平均谱单独作为参考，不计入历元。没有真实 DR4 历元数据时，窗口明确显示待接入，不生成模拟曲线。

## 接入已经校准的逐历元资料

`report --epochs DIRECTORY` 可读 `DIRECTORY/epochs.json`，也可直接传 JSON 路径。这只是本地展示格式，不是 Gaia DR4 官方下载或校准接口；正式产品仍需先核验源身份、时间定义、单位、质量和校准方法。已有拟合保持不变。

```json
{
  "schema_version": 1,
  "source_id": "6719035052475592576",
  "wavelength_unit": "nm",
  "flux_unit": "W m-2 nm-1",
  "records": [
    {
      "epoch_id": "PRODUCT_ID",
      "group_id": "OBSERVATION_GROUP",
      "instrument": "INSTRUMENT",
      "time": {
        "value": "OFFICIAL_TIME_VALUE",
        "format": "MJD",
        "scale": "OFFICIAL_TIME_SCALE",
        "definition": "说明起点、中点或覆盖范围"
      },
      "calibration_reference": "已核验的校准来源",
      "arrays_file": "PRODUCT_ID.npz",
      "sha256": "该数组文件的SHA256"
    }
  ]
}
```

以上是字段示例，不是观测。每个 NPZ 需有一维递增 `wave_nm`、同长 `flux_w_m2_nm` 和布尔 `mask`；可附精确字符串 `source_id`。文件必须位于该资料目录内，逐文件校验值需匹配。单条记录的 `epoch_id` 唯一；同一次观测的不同臂可共用 `group_id`。可选字段包括 `arm`、`label`、`release`、`resolving_power`、`wavelength_medium`、`spectral_frame`。

顶层与 NPZ 的 `source_id` 是关联到当前报告的源编号，目前为 DR3 编号。外部发布产品应另保留 `native_source_id`、`release` 和 `identity_reference`，分别记录其原生源编号、发布版本和身份匹配依据；DR4 编号不能直接沿用 DR3。标为 `Gaia DR4` 的记录必须提供原生编号与身份匹配依据。跨版本对应必须在准备资料时独立核验，本格式不会替用户建立源身份映射。

时间原值按字符串保存，不以位置参考历元代替。支持 `ISO 8601`、`JD`、`MJD` 和 `offset days`；偏移日数还需 `time.zero_point`。时标与时间定义必填，不能直接把 TCB/TDB 写成 UTC；本窗口不执行时标转换。逐组浏览保留输入资料顺序，准备资料时应按核验过的观测顺序排列。平均谱应作为参考而不是逐历元记录加入。

报告记录 JSON 与所有数组文件的 SHA256。格式和校验通过只说明文件可读取、单位声明相符，不代表校准质量已经得到物理验证，也不使展示数据自动成为拟合输入。
