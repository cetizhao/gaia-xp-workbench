# 单条 Gaia XP 光谱的输入格式

程序读取一个 NPZ 光谱文件和一个 JSON 元数据文件。NPZ 保存观测与相关误差，JSON 保存数据身份、标定过程和外部先验。输入必须是已经外部标定的 **Gaia DR3 平均 XP**；可用 `gaia-fetch` 下载、校准并生成此格式，也可自备文件。不接受将 DR4 产品改名后使用。

## NPZ 数组

| 字段 | 类型、形状与单位 |
|---|---|
| `source_id` | Unicode 字符串标量，例如 `np.array("6719035052475592576")`；不能用浮点数或科学计数法存储 |
| `wave` | `[343]`，nm；必须为 336–1020 nm、步长 2 nm 的网格 |
| `flux` | `[343]`，W m⁻² nm⁻¹；保留真实负通量 |
| `noise_factor` | `[343, k]`，单位同通量密度，满足协方差 `C = B Bᵀ` |
| `covariance` | 可代替 `noise_factor` 的 `[343,343]` 对称半正定协方差，单位为通量密度单位的平方 |
| `mask` | 可选布尔 `[343]`；True 为有效点，省略时全部有效 |
| `error` | 可选 `[343]` 边缘标准差；提供时必须与协方差一致 |

`noise_factor` 与 `covariance` 必须且只能提供一个。仅有逐点误差不能替代相关误差。有效波长处通量必须有限、边缘误差为正；质量掩码之外的缺测值不会用于拟合。保留负通量，不能为了拟合方便将其裁剪为零。单位转换必须同时作用于通量和协方差。

## JSON 元数据

以下只是格式示例，不是可直接使用的目标测量。请替换为观测及外部目录的真实值和来源；不要根据拟合希望得到的结果反向设置先验。

```json
{
  "source_id": "6719035052475592576",
  "name": "目标名称",
  "release": "Gaia DR3",
  "product": "mean_xp",
  "epoch_time": null,
  "calibration": "externally_calibrated",
  "calibration_version": "实际标定软件版本及修正状态",
  "wavelength_unit": "nm",
  "flux_unit": "W m-2 nm-1",
  "input_reference": "发布产品、下载记录及校准记录的位置",
  "prior_reference": "光谱型、Av和Teff采用值的来源",
  "spt_num": 73.75,
  "av_mag": 0.3,
  "teff_k": 3300
}
```

`source_id` 必须与 NPZ 完全一致，并与发布版本一起解释。光谱型数值采用 K0=60、M0=70；例如 M3.75 为 73.75。当前新拟合接受 60–78，即 K0 至 M8。`av_mag` 是非负的 V 波段消光，单位 mag，不是 Ak；`teff_k` 是正的有效温度，单位 K，用于模型光球总通量修正。标定和先验来源字段必须填写实际依据；信息不足时应补齐来源。

## 可选的绝对物理量换算

可增加 `stellar_parameters` 对象，包含 `distance_pc` 和 `reference`；若需要质量吸积率，再同时提供 `mass_msun`、`radius_rsun`。距离单位为 pc，质量和半径分别以太阳质量和太阳半径为单位。所有数值须为正且有限。

程序采用 `Lacc = 4πd²Facc`，以及 `Mdot = 1.25 Lacc Rstar/(G Mstar)`，后式假设内截断半径为 `5 Rstar`。这些参数在本版中视为固定目录值；换算后验不传播距离、质量、半径或几何假设的不确定性。缺少距离时只报告通量；缺少质量或半径时不报告 Mdot。

## 运行与输出

```text
gaia-xp inspect --input spectrum.npz --metadata metadata.json
gaia-xp fit --input spectrum.npz --metadata metadata.json --output new_run
gaia-xp review --run new_run
```

先阅读检查输出中的阻止拟合原因；不能通过修改发布版本、伪造协方差或删去有效负通量来绕过检查。`new_run` 必须是不存在的新目录。成功输出含输入副本、`run_contract.json`、`posterior.npz`、`summary.json`、`review.json`、`report.md`、`spectrum_fit.png` 和 `corner_positive.png`，由 `status.json` 记录完整性。
