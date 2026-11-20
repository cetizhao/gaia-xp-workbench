"""单条XP光谱的输入检查、Fang拟合及保存结果解读；不修改历史批次。"""

from __future__ import annotations

import copy

import csv

import hashlib

import json

import math

import re

import time

from dataclasses import dataclass

from pathlib import Path

import numpy as np

from gaia_accretion.assets import asset_path
from gaia_accretion import __version__
from gaia_accretion.report_language import (
    FIXED_DISTANCE, FIXED_STELLAR, METRIC_LABELS, MODEL_LIMITS, NO_DISTANCE, PRIOR_NOTE, english_note,
)

PROFILE = "fang25_broad16_single_v1"

LEVELS = [.16, .5, .84, .95]

LIMITS = MODEL_LIMITS

def read_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))

def write_json(path, value):
    Path(path).write_text(json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False) + "\n", encoding="utf-8")

def digest(path):
    with Path(path).open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()

def exact_id(value):
    if not isinstance(value, str) or not re.fullmatch(r"[1-9][0-9]{0,18}", value):
        raise ValueError("source_id必须是精确十进制字符串，不能由浮点数或科学计数法恢复")
    return value

def new_directory(path):
    """输出仅创建新目录，不覆盖已有运行或安装的程序。"""
    path = Path(path).expanduser().resolve()
    package = Path(__file__).resolve().parents[1]
    if path.is_relative_to(package):
        raise ValueError("输出目录不能位于安装的Python包内")
    path.mkdir(parents=True, exist_ok=False)
    return path

def profile():
    """默认配置随安装包发布，与研究项目历史目录无关。"""
    path = Path(__file__).resolve().parents[1]/"resources"/"profile.json"
    return copy.deepcopy(read_json(path)), path

@dataclass
class Spectrum:
    wave: np.ndarray
    flux: np.ndarray
    mask: np.ndarray
    factor: np.ndarray
    metadata: dict
    files: list[Path]

    @property
    def error(self):
        return np.linalg.norm(self.factor, axis=1)

def validate_spectrum(wave, flux, mask, factor, metadata, files=()):
    """保留负通量；掩码内的非有限值不能进入线性投影。"""
    meta = copy.deepcopy(metadata)
    exact_id(meta.get("source_id"))
    for key in ("release", "product", "calibration", "calibration_version", "input_reference", "prior_reference"):
        if not isinstance(meta.get(key), str) or not meta[key].strip():
            raise ValueError(f"元数据缺少{key}")
    if meta.get("wavelength_unit") != "nm" or meta.get("flux_unit") != "W m-2 nm-1":
        raise ValueError("本入口要求波长nm、通量密度W m-2 nm-1；转换时须同步传播协方差")
    for key in ("spt_num", "av_mag", "teff_k"):
        if isinstance(meta.get(key), bool) or not isinstance(meta.get(key), (int, float)) or not math.isfinite(meta[key]):
            raise ValueError(f"元数据{key}必须是有限数值")
    if meta["av_mag"] < 0 or meta["teff_k"] <= 0:
        raise ValueError("Av必须非负，Teff必须为正")
    stellar = meta.get("stellar_parameters")
    if stellar is not None:
        if not isinstance(stellar, dict) or not isinstance(stellar.get("reference"), str) or not stellar["reference"].strip():
            raise ValueError("恒星参数必须记录reference来源")
        for key in ("distance_pc", "mass_msun", "radius_rsun"):
            if key in stellar and (isinstance(stellar[key], bool) or not isinstance(stellar[key], (int, float)) or not math.isfinite(stellar[key]) or stellar[key] <= 0):
                raise ValueError(f"恒星参数{key}必须为正的有限数值")
        if "distance_pc" not in stellar or ("mass_msun" in stellar) != ("radius_rsun" in stellar):
            raise ValueError("光度换算需要距离；吸积率换算需要同时提供质量和半径")
    w, f, b = np.asarray(wave, float), np.asarray(flux, float), np.asarray(factor, float)
    m = np.asarray(mask)
    if w.ndim != 1 or f.shape != w.shape or m.shape != w.shape or m.dtype.kind != "b":
        raise ValueError("wave、flux和布尔mask须为等长一维数组")
    if len(w) < 2 or not np.isfinite(w).all() or np.any(np.diff(w) <= 0):
        raise ValueError("波长必须有限且严格递增")
    if b.ndim != 2 or b.shape[0] != len(w) or not b.shape[1] or not np.isfinite(b).all():
        raise ValueError("noise_factor须为有限的[n_wave,n_factor]矩阵，C=B B^T")
    if not m.any() or not np.isfinite(f[m]).all() or np.any(np.linalg.norm(b[m], axis=1) <= 0):
        raise ValueError("有效波长处的通量须有限，边缘误差须为正")
    return Spectrum(w, np.where(m, f, 0.), m, b, meta, [Path(p).resolve() for p in files])

def load_input(input_path, metadata_path):
    meta = read_json(metadata_path)
    with np.load(input_path, allow_pickle=False) as z:
        if "source_id" not in z or z["source_id"].shape != () or z["source_id"].dtype.kind != "U":
            raise ValueError("单谱NPZ的source_id须为Unicode字符串标量")
        if z["source_id"].item() != exact_id(meta.get("source_id")):
            raise ValueError("NPZ和JSON的source_id不一致")
        if ("noise_factor" in z) == ("covariance" in z):
            raise ValueError("必须且只能提供noise_factor或完整covariance，不能仅给逐点error")
        if "noise_factor" in z:
            factor = z["noise_factor"]
        else:
            covariance = np.asarray(z["covariance"], float)
            n = len(z["wave"])
            if covariance.shape != (n, n) or not np.isfinite(covariance).all():
                raise ValueError("covariance必须是有限的[n_wave,n_wave]矩阵")
            scale = np.max(np.abs(covariance))
            if scale <= 0 or not np.allclose(covariance, covariance.T, rtol=1e-8, atol=scale*1e-10):
                raise ValueError("covariance必须非零且对称")
            values, vectors = np.linalg.eigh((covariance + covariance.T)/2)
            if values.min() < -scale*1e-8:
                raise ValueError("covariance不是半正定矩阵")
            factor = vectors * np.sqrt(np.maximum(values, 0))
        mask = z["mask"] if "mask" in z else np.ones(len(z["wave"]), bool)
        result = validate_spectrum(z["wave"], z["flux"], mask, factor, meta, [input_path, metadata_path])
        if "error" in z and not np.allclose(z["error"][mask], result.error[mask], rtol=1e-6, atol=0):
            raise ValueError("error与协方差的边缘误差不一致")
    return result

def inspect(spectrum):
    from .fang_xp_broad import broad_projection, BROAD_WINDOWS
    s, meta = spectrum, spectrum.metadata
    blockers, notes, bands = [], [], []
    if (meta["release"], meta["product"], meta["calibration"]) != ("Gaia DR3", "mean_xp", "externally_calibrated"):
        blockers.append("The fit requires externally calibrated Gaia DR3 mean XP spectra.")
    if not np.array_equal(s.wave, np.arange(336., 1021., 2.)):
        blockers.append("The Fang model requires a 336–1020 nm grid sampled every 2 nm.")
    if not 60 <= meta["spt_num"] <= 78:
        blockers.append("The supported range of spectral types is K0–M8.")
    if meta["spt_num"] + 2 > 78:
        notes.append("The spectral-type prior is truncated at the M8 template boundary.")
    try:
        projection = broad_projection(s.wave, s.mask)
        for i, bounds in enumerate([(700., 900.), *BROAD_WINDOWS]):
            p = projection[:, i]
            value, error = float(p@s.flux), float(np.linalg.norm(p@s.factor))
            if error <= 0:
                blockers.append(f"The propagated uncertainty is zero in the {bounds[0]:g}–{bounds[1]:g} nm band.")
                continue
            bands.append(dict(lower_nm=bounds[0], upper_nm=bounds[1], flux=value, error=error, snr=value/error))
        if bands and bands[0]["snr"] < 5:
            blockers.append("The red-band signal-to-noise ratio falls below the required threshold of 5.")
        if len(bands) > 1 and bands[1]["snr"] < 3:
            notes.append("The blue continuum has a signal-to-noise ratio below 3. This ratio refers to the total continuum.")
    except ValueError as error:
        blockers.append(str(error))
    notes.append("Use archive flags and external observations to assess blending, neighbours, chromospheric emission and blue-end calibration.")
    return dict(source_id=meta["source_id"], metadata=meta, profile=PROFILE,
                ready_for_fit=not blockers, blockers=blockers, notes=notes,
                valid_wavelengths=int(s.mask.sum()), negative_valid_fluxes=int(np.sum(s.flux[s.mask] < 0)),
                bands=bands, band_flux_unit="W m-2 nm-1", limits=LIMITS)

def _backend():
    from .fang_xp_broad import FangXPBroadModel
    from gaia_accretion.workflows.inference import infer_supported
    return FangXPBroadModel, infer_supported

def fit(spectrum, output, seed=20260930):
    from threadpoolctl import threadpool_limits
    check = inspect(spectrum)
    if not check["ready_for_fit"]:
        raise ValueError("；".join(check["blockers"]))
    cfg, cfg_path = profile()
    model_class, infer = _backend()
    meta = spectrum.metadata
    support = [max(22., meta["spt_num"]-2), min(78., meta["spt_num"]+2)]
    package = Path(__file__).resolve().parents[1]
    code = sorted(package.rglob("*.py"))
    assets = [asset_path(key) for key in ("fang_template", "bc_table", "temperature_table")]
    assets += sorted(asset_path("slab_grid").glob("*.out"))
    contract = dict(package_version=__version__, profile=PROFILE, config=cfg, metadata=meta, spt_sigma=.5, spt_support=support,
                    seed=int(seed), posterior_draws=8000, source_config=str(cfg_path),
                    files={str(p):digest(p) for p in [*spectrum.files, cfg_path, *code, *assets]},
                    numeric_policy="one process; two grid workers; BLAS one thread", limits=LIMITS)
    destination = new_directory(output)
    write_json(destination/"run_contract.json", contract)
    write_json(destination/"inspection.json", check)
    write_json(destination/"metadata.json", meta)
    np.savez_compressed(destination/"spectrum.npz", source_id=np.array(meta["source_id"]), wave=spectrum.wave,
                        flux=spectrum.flux, mask=spectrum.mask, noise_factor=spectrum.factor)
    started = time.monotonic()
    write_json(destination/"status.json", dict(status="running", source_id=meta["source_id"]))
    try:
        # 运行期显式限制BLAS线程；积分器仅使用两个工作线程。
        with threadpool_limits(limits=1):
            model = model_class(spectrum.wave, cfg, valid_mask=spectrum.mask)
            projected = model.projection.T@spectrum.factor
            covariance = projected@projected.T
            anchor = model.make_context(spectrum.flux, covariance, meta["spt_num"], meta["av_mag"], teff=meta["teff_k"])
            result = infer(model, anchor, meta["spt_num"], destination, int(seed), support)
            result.update(source_id=meta["source_id"], name=meta.get("name", meta["source_id"]),
                          method_id=PROFILE, center_spt=meta["spt_num"], base_av=meta["av_mag"],
                          spt_support=support, elapsed_seconds=time.monotonic()-started,
                          run_contract_sha256=digest(destination/"run_contract.json"))
            write_json(destination/"summary.json", result)
            with np.load(destination/"posterior.npz", allow_pickle=False) as z:
                post = dict(z)
            prediction = make_prediction(model, anchor, spectrum, post)
            np.savez_compressed(destination/"prediction.npz", **prediction)
            report = describe_result(result, spectrum.metadata, post, prediction, check)
            write_json(destination/"review.json", report)
            write_report(destination/"report.md", report, figures=True)
            plot_result(destination, spectrum, post, prediction, result)
        write_json(destination/"status.json", dict(status="complete", source_id=meta["source_id"], elapsed_seconds=time.monotonic()-started,
                   artifact_hashes={name:digest(destination/name) for name in ("summary.json", "review.json")}))
    except Exception as error:
        write_json(destination/"status.json", dict(status="failed", source_id=meta["source_id"], error=str(error)))
        raise
    return dict(status="complete", source_id=meta["source_id"], output=str(destination), report=str(destination/"report.md"))

def make_prediction(model, anchor, spectrum, post):
    from dataclasses import replace
    indices = np.linspace(0, len(post["spt"])-1, min(160, len(post["spt"])), dtype=int)
    components = np.asarray([model.spectrum(replace(anchor, spt=float(post["spt"][k])), post["theta"][k], int(post["shape_index"][k])) for k in indices])
    total = components.sum(axis=1)
    lower, median, upper = np.quantile(total, [.16, .5, .84], axis=0)
    photo, slab = np.median(components, axis=0)
    p = model.projection[:, model.indices]
    observed = spectrum.flux@p
    predicted = np.median(total@p, axis=0)
    band_error = np.linalg.norm(p.T@spectrum.factor, axis=1)
    selected = (spectrum.wave >= 600) & (spectrum.wave <= 950) & spectrum.mask & (spectrum.flux > 0)
    red_residual = float(np.median(np.abs(spectrum.flux[selected]-median[selected])/spectrum.flux[selected]))
    return dict(lower=lower, median=median, upper=upper, photo=photo, slab=slab,
                band_observed=observed, band_predicted=predicted, band_error=band_error,
                band_residual_sigma=(observed-predicted)/band_error, red_fractional_residual=red_residual)

def describe_result(summary, metadata, post=None, prediction=None, inspection=None):
    """分别记录数值检查、适用性诊断和标定限制，不产生统一可信分数。"""
    checks = summary.get("checks", [])
    last = checks[-1] if checks else {}
    numerical = "not_recorded"
    if checks:
        numerical = "passed" if (last.get("maximum_branch_logz_change", math.inf) < .05
                                  and last.get("mean_spt_change", math.inf) < .02
                                  and last.get("max_r_av_logz_change", math.inf) < .05) else "failed"
    metrics, flags = {}, []
    if post is not None:
        support = summary["spt_support"]
        metrics = dict(p_spt_edge=float(np.mean((post["spt"] < support[0]+.25) | (post["spt"] > support[1]-.25))),
                       p_av_upper=float(np.mean(post["positive_av_mag"] > summary["base_av"]+.55)),
                       p_r_upper=float(np.mean(post["positive_r_red"] > 3/10**.1)))
        flags.extend(name for key, name in [("p_spt_edge", "spt_support_boundary"), ("p_av_upper", "av_upper_boundary"), ("p_r_upper", "r_upper_boundary")] if metrics[key] > .1)
    if prediction is not None:
        metrics["max_abs_band_residual_sigma"] = float(np.max(np.abs(prediction["band_residual_sigma"])))
        metrics["red_residual"] = float(prediction["red_fractional_residual"])
        if metrics["red_residual"] > .1:
            flags.append("red_residual_gt_0.1")
    if inspection and len(inspection["bands"]) > 1:
        metrics["blue_continuum_snr"] = inspection["bands"][1]["snr"]
        if metrics["blue_continuum_snr"] < 3:
            flags.append("blue_snr_below_3")
    quantities = dict(summary.get("physical_quantiles", {}))
    quantities["q_model_facc_over_fstar"] = summary.get("q_quantiles")
    quantities["spt_num"] = summary.get("spt_quantiles")
    conversion_note = NO_DISTANCE
    if post is not None and metadata.get("stellar_parameters"):
        from .luminosity_boundary import zero_mixture_quantiles
        stellar = metadata["stellar_parameters"]
        lacc = post["positive_facc_w_m2"] * (4*np.pi*(stellar["distance_pc"]*3.085677581491367e16)**2/3.828e26)
        quantities["lacc_lsun"] = zero_mixture_quantiles(lacc, summary["p_zero"]).tolist()
        conversion_note = FIXED_DISTANCE
        if "mass_msun" in stellar:
            conversion = 1.25*3.828e26*(stellar["radius_rsun"]*6.957e8)/(6.67430e-11*stellar["mass_msun"]*1.98847e30)*31557600/1.98847e30
            quantities["mdot_msun_yr"] = zero_mixture_quantiles(lacc*conversion, summary["p_zero"]).tolist()
            conversion_note = FIXED_STELLAR
        if stellar.get("catalogue_flag", "good") != "good":
            flags.append("stellar_parameters_"+stellar["catalogue_flag"])
    known_prior, prior_note, artifacts = [], PRIOR_NOTE, {}
    return dict(source_id=exact_id(summary["source_id"]), name=summary.get("name", summary["source_id"]),
                method_id=summary.get("method_id"), metadata=metadata, numerical_status=numerical,
                numerical_checks=checks, p_zero=summary.get("p_zero"),
                ln_bayes_factor=summary.get("log_bayes_factor_positive_over_zero"),
                quantile_levels=LEVELS, quantities=quantities, diagnostic_flags=flags, diagnostic_metrics=metrics,
                applicability="requires_review" if flags else "no_listed_flags_not_certified",
                physical_calibration="not_established", prior_sensitivity=known_prior, prior_note=prior_note,
                stellar_conversion=conversion_note,
                artifacts=artifacts, limits=LIMITS)

def review(run):
    folder = Path(run).resolve()
    status = read_json(folder/"status.json")
    if status.get("status") != "complete":
        raise ValueError(f"该运行尚未成功完成：{status.get('status')}")
    for name in ("summary.json", "review.json"):
        if digest(folder/name) != status.get("artifact_hashes", {}).get(name):
            raise ValueError(f"保存的{name}与完成记录不一致")
    summary = read_json(folder/"summary.json")
    if digest(folder/"posterior.npz") != summary["posterior_sha256"] or digest(folder/"run_contract.json") != summary["run_contract_sha256"]:
        raise ValueError("后验或契约与保存的SHA256不符")
    report = read_json(folder/"review.json")
    # 读取后翻译固定方法说明；原文件和自由填写的来源字段保留原文。
    for field in ("prior_note", "stellar_conversion"):
        report[field] = english_note(report[field], fallback=report[field])
    report["limits"] = [english_note(note, fallback=note) for note in report["limits"]]
    report["artifacts"] = {"spectrum":str(folder/"spectrum_fit.png"), "corner":str(folder/"corner_positive.png")}
    return report

def write_report(path, report, figures=False):
    """给出可独立阅读的简短解释，未测的物理量不补成数字。"""
    quantities = {
        "facc_w_m2": ("Accretion flux, Facc", "W m⁻²"),
        "r_red": ("Red optical excess, r", "dimensionless"),
        "av_mag": ("Visual extinction, Av", "mag"),
        "fstar_bol_w_m2": ("Model photospheric flux, Fstar", "W m⁻²"),
        "q_model_facc_over_fstar": ("Model luminosity ratio, Facc/Fstar", "dimensionless"),
        "spt_num": ("Spectral type", "K0 = 60, M0 = 70"),
        "lacc_lsun": ("Accretion luminosity, Lacc", "L☉"),
        "mdot_msun_yr": ("Mass accretion rate, Mdot", "M☉ yr⁻¹"),
    }
    metadata = report["metadata"]
    product = "mean XP spectrum" if metadata["product"] == "mean_xp" else metadata["product"]
    lines = [
        f"# {report['name']} — XP continuum fit", "",
        f"Gaia source `{report['source_id']}` · {metadata['release']} {product} · `{report['method_id']}`",
        "", "## Inferred properties", "",
        "The table gives posterior percentiles. Facc, r and Facc/Fstar include the zero-accretion branch. "
        "Spectral type and extinction are marginalized over the joint posterior.", "",
        "| Quantity | Unit or scale | p16 | p50 | p84 | p95 |", "|---|---|---:|---:|---:|---:|",
    ]
    for key, values in report["quantities"].items():
        if values is not None:
            label, unit = quantities.get(key, (key, ""))
            lines.append(f"| {label} | {unit} | " + " | ".join(f"{v:.5g}" for v in values) + " |")
    flags = ", ".join(english_note(flag) for flag in report["diagnostic_flags"]) or "none triggered"
    lines.extend([
        "", f"The zero-accretion branch has posterior weight P0 = {report['p_zero']:.6g}. "
        f"The log Bayes factor for a positive excess relative to zero is {report['ln_bayes_factor']:.6g}. "
        "Both depend on the adopted model and priors.",
        "", english_note(report["stellar_conversion"]), "", "## Diagnostics", "",
        f"Numerical integration checks **{report['numerical_status'].replace('_', ' ')}**. "
        "These checks track changes in the integrated evidence and mean spectral type.",
        f"Model applicability flags: {flags}.", "",
        "| Diagnostic | Value |", "|---|---:|",
    ])
    for key, value in report["diagnostic_metrics"].items():
        cell = "Unavailable" if value is None else f"{value:.5g}"
        lines.append(f"| {METRIC_LABELS.get(key, key)} | {cell} |")
    lines.extend([
        "", "Band residuals use marginal uncertainties. Correlations between bands affect any goodness-of-fit statistic.",
        "", english_note(report["prior_note"]), "", "## Fit and posterior", "",
        "The spectrum figure shows the full fit, the blue photospheric and slab continua, and the band residuals. "
        "Each component has its own pointwise median. The corner plot shows parameter correlations conditional on positive excess.",
        "",
    ])
    artifacts = {"spectrum":"spectrum_fit.png", "corner":"corner_positive.png"} if figures else report["artifacts"]
    lines.extend(f"- [{key.capitalize()}]({Path(value).as_posix()})" for key, value in artifacts.items())
    lines.extend(["", "## Interpretation", "", *(f"- {english_note(note)}" for note in report["limits"]), ""])
    Path(path).write_text("\n".join(lines), encoding="utf-8")

def summarize(reports, output):
    """按明确选定的结果汇总；同星多次结果不当成新增恒星。"""
    if not reports:
        raise ValueError("请明确指定至少一个运行目录")
    destination = new_directory(output)
    fields = ["source_id", "method_id", "numerical_status", "p_zero", "ln_bayes_factor", "applicability", "diagnostic_flags"]
    fields += [f"{q}_p{int(p*100)}" for q in ["facc_w_m2", "r_red", "q_model_facc_over_fstar", "lacc_lsun", "mdot_msun_yr"] for p in LEVELS]
    with (destination/"catalogue.csv").open("x", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields); writer.writeheader()
        for r in reports:
            row = {k:r[k] for k in fields[:7]}
            row["diagnostic_flags"] = ";".join(row["diagnostic_flags"])
            for q, values in r["quantities"].items():
                if values is not None:
                    row.update({f"{q}_p{int(p*100)}":v for p,v in zip(LEVELS, values) if f"{q}_p{int(p*100)}" in fields})
            writer.writerow(row)
    result = dict(result_count=len(reports), independent_stars=len({r['source_id'] for r in reports}),
                  records=reports, note="Each run retains its own posterior summary and upper limits. Import the CSV source IDs as text to preserve their full precision.")
    write_json(destination/"catalogue.json", result)
    (destination/"README.md").write_text(
        f"# Gaia XP fit catalogue\n\n{len(reports)} saved run(s) for {result['independent_stars']} distinct star(s).\n\n"
        f"{result['note']} See [catalogue.csv](catalogue.csv) for the table and [catalogue.json](catalogue.json) for the full records.\n",
        encoding="utf-8",
    )
    return dict(output=str(destination), result_count=result["result_count"], independent_stars=result["independent_stars"])

def plot_result(destination, spectrum, post, prediction, summary):
    from .xp_workbench_plots import plot_result as render
    render(destination, spectrum, post, prediction, summary)
