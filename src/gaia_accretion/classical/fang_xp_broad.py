"""Fang+25原生XP光球与宽波段连续谱模型；不重复展宽经验光球。"""
from dataclasses import replace
from functools import lru_cache
import numpy as np

from gaia_accretion.pseudo_xp import gaia_xp_resolving_power
from gaia_accretion.support.p2.templates import (
    load_template_grid, select_template_nodes, interpolate_template,
    apply_ccm89_extinction,
)
from .luminosity import PhotosphereCorrection
from .luminosity_reference import ReferenceLuminosityModel, author_library


# 左闭右开的宽波段避免共享端点。避开Balmer边缘过渡区与Halpha邻域。
BROAD_WINDOWS = [
    (340., 364.), (386., 414.), (414., 444.), (444., 474.),
    (474., 514.), (514., 554.), (554., 594.), (594., 634.),
    (678., 710.), (710., 746.), (746., 786.), (786., 826.),
    (826., 866.), (866., 906.), (906., 946.), (946., 986.),
]


def broad_projection(wave, valid=None):
    """首列仅用于单位与r定义；其余16列才是实际似然观测量。"""
    wave = np.asarray(wave, float)
    valid = np.ones(len(wave), bool) if valid is None else np.asarray(valid, bool)
    red = (wave >= 700) & (wave <= 900) & valid
    if red.sum() < 20:
        raise ValueError('红端尺度覆盖不足')
    columns = [red / red.sum()]
    for lo, hi in BROAD_WINDOWS:
        available = (wave >= lo) & (wave < hi)
        chosen = available & valid
        if chosen.sum() < 8 or chosen.sum() < .8 * available.sum():
            raise ValueError(f'宽波段覆盖不足：{lo}-{hi} nm')
        columns.append(chosen / chosen.sum())
    return np.asarray(columns).T


class FangXPBroadModel(ReferenceLuminosityModel):
    """只继承已核验的slab积分与似然算法，独立构造Fang光球与投影。"""
    def __init__(self, wave, config, valid_mask=None):
        self.settings = config
        self.wave = np.asarray(wave, float)
        self.valid_mask = np.ones(len(wave), bool) if valid_mask is None else np.asarray(valid_mask, bool)
        self.projection = broad_projection(self.wave, self.valid_mask)
        self.band_names = ['red700-900_unit_only'] + [f'F{a:g}-{b:g}' for a, b in BROAD_WINDOWS]
        self.red = 0
        self.indices = np.arange(1, len(self.band_names))
        self.balmer_weight = 1.
        self.rv = float(config['rv'])
        self.nu = float(config['degrees_of_freedom'])
        self.mismatch = float(config['template_fraction'])
        self.sigma_av = float(config['delta_av_prior_sigma'])
        self.logr_bounds = np.log10(config['r_limits'])
        self.amplitude_bounds = np.asarray(config['total_red_scale_limits'])
        self.correction = PhotosphereCorrection(config['calibration'])
        self.fang = select_template_nodes(load_template_grid(), config['fang_node_policy'])
        if not np.array_equal(self.wave, self.fang['wavelength_nm']):
            raise ValueError('输入与Fang模板必须使用同一原生XP波长网格')
        self.photo_kind = 'fang25_native_xp'
        full_wave, full_flux, self.shape_parameters, self.shape_prior, self.shape_family = author_library()
        self.shape_log_prior = np.log(self.shape_prior)
        self.integral_wave = full_wave
        self.slab_integral = np.trapezoid(full_flux, full_wave, axis=1)
        self.dense_wave = np.arange(300., 1100.25, .25)
        self.dense_slab = np.asarray([np.interp(self.dense_wave, full_wave, f) for f in full_flux])
        sigma = self.wave / gaia_xp_resolving_power(self.wave) / 2.354820045
        kernel = np.exp(-.5 * ((self.dense_wave[None, :] - self.wave[:, None]) / sigma[:, None])**2)
        self.response = kernel / kernel.sum(axis=1, keepdims=True)
        self.band_response = self.projection.T @ self.response
        self._quadratic_cache = {}

    @lru_cache(maxsize=1024)
    def photosphere(self, spt):
        # Fang模板已经由XP构造；不展宽、不改为FRAPPE、不裁剪负通量。
        return np.asarray(interpolate_template(self.fang, float(spt))['flux'], float)

    def make_context(self, flux, covariance, spt, av, teff=None):
        if teff is None:
            raise ValueError('必须显式提供目录Teff；本轮不从另一套光球库映射温度')
        return super().make_context(flux, covariance, spt, av, teff=teff)


def photo_context(model, anchor, spt):
    """更新Fang形状；固定目录温度只用于附属光球总光度诊断。"""
    photo = model.photosphere(float(spt))
    fbol = model.correction.bolometric_flux(model.wave, photo, anchor.teff)
    pn, pc = [], []
    for dv in anchor.av_nodes:
        pb = apply_ccm89_extinction(model.wave, photo, anchor.base_av + dv, model.rv)['flux'] @ model.projection
        pn.append(pb[model.indices] / pb[model.red])
        pc.append(fbol / pb[model.red])
    return replace(anchor, spt=float(spt), photo_nodes=np.asarray(pn), photo_correction=np.asarray(pc))
