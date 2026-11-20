"""英文报告中历史方法说明的对应译文。"""
import re


MODEL_LIMITS = [
    "The Fang photospheric templates have incomplete records of contributing stars and wavelength covariance. Their independence from the CrA sample remains uncertain.",
    "The slab model uses an approximate XP response. The fit assumes a 5% model error and a 1% red flux floor.",
    "The zero-branch probability and Bayes factor depend on the model and priors. Their empirical false-positive rates and calibration against independent accretion measurements remain unknown.",
    "The optical excess r is the reddened slab-to-photosphere flux-density ratio at 700–900 nm. The model luminosity ratio q uses Facc/Fstar.",
    "Facc integrates the slab spectrum over 50–2477.47 nm. Absolute luminosity and mass accretion rate also require distance and stellar parameters.",
    "DR3 mean XP averages the spectrum over multiple visits. A fit to that spectrum cannot establish the accretion rate at an individual visit or its time average.",
]
PRIOR_NOTE = "This run used a single prior prescription. Narrow intervals can reflect the imposed priors."
NO_DISTANCE = "A distance is required to derive the accretion luminosity and mass accretion rate."
FIXED_DISTANCE = "Lacc uses the fixed catalogue distance. Its interval excludes distance uncertainty."
FIXED_STELLAR = "Lacc and Mdot use fixed catalogue values for distance, mass and radius, with Rin = 5 Rstar. Their intervals exclude uncertainty in these inputs and in the accretion geometry."

METRIC_LABELS = {
    "p_spt_edge": "Posterior fraction near the spectral-type boundary",
    "p_av_upper": "Positive-branch fraction near the upper extinction boundary",
    "p_r_upper": "Positive-branch fraction near the upper optical-excess boundary",
    "max_abs_band_residual_sigma": "Largest absolute band residual (marginal σ)",
    "red_residual": "Median absolute fractional residual at 600–950 nm",
    "blue_continuum_snr": "Blue-band continuum signal-to-noise ratio",
}

_LEGACY = {
    "Fang光球的贡献星身份与波长协方差不完整，CrA与模板构造样本的独立性未确认。": MODEL_LIMITS[0],
    "slab使用近似XP响应；5%模型误差与1%红端下限是采用值，不是经验测得的系统误差。": MODEL_LIMITS[1],
    "零分支概率与Bayes因子以本模型及先验为条件，尚未标定为真实吸积概率或误报率。": MODEL_LIMITS[2],
    "r为消光后700–900 nm的slab/光球比；q为模型Facc/Fstar，二者不能互换。": MODEL_LIMITS[3],
    "Facc积分范围为作者slab的50–2477.47 nm；绝对光度与吸积率还依赖距离及恒星参数。": MODEL_LIMITS[4],
    "DR3平均谱的拟合不是历元测量，亦不等于真实吸积率的时间平均。": MODEL_LIMITS[5],
    "未执行先验敏感性比较；窄区间不等于由数据独立确定": PRIOR_NOTE,
    "未提供距离，不输出绝对Lacc或Mdot": NO_DISTANCE,
    "Lacc采用固定目录距离；分位数未传播距离误差": FIXED_DISTANCE,
    "Lacc、Mdot采用固定目录距离、质量和半径，且Rin=5Rstar；分位数未传播这些参数及几何假设的不确定性": FIXED_STELLAR,
}

_FLAGS = {
    "spt_support_boundary": "spectral type near a grid boundary",
    "av_upper_boundary": "extinction near the upper grid boundary",
    "r_upper_boundary": "optical excess near the upper grid boundary",
    "red_residual_gt_0.1": "red fractional residual above 10%",
    "blue_snr_below_3": "blue continuum signal-to-noise ratio below 3",
}


def english_note(value, *, fallback="See the source record for the original note."):
    """历史内置说明有固定译文；其他中文自由文本保留在原始记录中。"""
    text = str(value).strip()
    if text in _FLAGS:
        return _FLAGS[text]
    if text in _LEGACY:
        return _LEGACY[text]
    if re.search(r"[\u3400-\u9fff\uf900-\ufaff\U00020000-\U0002FA1F]", text):
        return fallback
    return text
