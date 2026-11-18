"""slab 使用的近似 XP 响应；不等于官方历元响应。"""
import numpy as np

def gaia_xp_resolving_power(wavelength_nm: np.ndarray | float) -> np.ndarray:
    """保守的 BP/RP 分段近似：BP R≈60→20，RP R≈50→30。"""
    wavelength = np.asarray(wavelength_nm, dtype=np.float64)
    bp = np.interp(wavelength, [336.0, 680.0], [60.0, 20.0])
    rp = np.interp(wavelength, [640.0, 1020.0], [50.0, 30.0])
    blend = np.clip((wavelength - 640.0) / 40.0, 0.0, 1.0)
    return (1.0 - blend) * bp + blend * rp
