"""Fang 原生 XP 模板、节点选择、插值和 CCM89 消光。"""
from __future__ import annotations
from pathlib import Path
import extinction
import numpy as np
from scipy.io import readsav
from gaia_accretion.assets import asset_path

EXPECTED_TEMPLATE_NODES = 113

EXPECTED_WAVELENGTH_POINTS = 343

REQUIRED_TEMPLATE_FIELDS = {
    "SPT",
    "SPTNUM",
    "LAM",
    "FLUX",
    "NUM",
    "FLAG",
}

TEMPLATE_NODE_FIELDS = (
    "spt_label",
    "spt_num",
    "flux",
    "num",
    "flag",
)

SUPPORTED_TEMPLATE_POLICIES = (
    "num_positive",
    "all_113",
)

DEFAULT_RV = 3.1

def _decode_spt_label(value: object) -> str:
    """把 IDL SAV 中可能出现的 bytes/字符串标签统一成 Python 字符串。"""
    if isinstance(value, bytes):
        return value.decode("utf-8", errors="replace").strip()
    return str(value).strip()

def load_template_grid(
    path: str | Path | None = None,
) -> dict[str, np.ndarray]:
    """读取 113×343 模板网格，并显式统一波长单位。

    返回的 ``wavelength_angstrom`` 保留 SAV 原始单位；后续与 Gaia XP
    比较时应使用 ``wavelength_nm``。``num`` 是原始构造字段，目前只用于
    provenance/policy 分层，不能当作独立恒星数量或统计权重。
    """
    path = asset_path("fang_template") if path is None else Path(path)
    if not path.is_file():
        raise FileNotFoundError(f"找不到 Fang 模板：{path}")

    sav = readsav(str(path), python_dict=True)
    if "gaia_template" not in sav:
        raise ValueError("Fang SAV 缺少 gaia_template 结构")

    records = sav["gaia_template"]
    field_names = set(records.dtype.names or ())
    missing_fields = sorted(REQUIRED_TEMPLATE_FIELDS - field_names)
    if missing_fields:
        raise ValueError(
            "gaia_template 缺少字段："
            f"{', '.join(missing_fields)}"
        )

    spt_label = np.asarray(
        [_decode_spt_label(value) for value in records["SPT"]]
    )
    spt_num = np.asarray(records["SPTNUM"], dtype=np.float64)
    wavelength_rows_angstrom = np.stack(
        [np.asarray(value, dtype=np.float64) for value in records["LAM"]]
    )
    flux = np.stack(
        [np.asarray(value, dtype=np.float64) for value in records["FLUX"]]
    )
    num = np.asarray(records["NUM"], dtype=np.int64)
    flag = np.asarray(records["FLAG"], dtype=np.int64)

    expected_shape = (
        EXPECTED_TEMPLATE_NODES,
        EXPECTED_WAVELENGTH_POINTS,
    )
    if wavelength_rows_angstrom.shape != expected_shape:
        raise ValueError(
            "模板波长数组形状错误："
            f"预期 {expected_shape}，实际 {wavelength_rows_angstrom.shape}"
        )
    if flux.shape != expected_shape:
        raise ValueError(
            f"模板 flux 形状错误：预期 {expected_shape}，实际 {flux.shape}"
        )
    if not np.array_equal(
        wavelength_rows_angstrom,
        np.broadcast_to(
            wavelength_rows_angstrom[0],
            wavelength_rows_angstrom.shape,
        ),
    ):
        raise ValueError("113 个模板节点没有使用完全相同的波长网格")

    wavelength_angstrom = wavelength_rows_angstrom[0]
    wavelength_nm = wavelength_angstrom / 10.0

    if not np.all(np.diff(wavelength_angstrom) > 0):
        raise ValueError("模板波长网格必须严格递增")
    if not np.all(np.diff(spt_num) > 0):
        raise ValueError("模板 SPTNUM 网格必须严格递增")
    if not np.isfinite(wavelength_angstrom).all():
        raise ValueError("模板波长包含非有限值")
    if not np.isfinite(flux).all():
        raise ValueError("模板 flux 包含非有限值")
    if not np.all((num == -1) | (num > 0)):
        raise ValueError("模板 NUM 必须为 -1 或正整数")

    return {
        "spt_label": spt_label,
        "spt_num": spt_num,
        "wavelength_angstrom": wavelength_angstrom,
        "wavelength_nm": wavelength_nm,
        "flux": flux,
        "num": num,
        "flag": flag,
    }

def select_template_nodes(
    grid: dict[str, np.ndarray],
    policy: str = "num_positive",
) -> dict[str, np.ndarray | str | int]:
    """按预注册策略选择模板节点，同时保留原始节点索引。

    本工作台配置显式采用 ``all_113``；``num_positive`` 保留为读取能力，
    不改变默认模型。两种策略都不能把节点解释成相互独立的恒星。
    """
    if policy not in SUPPORTED_TEMPLATE_POLICIES:
        supported = ", ".join(SUPPORTED_TEMPLATE_POLICIES)
        raise ValueError(
            f"未知 template policy：{policy}；可选值为 {supported}"
        )

    required_keys = {
        *TEMPLATE_NODE_FIELDS,
        "wavelength_angstrom",
        "wavelength_nm",
    }
    missing_keys = sorted(required_keys - set(grid))
    if missing_keys:
        raise ValueError(
            "template grid 缺少字段："
            f"{', '.join(missing_keys)}"
        )

    source_node_count = len(grid["spt_num"])
    for field in TEMPLATE_NODE_FIELDS:
        if len(grid[field]) != source_node_count:
            raise ValueError(
                f"模板字段 {field} 的节点数与 spt_num 不一致"
            )

    if policy == "num_positive":
        selection_mask = np.asarray(grid["num"]) > 0
    else:
        selection_mask = np.ones(source_node_count, dtype=bool)

    selected_node_indices = np.flatnonzero(selection_mask)
    if len(selected_node_indices) < 2:
        raise ValueError("template policy 至少需要保留两个节点")

    selected: dict[str, np.ndarray | str | int] = {
        "policy": policy,
        "source_node_count": source_node_count,
        "selected_node_indices": selected_node_indices,
        "wavelength_angstrom": np.asarray(
            grid["wavelength_angstrom"]
        ).copy(),
        "wavelength_nm": np.asarray(grid["wavelength_nm"]).copy(),
    }
    for field in TEMPLATE_NODE_FIELDS:
        selected[field] = np.asarray(grid[field])[selection_mask].copy()

    selected_spt_num = np.asarray(selected["spt_num"])
    if not np.all(np.diff(selected_spt_num) > 0):
        raise ValueError("选择后的 SPTNUM 节点必须严格递增")

    return selected

def interpolate_template(
    selected_grid: dict[str, np.ndarray | str | int],
    spt_num: float,
) -> dict[str, np.ndarray | str | float | int]:
    """在已选择的 SPTNUM 节点间进行逐波长线性插值。

    本函数不进行外推、消光、缩放、负值裁剪或模板修正。返回值保留
    上下节点、原始节点索引与插值权重，供后续 provenance audit 使用。
    """
    target_spt_num = float(spt_num)
    if not np.isfinite(target_spt_num):
        raise ValueError("spt_num 必须是有限数值")

    required_keys = {
        "policy",
        "selected_node_indices",
        "spt_num",
        "wavelength_nm",
        "flux",
    }
    missing_keys = sorted(required_keys - set(selected_grid))
    if missing_keys:
        raise ValueError(
            "selected template grid 缺少字段："
            f"{', '.join(missing_keys)}"
        )

    nodes = np.asarray(selected_grid["spt_num"], dtype=np.float64)
    flux_grid = np.asarray(selected_grid["flux"], dtype=np.float64)
    source_indices = np.asarray(
        selected_grid["selected_node_indices"],
        dtype=np.int64,
    )

    if nodes.ndim != 1 or len(nodes) < 2:
        raise ValueError("selected template grid 至少需要两个一维 SPTNUM 节点")
    if flux_grid.ndim != 2 or flux_grid.shape[0] != len(nodes):
        raise ValueError("selected template flux 的首维必须对应 SPTNUM 节点")
    if source_indices.shape != nodes.shape:
        raise ValueError("selected_node_indices 必须与 SPTNUM 节点一一对应")
    if not np.all(np.diff(nodes) > 0):
        raise ValueError("selected template SPTNUM 节点必须严格递增")

    lower_bound = float(nodes[0])
    upper_bound = float(nodes[-1])
    if target_spt_num < lower_bound or target_spt_num > upper_bound:
        raise ValueError(
            f"spt_num={target_spt_num} 超出模板范围 "
            f"[{lower_bound}, {upper_bound}]；P2-v0 禁止外推"
        )

    exact_positions = np.flatnonzero(
        np.isclose(
            nodes,
            target_spt_num,
            rtol=0.0,
            atol=1e-12,
        )
    )
    if len(exact_positions) == 1:
        lower_position = int(exact_positions[0])
        upper_position = lower_position
        upper_weight = 0.0
        interpolated_flux = flux_grid[lower_position].copy()
    elif len(exact_positions) > 1:
        raise ValueError("selected template grid 包含重复 SPTNUM 节点")
    else:
        upper_position = int(np.searchsorted(nodes, target_spt_num))
        lower_position = upper_position - 1
        lower_spt_num = float(nodes[lower_position])
        upper_spt_num = float(nodes[upper_position])
        upper_weight = (
            (target_spt_num - lower_spt_num)
            / (upper_spt_num - lower_spt_num)
        )
        interpolated_flux = (
            (1.0 - upper_weight) * flux_grid[lower_position]
            + upper_weight * flux_grid[upper_position]
        )

    return {
        "policy": str(selected_grid["policy"]),
        "requested_spt_num": target_spt_num,
        "lower_spt_num": float(nodes[lower_position]),
        "upper_spt_num": float(nodes[upper_position]),
        "upper_weight": float(upper_weight),
        "lower_source_node_index": int(source_indices[lower_position]),
        "upper_source_node_index": int(source_indices[upper_position]),
        "wavelength_nm": np.asarray(
            selected_grid["wavelength_nm"],
            dtype=np.float64,
        ).copy(),
        "flux": interpolated_flux,
    }

def apply_ccm89_extinction(
    wavelength_nm: np.ndarray,
    flux: np.ndarray,
    av_mag: float,
    rv: float = DEFAULT_RV,
) -> dict[str, np.ndarray | float | str]:
    """对内禀模板施加 CCM89 消光，得到观测方向的 reddened flux。"""
    wavelength_nm = np.asarray(wavelength_nm, dtype=np.float64)
    flux = np.asarray(flux, dtype=np.float64)
    av_mag = float(av_mag)
    rv = float(rv)

    if wavelength_nm.ndim != 1 or flux.ndim != 1:
        raise ValueError("wavelength_nm 和 flux 必须是一维数组")
    if wavelength_nm.shape != flux.shape:
        raise ValueError("wavelength_nm 与 flux 形状必须一致")
    if not np.isfinite(wavelength_nm).all() or np.any(wavelength_nm <= 0):
        raise ValueError("wavelength_nm 必须是有限正数")
    if not np.isfinite(flux).all():
        raise ValueError("flux 包含非有限值")
    if not np.isfinite(av_mag) or av_mag < 0:
        raise ValueError("av_mag 必须是有限非负数")
    if not np.isfinite(rv) or rv <= 0:
        raise ValueError("rv 必须是有限正数")

    wavelength_angstrom = wavelength_nm * 10.0
    extinction_curve_per_av = extinction.ccm89(
        wavelength_angstrom,
        a_v=1.0,
        r_v=rv,
        unit="aa",
    )
    transmission = np.power(
        10.0,
        -0.4 * av_mag * extinction_curve_per_av,
    )
    reddened_flux = flux * transmission

    return {
        "law": "CCM89",
        "av_mag": av_mag,
        "rv": rv,
        "wavelength_nm": wavelength_nm.copy(),
        "extinction_curve_per_av": extinction_curve_per_av,
        "transmission": transmission,
        "flux": reddened_flux,
    }
