"""单谱拟合图与条件正分支后验图；图示抽样不改变保存的科学分位数。"""
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

from .fang_xp_broad import BROAD_WINDOWS


def plot_result(destination, spectrum, post, prediction, summary):
    destination = Path(destination)
    wave, flux, error = spectrum.wave, spectrum.flux, spectrum.error
    red = (wave >= 700) & (wave <= 900) & spectrum.mask
    unit = flux[red].mean()
    fig = plt.figure(figsize=(11, 8))
    layout = fig.add_gridspec(3, 2, height_ratios=[1.25, 1, .75])
    full = fig.add_subplot(layout[0, :])
    blue = fig.add_subplot(layout[1, 0])
    density = fig.add_subplot(layout[1, 1])
    residual = fig.add_subplot(layout[2, :])
    observed = np.where(spectrum.mask, flux/unit, np.nan)
    errors = np.where(spectrum.mask, error/unit, np.nan)
    for ax in (full, blue):
        ax.fill_between(wave, observed-errors, observed+errors, color=".85", label="XP marginal 1 sigma")
        ax.plot(wave, observed, color=".25", lw=.8, label="DR3 mean XP")
        ax.fill_between(wave, prediction["lower"]/unit, prediction["upper"]/unit, color="#267cae", alpha=.22)
        ax.plot(wave, prediction["median"]/unit, color="#267cae", label="Total median; band: 16-84%")
        ax.plot(wave, prediction["photo"]/unit, "--", color="#b56b27", label="Photosphere median")
        ax.plot(wave, prediction["slab"]/unit, "--", color="#99559a", label="Slab median")
        ax.axhline(0, color=".6", lw=.5)
        ax.set(xlabel="Wavelength (nm)", ylabel="Flux / observed 700-900 nm mean")
    full.set_xlim(336, 1000)
    full.legend(fontsize=8, ncol=3, loc="upper left")
    blue.set_xlim(336, 480)
    selected = (wave >= 336) & (wave <= 480) & spectrum.mask
    bounds = np.r_[observed[selected]-errors[selected], observed[selected]+errors[selected],
                   prediction["lower"][selected]/unit, prediction["upper"][selected]/unit]
    pad = max(float(np.ptp(bounds))*.08, .005)
    blue.set_ylim(float(bounds.min())-pad, float(bounds.max())+pad)
    blue.axvline(364.6, color=".45", ls=":", lw=.8)
    blue.set_title("Blue continuum and Balmer edge", fontsize=10)
    density.hist(np.log10(post["positive_facc_w_m2"]), bins=35, density=True, color="#267cae", alpha=.75)
    upper = summary["physical_quantiles"]["facc_w_m2"][-1]
    if upper > 0:
        density.axvline(np.log10(upper), color="#ad4d31", ls="--", label="Mixture p95")
        density.legend(fontsize=8)
    density.set(xlabel="log10 Facc (W m$^{-2}$)", ylabel="Positive-branch density",
                title=f"P0 = {summary['p_zero']:.4g}; zero mass shown separately")
    centers = np.mean(BROAD_WINDOWS, axis=1)
    residual.axhline(0, color=".3", lw=.8)
    residual.errorbar(centers, prediction["band_residual_sigma"], yerr=np.ones(len(centers)),
                      xerr=np.diff(BROAD_WINDOWS, axis=1).ravel()/2, fmt="o", ms=3, color="#267cae")
    residual.set(xlabel="Fitted band center (nm)", ylabel="(Data - model) / sigma",
                 title="Correlated band residuals; marginal noise only, not independent chi-square", xlim=(336, 1000))
    for ax in (full, blue, density, residual):
        ax.spines[["top", "right"]].set_visible(False)
        ax.tick_params(labelsize=8)
    fig.suptitle(f"{summary['name']} | Gaia DR3 {summary['source_id']}\nFang+25 / 16 broad bands; model-conditional inference", fontsize=11)
    fig.tight_layout(rect=(0, 0, 1, .94))
    fig.savefig(destination/"spectrum_fit.png", dpi=160)
    plt.close(fig)

    values = np.c_[post["positive_spt"], post["positive_av_mag"], np.log10(post["positive_r_red"]), np.log10(post["positive_facc_w_m2"])]
    labels = ["SpT (K0=60, M0=70)", "Av (mag)", "log10 r (700-900 nm)", "log10 Facc (W m$^{-2}$)"]
    fig, axes = plt.subplots(4, 4, figsize=(10, 9))
    for i in range(4):
        for j in range(4):
            ax = axes[i, j]
            if j > i:
                ax.set_visible(False)
                continue
            if i == j:
                ax.hist(values[:, i], bins=32, color="#267cae", alpha=.8)
                for value in np.quantile(values[:, i], [.16, .5, .84]):
                    ax.axvline(value, color=".3", ls="--", lw=.7)
                ax.set_yticks([])
            else:
                ax.hist2d(values[:, j], values[:, i], bins=32, cmin=1, cmap="Blues")
            if i == 3:
                ax.set_xlabel(labels[j], fontsize=9)
            else:
                ax.tick_params(labelbottom=False)
            if j == 0 and i > 0:
                ax.set_ylabel(labels[i], fontsize=9)
            elif i != j:
                ax.tick_params(labelleft=False)
            ax.tick_params(labelsize=8)
    fig.suptitle(f"{summary['name']} | conditional positive-excess posterior\nP0 = {summary['p_zero']:.4g} is excluded from these panels; not a detection certificate", fontsize=11)
    fig.tight_layout(rect=(0, 0, 1, .94))
    fig.savefig(destination/"corner_positive.png", dpi=150)
    plt.close(fig)
