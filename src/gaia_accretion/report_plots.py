"""只绘制保存的光谱预测与后验，不调用模板、拟合或重新抽样。"""
from __future__ import annotations

from pathlib import Path
import textwrap

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.ticker import MaxNLocator
import numpy as np


_BLUE = "#226e9b"
_INK = "#233443"
_PHOTO = "#b66c29"
_SLAB = "#92639b"


def _number(value):
    if value is None or not np.isfinite(value):
        return "not provided"
    return f"{value:.3g}"


def _quantile(report, key, level):
    values = report.get("quantities", {}).get(key)
    if values is None:
        return None
    for index, stored_level in enumerate(report.get("quantile_levels", [])):
        if np.isclose(stored_level, level):
            return float(values[index])
    return None


def _observed(spectrum):
    wave = np.asarray(spectrum["wave"])
    flux = np.asarray(spectrum["flux"])
    mask = np.asarray(spectrum.get("mask", np.ones(wave.shape, dtype=bool)), dtype=bool)
    if "noise_factor" in spectrum:
        error = np.linalg.norm(spectrum["noise_factor"], axis=1)
    elif "covariance" in spectrum:
        error = np.sqrt(np.diag(spectrum["covariance"]))
    else:
        error = np.asarray(spectrum["error"])
    red = (wave >= 700) & (wave <= 900) & mask
    scale = float(np.mean(flux[red]))
    if not np.isfinite(scale) or scale <= 0:
        raise ValueError("保存的红端通量无法用于绘图归一化")
    return wave, np.where(mask, flux / scale, np.nan), np.where(mask, error / scale, np.nan), scale


def _style_axes(ax):
    ax.spines[["top", "right"]].set_visible(False)
    ax.tick_params(labelsize=8, colors=_INK)
    ax.grid(axis="y", color="#e7edf1", linewidth=.6, zorder=0)


def _spectrum(ax, spectrum, prediction, *, blue=False, legend=False):
    wave, observed, error, scale = _observed(spectrum)
    ax.fill_between(wave, observed - error, observed + error, color="#dce1e5", label="XP marginal 1 sigma", zorder=1)
    ax.fill_between(wave, prediction["lower"] / scale, prediction["upper"] / scale, color=_BLUE, alpha=.20, label="Model p16-p84", zorder=2)
    ax.plot(wave, observed, color="#555e65", lw=.85, label="DR3 mean XP", zorder=3)
    ax.plot(wave, prediction["median"] / scale, color=_BLUE, lw=1.4, label="Total median", zorder=4)
    ax.plot(wave, prediction["photo"] / scale, color=_PHOTO, lw=1.2, ls="--", label="Photosphere median")
    ax.plot(wave, prediction["slab"] / scale, color=_SLAB, lw=1.2, ls="--", label="Slab median")
    ax.axhline(0, color="#909ba4", lw=.6)
    ax.set(xlim=(336, 480) if blue else (float(wave.min()), float(wave.max())),
           xlabel="Wavelength (nm)", ylabel="Flux / observed red mean")
    if blue:
        chosen = (wave >= 336) & (wave <= 480)
        bounds = np.r_[observed[chosen] - error[chosen], observed[chosen] + error[chosen],
                       prediction["lower"][chosen] / scale, prediction["upper"][chosen] / scale]
        finite = bounds[np.isfinite(bounds)]
        if finite.size:
            padding = max(float(np.ptp(finite)) * .10, .005)
            ax.set_ylim(float(finite.min()) - padding, float(finite.max()) + padding)
        ax.axvline(364.6, ls=":", color="#6f7b84", lw=.9)
        ax.text(364.6, .97, " Balmer edge", transform=ax.get_xaxis_transform(), va="top", fontsize=8, color="#53616b")
    if legend:
        ax.legend(loc="upper left", ncol=3, fontsize=7.4, frameon=True, framealpha=.92,
                  borderpad=.6, columnspacing=1, handlelength=2)
    _style_axes(ax)


def _residual(ax, prediction, contract):
    windows = np.asarray(contract["config"]["fit_windows_nm"], dtype=float)
    centers = windows.mean(axis=1)
    values = np.asarray(prediction["band_residual_sigma"])
    if len(windows) != len(values):
        raise ValueError("保存的拟合窗口与残差长度不一致")
    ax.axhline(0, color="#56646f", lw=.8)
    ax.axhspan(-1, 1, color=_BLUE, alpha=.07)
    ax.errorbar(centers, values, xerr=np.diff(windows, axis=1).ravel() / 2,
                yerr=np.ones(len(values)), fmt="o", ms=3.5, lw=1.1, color=_BLUE)
    ax.set(xlim=(336, 1020), xlabel="Fitted band center (nm)", ylabel="(Data - model) / sigma")
    _style_axes(ax)


def _positive_values(posterior):
    spt = np.asarray(posterior["positive_spt"])
    av = np.asarray(posterior["positive_av_mag"])
    red = np.asarray(posterior["positive_r_red"])
    facc = np.asarray(posterior["positive_facc_w_m2"])
    if not all(len(v) == len(spt) for v in (av, red, facc)):
        raise ValueError("正分支联合样本长度不一致")
    if not all(np.all(np.isfinite(v)) for v in (spt, av, red, facc)) or np.any(red <= 0) or np.any(facc <= 0):
        raise ValueError("正分支样本含非有限值或不可取对数的通量")
    return np.column_stack((spt, av, np.log10(red), np.log10(facc)))


def _spt_bin_edges(values):
    """规则离散节点按中点分箱，保留未抽到样本的中间节点。"""
    nodes = np.unique(np.asarray(values, dtype=float))
    if len(nodes) < 2:
        return np.histogram_bin_edges(values, bins=1)
    step = float(np.min(np.diff(nodes)))
    positions = (nodes - nodes[0]) / step
    # 连续样本或极密节点仍采用普通分箱，不把浮点舍入误差误认为积分步长。
    if len(nodes) > 512 or positions[-1] > 511 or not np.allclose(positions, np.round(positions), rtol=0, atol=1e-7):
        return np.histogram_bin_edges(values, bins=32)
    count = int(round(positions[-1])) + 1
    return nodes[0] + (np.arange(count + 1) - .5) * step


def _corner(fig, posterior, bounds, *, size=8):
    values = _positive_values(posterior)
    left, bottom, right, top = bounds
    grid = fig.add_gridspec(4, 4, left=left, bottom=bottom, right=right, top=top, wspace=.13, hspace=.13)
    labels = ["SpT number", "Av (mag)", "log10 r", "log10 Facc"]
    if not len(values):
        ax = fig.add_subplot(grid[:, :])
        ax.axis("off")
        ax.text(.5, .5, "No positive-branch samples saved", ha="center", va="center")
        return
    bins = [_spt_bin_edges(values[:, 0])] + [np.histogram_bin_edges(values[:, i], bins=32) for i in range(1, 4)]
    for i in range(4):
        for j in range(i + 1):
            ax = fig.add_subplot(grid[i, j])
            if i == j:
                ax.hist(values[:, i], bins=bins[i], color=_BLUE, alpha=.80, linewidth=0)
                ax.set_yticks([])
            else:
                ax.hist2d(values[:, j], values[:, i], bins=[bins[j], bins[i]], cmin=1, cmap="Blues")
                ax.yaxis.set_major_locator(MaxNLocator(3))
            ax.xaxis.set_major_locator(MaxNLocator(3))
            ax.tick_params(labelsize=size - 1, length=2.5)
            if i == 3:
                ax.set_xlabel(labels[j], fontsize=size)
            else:
                ax.tick_params(labelbottom=False)
            if j == 0 and i > 0:
                ax.set_ylabel(labels[i], fontsize=size)
            elif i != j:
                ax.tick_params(labelleft=False)
            ax.spines[["top", "right"]].set_visible(False)


def _identity(report):
    sid = report["source_id"]
    name = report.get("name", sid)
    release = report.get("metadata", {}).get("release", "Gaia")
    return f"{name}  |  {release} {sid}" if name != sid else f"{release} {sid}"


def _main_values(fig, report):
    entries = [("Facc  (W m$^{-2}$)", "facc_w_m2"),
               ("Optical excess r", "r_red"),
               ("Model Facc / Fstar", "q_model_facc_over_fstar"),
               ("Av  (mag)", "av_mag"), ("SpT number", "spt_num")]
    for x, (label, key) in zip(np.linspace(.06, .80, len(entries)), entries):
        fig.text(x, .887, label, fontsize=10, color="#5c6f7c")
        fig.text(x, .858, _number(_quantile(report, key, .5)), fontsize=18, weight="bold", color=_INK)
        interval = f"p16-p84: {_number(_quantile(report, key, .16))} to {_number(_quantile(report, key, .84))}"
        fig.text(x, .839, interval, fontsize=8.5, color="#5c6f7c")


def render_overview(destination, spectrum, prediction, posterior, report, contract):
    """同一组已保存数组生成总览和两个可嵌入报告的细节图。"""
    destination = Path(destination)
    styles = {"font.family":"DejaVu Sans", "font.size":10, "axes.labelcolor":_INK,
              "text.color":_INK, "axes.edgecolor":"#8997a1", "axes.titleweight":"bold",
              "savefig.facecolor":"white", "figure.facecolor":"white"}
    p0 = report.get("p_zero")
    upper = _quantile(report, "facc_w_m2", .95)
    with plt.rc_context(styles):
        fig = plt.figure(figsize=(16.54, 11.69))
        fig.text(.06, .967, _identity(report), fontsize=18, weight="bold")
        fig.text(.06, .944, "Fang+25 native XP  /  16 broad bands  /  saved model-conditional inference", fontsize=11, color="#5c6f7c")
        fig.text(.06, .918, f"Numerical integration: {report.get('numerical_status', 'not recorded')}   |   "
                 f"Physical calibration: {report.get('physical_calibration', 'not recorded').replace('_', ' ')}   |   "
                 f"P0 = {_number(p0)}   |   ln BF = {_number(report.get('ln_bayes_factor'))}", fontsize=10)
        _main_values(fig, report)
        full = fig.add_axes((.06, .545, .48, .235))
        blue = fig.add_axes((.06, .29, .48, .185))
        residual = fig.add_axes((.06, .105, .48, .115))
        _spectrum(full, spectrum, prediction, legend=True)
        _spectrum(blue, spectrum, prediction, blue=True)
        _residual(residual, prediction, contract)
        full.set_title("A  Full XP spectrum", loc="left", fontsize=11, pad=10)
        blue.set_title("B  Blue continuum", loc="left", fontsize=11, pad=10)
        residual.set_title("C  Correlated band residuals", loc="left", fontsize=11, pad=10)
        fig.text(.635, .796, "D  Conditional positive-branch posterior", fontsize=11, weight="bold")
        fig.text(.635, .773, f"P0 is excluded from these log panels; mixed Facc p95 = {_number(upper)} W m$^{{-2}}$", fontsize=9)
        _corner(fig, posterior, (.635, .16, .965, .74), size=8)
        fig.text(.635, .11, "SpT numbering: K0 = 60, M0 = 70.  Facc units: W m$^{-2}$.", fontsize=9)
        luminosities = "   |   ".join(f"{label}: {_number(_quantile(report, key, .5))}"
                                      for label, key in [("Lacc (Lsun)", "lacc_lsun"), ("Mdot (Msun/yr)", "mdot_msun_yr")])
        fig.text(.635, .086, luminosities, fontsize=9)
        flags = report.get("diagnostic_flags", [])
        flag_text = ", ".join(flags) if flags else "none listed; this is not a reliability certificate"
        fig.text(.06, .055, textwrap.fill("Diagnostic flags: " + flag_text, width=170), fontsize=9, va="top")
        fig.text(.06, .018, "Reported intervals include the zero branch. Residual errors are marginal and correlated, not independent chi-square. "
                 "Component medians need not sum to the total median.", fontsize=8.5, color="#5c6f7c")
        fig.savefig(destination / "overview.png", dpi=180)
        plt.close(fig)

        fig = plt.figure(figsize=(12, 10))
        grid = fig.add_gridspec(3, 1, left=.10, right=.97, bottom=.09, top=.89, hspace=.58, height_ratios=[1.3, 1.1, .65])
        axes = [fig.add_subplot(grid[i]) for i in range(3)]
        _spectrum(axes[0], spectrum, prediction, legend=True)
        _spectrum(axes[1], spectrum, prediction, blue=True)
        _residual(axes[2], prediction, contract)
        for ax, title in zip(axes, ["Full XP spectrum", "Blue continuum", "Correlated band residuals"]):
            ax.set_title(title, loc="left", fontsize=11)
        fig.suptitle(_identity(report), fontsize=14, y=.97)
        fig.text(.10, .93, "Saved prediction p16-p84; flux normalized to the observed 700-900 nm mean", fontsize=10, color="#5c6f7c")
        fig.text(.10, .025, "Marginal errors are correlated; residuals are not independent chi-square. Component medians need not sum.", fontsize=9)
        fig.savefig(destination / "spectrum.png", dpi=160)
        plt.close(fig)

        fig = plt.figure(figsize=(10, 9))
        fig.suptitle(_identity(report), fontsize=13, y=.97)
        fig.text(.10, .93, f"Conditional positive-branch posterior  |  P0 = {_number(p0)} is excluded", fontsize=11)
        fig.text(.10, .90, f"Mixed Facc posterior p95: {_number(upper)} W m$^{{-2}}$; not a calibrated detection threshold", fontsize=10)
        _corner(fig, posterior, (.10, .12, .97, .86), size=10)
        fig.text(.10, .025, "SpT: K0 = 60, M0 = 70.  r: observed red excess ratio.  Facc: W m$^{-2}$, integrated over 50-2477.47 nm.", fontsize=9)
        fig.savefig(destination / "posterior.png", dpi=160)
        plt.close(fig)
    return {"overview":"overview.png", "spectrum":"spectrum.png", "posterior":"posterior.png"}
