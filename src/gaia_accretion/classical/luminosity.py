"""当前 Fang 入口实际使用的尺度积分、抽样和光度换算。"""
from __future__ import annotations
from dataclasses import dataclass
import numpy as np
from scipy.special import gammaln, logsumexp, stdtr, stdtrit
from gaia_accretion.assets import asset_path
from gaia_accretion.support.p2.templates import apply_ccm89_extinction
PC_M = 3.085677581491367e16
LSUN_W = 3.828e26

def luminosity_lsun(flux_w_m2, distance_pc):
    """由消光改正后的地球处积分通量换算光度，保留零值。"""
    flux, distance = np.broadcast_arrays(np.asarray(flux_w_m2, float), np.asarray(distance_pc, float))
    if not np.isfinite(flux).all() or np.any(flux < 0):
        raise ValueError("积分通量必须有限且非负")
    if not np.isfinite(distance).all() or np.any(distance <= 0):
        raise ValueError("距离必须为有限正值，单位 pc")
    return 4 * np.pi * (distance * PC_M)**2 * flux / LSUN_W

def log_with_zero(values):
    values = np.asarray(values, float)
    if np.any(values < 0) or not np.isfinite(values).all():
        raise ValueError("对数的输入必须有限且非负")
    result = np.full(values.shape, -np.inf)
    np.log10(values, out=result, where=values > 0)
    return result

class PhotosphereCorrection:
    """作者发布的 f751/Fbol（每埃）及 SpT—Teff 表；禁止边界外插。"""
    def __init__(self, config):
        self.bc = np.loadtxt(asset_path("bc_table"))
        rows = np.genfromtxt(asset_path("temperature_table"), dtype=str, skip_header=1)
        self.spt = np.array([{"G": 50, "K": 60, "M": 70}[s[0]] + float(s[1:]) for s in rows[:, 0]])
        self.temperature = rows[:, 2].astype(float)

    def teff(self, spt):
        if not np.isfinite(spt) or not self.spt[0] <= spt <= self.spt[-1]:
            raise ValueError("SpT 超出校准表支持；不可外插")
        return float(np.interp(spt, self.spt, self.temperature))

    def factor_per_nm(self, teff):
        if not np.isfinite(teff) or not self.bc[0, 0] <= teff <= self.bc[-1, 0]:
            raise ValueError("Teff 超出光度修正支持；不可外插")
        # 原表是每埃，拟合谱是每纳米，因此需乘 10。
        return float(10 * np.interp(teff, self.bc[:, 0], self.bc[:, 1]))

    def bolometric_flux(self, wave, intrinsic_photo, teff):
        wave, photo = np.asarray(wave), np.asarray(intrinsic_photo)
        if wave[0] > 730 or wave[-1] < 758:
            raise ValueError("光球谱未覆盖总光度修正所需窗口")
        if teff < 3500:
            anchor = np.interp([730., 758.], wave, photo) @ np.array([.25, .75])
        else:
            anchor = np.median(photo[(wave > 747) & (wave < 755)])
        if not np.isfinite(anchor) or anchor <= 0:
            raise ValueError("光球 751 nm 代理连续谱必须为正")
        return float(anchor / self.factor_per_nm(teff))

@dataclass
class FluxContext:
    spt: float
    teff: float
    base_av: float
    flux_unit: float
    band_flux: np.ndarray
    band_covariance: np.ndarray
    observed: np.ndarray
    scale_matrix: np.ndarray
    precision: np.ndarray
    log_normalization: float
    av_nodes: np.ndarray
    photo_nodes: np.ndarray
    slab_nodes: np.ndarray
    photo_correction: np.ndarray
    slab_correction: np.ndarray
    red_snr: float

class LuminosityModel:
    """仅保留宽波段 Fang 模型调用的公共数值方法。"""
    @staticmethod
    def interpolate_nodes(nodes, values, x):
        x = np.atleast_1d(x)
        index = np.clip(np.searchsorted(nodes,x)-1,0,len(nodes)-2)
        fraction = (x-nodes[index])/(nodes[index+1]-nodes[index])
        fraction = fraction.reshape((-1,)+(1,)*(values.ndim-1))
        return values[index]*(1-fraction)+values[index+1]*fraction

    def make_context(self, flux, covariance, spt, av, teff=None):
        flux, covariance = np.asarray(flux, float), np.asarray(covariance, float)
        if flux.shape != self.wave.shape or not np.isfinite(flux[self.valid_mask]).all():
            raise ValueError("有效波长上需要有限流量")
        if covariance.shape != (len(self.band_names),) * 2 or not np.isfinite(covariance).all():
            raise ValueError("需要全部窗口的有限协方差矩阵")
        if not np.isfinite(av) or av < 0:
            raise ValueError("外部 Av 必须有限且非负")
        band = np.where(self.valid_mask, flux, 0.) @ self.projection
        scale = float(band[self.red])
        if scale <= 0 or covariance[self.red, self.red] <= 0:
            raise ValueError("红端均值及其方差必须为正")
        snr = scale / np.sqrt(covariance[self.red, self.red])
        if snr < self.settings["minimum_red_snr"]:
            raise ValueError("红端 S/N 不足，暂不输出光度")
        c = covariance[np.ix_(self.indices, self.indices)] / scale**2
        if not np.allclose(c, c.T, rtol=1e-8, atol=1e-12) or np.linalg.eigvalsh(c).min() < -1e-10 * np.max(np.diag(c)):
            raise ValueError("输入窗口协方差不是对称半正定矩阵")
        photo = self.photosphere(float(spt))
        teff = self.correction.teff(spt) if teff is None else float(teff)
        fbol = self.correction.bolometric_flux(self.wave, photo, teff)
        reference = apply_ccm89_extinction(self.wave, photo, av, self.rv)["flux"] @ self.projection
        floor = self.mismatch * np.maximum(np.abs(reference[self.indices] / reference[self.red]), .2)
        matrix = (c + c.T) / 2 + np.diag(floor**2)
        sign, logdet = np.linalg.slogdet(matrix)
        if sign <= 0:
            raise ValueError("似然尺度矩阵必须正定")
        n = len(self.indices)
        constant = gammaln((self.nu + n) / 2) - gammaln(self.nu / 2) - .5 * (n * np.log(self.nu * np.pi) + logdet)
        lower, upper = self.settings["delta_av_limits"]
        nodes = np.linspace(max(lower, -av), upper, self.settings["interpolation_nodes"])
        if nodes[-1] <= nodes[0]:
            raise ValueError("消光先验支持为空")
        if nodes[0] <= 0 <= nodes[-1]:
            nodes = np.unique(np.r_[nodes, 0.])
        pn, sn, pc, sc = [], [], [], []
        for delta in nodes:
            extinction = apply_ccm89_extinction(self.dense_wave, np.ones_like(self.dense_wave), av + delta, self.rv)["flux"]
            sb = (self.dense_slab * extinction) @ self.band_response.T
            pb = apply_ccm89_extinction(self.wave, photo, av + delta, self.rv)["flux"] @ self.projection
            pn.append(pb[self.indices] / pb[self.red])
            sn.append(sb[:, self.indices] / sb[:, self.red, None])
            pc.append(fbol / pb[self.red])
            sc.append(self.slab_integral / sb[:, self.red])
        return FluxContext(float(spt), teff, float(av), scale, band, covariance,
                           band[self.indices] / scale, matrix, np.linalg.inv(matrix), float(constant), nodes,
                           np.array(pn), np.array(sn), np.array(pc), np.array(sc), float(snr))

    def draw_grid(self, context, grid, count, rng, zero=False):
        if zero:
            delta = rng.choice(grid["av_zero"], count, p=grid["weight_zero"])
            logr = np.full(count, -np.inf)
        else:
            nodes = grid["points"][rng.choice(len(grid["points"]), count, p=grid["weight"])]
            logr, delta = nodes.T
        ll, center, width, low, high = self.amplitude_distribution(context, logr, delta, zero)
        if not zero:
            ll = ll + self.shape_log_prior
        probability = np.exp(ll - logsumexp(ll, axis=1)[:, None])
        shape = (rng.random(count)[:, None] > np.cumsum(probability, axis=1)).sum(axis=1)
        shape = np.minimum(shape, ll.shape[1] - 1)
        index = (np.arange(count), shape)
        df = self.nu + len(self.indices) - 1
        lower, upper = low[index], high[index]
        u = rng.random(count)
        cdf = stdtr(df, lower) + u * (stdtr(df, upper) - stdtr(df, lower))
        survival = stdtr(df, -upper) + u * (stdtr(df, -lower) - stdtr(df, -upper))
        z = np.where(lower > 0, -stdtrit(df, survival), stdtrit(df, cdf))
        amplitude = center[index] + width[index] * z
        if not np.isfinite(amplitude).all() or np.any(amplitude < 0) or np.any(amplitude > self.amplitude_bounds[1]):
            raise ValueError("尺度条件分布采样超出先验")
        return np.c_[logr, delta, amplitude], np.full(count, -1, int) if zero else shape

    def physical_samples(self, context, theta, shape_index, distance_pc=None):
        theta, shape = np.asarray(theta), np.asarray(shape_index, int)
        r = 10**theta[:, 0]
        positive = shape >= 0
        if np.any(positive != (r > 0)) or np.any(shape >= len(self.shape_parameters)):
            raise ValueError("零吸积分支与 slab 编号不一致")
        pc = self.interpolate_nodes(context.av_nodes, context.photo_correction, theta[:, 1])
        sc = self.interpolate_nodes(context.av_nodes, context.slab_correction, theta[:, 1])
        photo_red = context.flux_unit * theta[:, 2] / (1 + r)
        fstar = photo_red * pc
        facc = np.zeros(len(theta))
        facc[positive] = photo_red[positive] * r[positive] * sc[np.flatnonzero(positive), shape[positive]]
        result = {"r_red": r, "av_mag": context.base_av + theta[:, 1],
                  "total_red_flux_w_m2_nm": context.flux_unit * theta[:, 2],
                  "facc_50_2500nm_w_m2": facc, "fstar_bol_w_m2": fstar,
                  "lacc_over_lstar": facc / fstar, "log10_lacc_over_lstar": log_with_zero(facc / fstar)}
        if distance_pc is not None:
            distance = np.broadcast_to(np.asarray(distance_pc, float), facc.shape)
            result.update({"distance_pc": distance, "lacc_lsun": luminosity_lsun(facc, distance),
                           "lstar_lsun": luminosity_lsun(fstar, distance)})
            result["log10_lacc_lsun"] = log_with_zero(result["lacc_lsun"])
        return result
