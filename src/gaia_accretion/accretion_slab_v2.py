"""按 Manara 2014 / John 1988 公式核验的 LTE 氢连续谱。

输入 nm、K、log10(cm^-3)、氢在 300 nm 的光深；输出 CGS 每埃每球面度比强度。
修正旧 Gaunt 求和和 H⁻ 系数/指数；H⁻ 近似的未覆盖 UV 不作多项式外插。
本包只包含修订公式，不提供旧内核。来源文件的哈希与提取记录见
resources/extraction.json；第三方来源与使用限制见仓库的授权说明。
"""
from __future__ import annotations

import numpy as np

SLAB_VERSION = "manara_john_checked_v2"
C = 2.99792458e10
H = 6.62607004e-27
KB = 1.38064852e-16
ME = 9.10938356e-28
NU_LYMAN = 3.28795e15
ALPHA_UM_K = 1.439e4
LAMBDA_MINUS_UM = 1.6419
N_BOUND = 19

# 每行对应原表 n=1…6，每列 A…F；已逐行对照论文表 2.2、2.3 和作者代码。
FF_SHORT = np.array([
    [518.1021, -734.8667, 1021.1775, -479.0721, 93.1373, -6.4285],
    [473.2636, 1443.4137, -1977.3395, 922.3575, -178.9275, 12.3600],
    [-482.2089, -737.1616, 1096.8827, -521.1341, 101.7963, -7.0571],
    [115.5291, 169.6374, -245.6490, 114.2430, -21.9972, 1.5097],
    [0., 0., 0., 0., 0., 0.],
    [0., 0., 0., 0., 0., 0.],
])
FF_LONG = np.array([
    [0., 0., 0., 0., 0., 0.],
    [2483.3460, 285.8270, -2054.2910, 2827.7760, -1341.5370, 208.9520],
    [-3449.8890, -1158.3820, 8746.5230, -11485.6320, 5303.6090, -812.9390],
    [2200.0400, 2427.7190, -13651.1050, 16755.5240, -7510.4940, 1132.7380],
    [-696.2710, -1841.4000, 8624.9700, -10051.5300, 4400.0670, -655.0200],
    [88.2830, 444.5170, -1863.8640, 2095.2880, -901.7880, 132.9850],
])
BF_COEFFICIENTS = np.array([152.519, 49.534, -118.858, 92.536, -34.194, 4.982])


def planck_nu(nu, temperature):
    nu = np.asarray(nu, float)
    return 2 * H * nu**3 / C**2 / np.expm1(H * nu / (KB * temperature))


def gaunt_fb(nu, temperature, n_max=N_BOUND):
    """每个可达能级只加一次；不把按最低能级分组误写为累积掩码。"""
    nu = np.asarray(nu, float)
    f = nu / NU_LYMAN
    lowest = np.floor(np.sqrt(1 / f) + 1).astype(int)
    answer = np.zeros_like(nu)
    for n in range(1, n_max + 1):
        gn = (1 + .1728 * (f**(1/3) - 2*f**(-2/3)/n**2)
              - .0496 * (f**(2/3) - 2*f**(-1/3)/(3*n**2) + 2*f**(-4/3)/(3*n**4)))
        answer += (n >= lowest) * np.exp(H*NU_LYMAN/(n**2*KB*temperature)) * gn / n**3
    return 2*H*NU_LYMAN/(KB*temperature) * answer


def gaunt_ff(nu, temperature):
    nu = np.asarray(nu, float)
    f, u = nu / NU_LYMAN, KB * temperature / (H * nu)
    return 1 + .1728*f**(1/3)*(1+2*u) - .0496*f**(2/3)*(1+2*u/3+4*u*u/3)


def hminus_coefficients(wavelength_um, temperature):
    """返回每单位电子压强、每中性氢的 bf/ff 吸收系数，cm^4/dyne。

    BF 仅 0.125…1.6419 μm；FF 仅大于 0.182 μm。域外返回零表示本近似省略，
    不声称真实物理吸收为零。温度必须在原表 0.5≤5040/T≤3.6 的范围。
    """
    if not np.isfinite(temperature) or not 1400 <= temperature <= 10080:
        raise ValueError("H⁻ 系数仅支持 1400–10080 K；禁止静默温度外插")
    wave = np.asarray(wavelength_um, float)
    if not np.isfinite(wave).all() or np.any(wave <= 0):
        raise ValueError("H⁻ 波长必须为有限正值 μm")
    bf, ff = np.zeros_like(wave), np.zeros_like(wave)
    valid = (wave >= .125) & (wave < LAMBDA_MINUS_UM)
    w = wave[valid]
    x = 1 / w - 1 / LAMBDA_MINUS_UM
    polynomial = np.polynomial.polynomial.polyval(np.sqrt(x), BF_COEFFICIENTS)
    sigma = 1e-18 * w**3 * x**1.5 * polynomial
    bf[valid] = (.750 * temperature**-2.5 * np.exp(ALPHA_UM_K/(LAMBDA_MINUS_UM*temperature))
                 * -np.expm1(-ALPHA_UM_K/(w*temperature)) * sigma)
    temperature_powers = (5040/temperature)**((np.arange(1, 7)+1)/2)
    for valid, coefficients in (((wave > .182) & (wave < .3645), FF_SHORT),
                                (wave >= .3645, FF_LONG)):
        w = wave[valid]
        basis = np.stack([w*w, np.ones_like(w), 1/w, 1/w**2, 1/w**3, 1/w**4])
        ff[valid] = 1e-29 * temperature_powers @ coefficients @ basis
    if np.any(bf < 0) or np.any(ff < 0) or not np.isfinite(bf+ff).all():
        raise ValueError("有效域内 H⁻ 系数出现负值或非有限值")
    return bf, ff


def slab_components(wavelength_nm, T, log_ne, tau_0):
    """提供可独立核对的光深、厚度和比强度，不引入地球处流量或面积。"""
    wave = np.asarray(wavelength_nm, float)
    if wave.ndim != 1 or not len(wave) or not np.isfinite(wave).all() or np.any((wave < 50) | (wave > 2500)):
        raise ValueError("slab 输入需要 50–2500 nm 的非空一维波长")
    if not np.isfinite(log_ne) or not 0 <= log_ne <= 20 or not np.isfinite(tau_0) or tau_0 < 0:
        raise ValueError("电子密度或参考光深非法")
    bf, ff = hminus_coefficients(wave / 1000, T)
    nu, nu_ref = C/(wave*1e-7), C/(300e-7)
    ne = 10.**log_ne
    b = planck_nu(nu, T)
    def emissivity(frequency):
        return (5.44e-39 * T**-.5 * ne**2 * np.exp(-H*frequency/(KB*T))
                * (gaunt_fb(frequency, T) + gaunt_ff(frequency, T)))
    thickness = float(tau_0 * planck_nu(nu_ref, T) / emissivity(nu_ref))
    tau_h = emissivity(nu) * thickness / b
    levels = np.arange(1, N_BOUND + 1, dtype=float)
    neutral = (ne**2 * H**3/(2*np.pi*ME*KB)**1.5 * T**-1.5
               * np.sum(levels**2 * np.exp(H*NU_LYMAN/(levels**2*KB*T))))
    tau_minus = (bf + ff) * ne * neutral * KB*T * thickness
    total_tau = tau_h + tau_minus
    if np.any(total_tau < 0) or not np.isfinite(total_tau).all():
        raise ValueError("总光深出现非法值，不能裁剪后继续")
    conversion = C/(wave*1e-7)**2 * 1e-8
    return {"intensity_per_A_sr": b * -np.expm1(-total_tau) * conversion,
            "planck_per_A_sr": b * conversion, "tau_h": tau_h, "tau_hminus": tau_minus,
            "thickness_cm": thickness, "neutral_h_cm3": float(neutral)}


def compute_slab_spectrum(wavelength_nm, T, log_ne, tau_0):
    return slab_components(wavelength_nm, T, log_ne, tau_0)["intensity_per_A_sr"]
