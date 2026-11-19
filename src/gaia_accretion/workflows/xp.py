"""可移植XP单谱检查、传统Fang拟合、解读和明确选定结果汇总。"""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

# 一个进程，积分器两个工作线程，每个数值库保持单线程。
for _key in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS", "NUMEXPR_NUM_THREADS", "VECLIB_MAXIMUM_THREADS"):
    os.environ[_key] = "1"
os.environ["MPLBACKEND"] = "Agg"


def parser():
    cli = argparse.ArgumentParser(description=__doc__)
    cli.add_argument("--assets-dir", type=Path, help="固定版本的本地资产目录；也可设GAIA_XP_ASSETS")
    from gaia_accretion import __version__
    cli.add_argument("--version", action="version", version=f"gaia-xp-workbench {__version__}")
    commands = cli.add_subparsers(dest="command", required=True)
    commands.add_parser("assets", help="资产清单、检查和本地导入；assets --help查看")
    for name in ("inspect", "fit"):
        sub = commands.add_parser(name, help="检查光谱输入" if name == "inspect" else "在新目录拟合单谱")
        sub.add_argument("--input", type=Path, required=True, help="单谱NPZ")
        sub.add_argument("--metadata", type=Path, required=True, help="配套JSON元数据")
        sub.add_argument("--output", type=Path, required=name == "fit", help="尚不存在的新目录")
        if name == "fit":
            sub.add_argument("--seed", type=int, default=20260930)
    sub = commands.add_parser("review", help="读取完整运行并核验后验及摘要")
    sub.add_argument("--run", type=Path, required=True)
    sub.add_argument("--output", type=Path, help="可选新解读目录")
    sub = commands.add_parser("report", help="从保存结果生成总览图和离线HTML，不重拟合")
    sub.add_argument("--run", type=Path, required=True)
    sub.add_argument("--photometry", type=Path, help="已下载的同源测光目录；报告阶段不联网")
    sub.add_argument("--spectra", type=Path, help="已下载并核验的同源档案光谱目录")
    sub.add_argument("--output", type=Path, required=True, help="尚不存在的新报告目录")
    sub = commands.add_parser("photometry", help="查询并保存单源巡天测光，不拟合XP")
    sub.add_argument("--source-id", required=True, help="精确的Gaia DR3源编号")
    sub.add_argument("--radius-arcsec", type=float, default=3.0, help="候选搜索半径，单位角秒")
    sub.add_argument("--output", type=Path, required=True, help="尚不存在的新测光目录")
    sub = commands.add_parser("gaia-select", help="按编号或限定天区和测光条件选择Gaia候选")
    sub.add_argument("--release", choices=("dr3", "dr4"), default="dr3")
    sub.add_argument("--source-id", action="append", dest="source_ids")
    sub.add_argument("--ra", type=float, dest="ra_deg", help="ICRS赤经，度")
    sub.add_argument("--dec", type=float, dest="dec_deg", help="ICRS赤纬，度")
    sub.add_argument("--radius-arcmin", type=float)
    sub.add_argument("--g-max", type=float)
    sub.add_argument("--bp-rp-min", type=float)
    sub.add_argument("--bp-rp-max", type=float)
    sub.add_argument("--limit", type=int, default=20)
    sub.add_argument("--output", type=Path, required=True)
    sub = commands.add_parser("gaia-fetch", help="下载单源Gaia XP并准备分析输入，不自动拟合")
    sub.add_argument("--source-id", required=True)
    sub.add_argument("--release", choices=("dr3", "dr4"), default="dr3")
    sub.add_argument("--metadata", type=Path, help="同源的外部恒星参数及来源")
    sub.add_argument("--no-calibrate", action="store_true", help="仅保存原产品")
    sub.add_argument("--output", type=Path, required=True)
    sub = commands.add_parser("gaia-probe", help="检查Gaia发布版本的在线表结构，不假定DR4已可用")
    sub.add_argument("--release", choices=("dr3", "dr4"), default="dr4")
    sub.add_argument("--output", type=Path, required=True)
    sub = commands.add_parser("spectra-search", help="查询同源ESO档案光谱及可用产品")
    sub.add_argument("--source-id", required=True)
    sub.add_argument("--radius-arcsec", type=float, default=5.)
    sub.add_argument("--output", type=Path, required=True)
    sub = commands.add_parser("spectra-fetch", help="下载选定的已归约档案光谱")
    sub.add_argument("--discovery", type=Path, required=True)
    sub.add_argument("--product-id", action="append", dest="product_ids")
    sub.add_argument("--output", type=Path, required=True)
    sub = commands.add_parser("summarize", help="汇总指定结果，不重新拟合")
    sub.add_argument("--run", type=Path, action="append", required=True)
    sub.add_argument("--output", type=Path, required=True)
    return cli


def main(argv=None):
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8")
    argv = list(sys.argv[1:] if argv is None else argv)
    # 资产子命令独立解析，保证检查和导入不加载数值后端。
    prefix = argparse.ArgumentParser(add_help=False)
    prefix.add_argument("--assets-dir", type=Path)
    early, remaining = prefix.parse_known_args(argv)
    if early.assets_dir:
        os.environ["GAIA_XP_ASSETS"] = str(early.assets_dir.expanduser().resolve())
    if remaining and remaining[0] == "assets":
        from gaia_accretion.assets import main as asset_main
        return asset_main(remaining[1:])
    cli = parser()
    args = cli.parse_args(argv)
    from gaia_accretion.classical import xp_workbench as work
    from threadpoolctl import threadpool_limits
    try:
        with threadpool_limits(limits=1):
            if args.command in ("inspect", "fit"):
                data = work.load_input(args.input, args.metadata)
                if args.command == "fit":
                    result = work.fit(data, args.output, args.seed)
                else:
                    result = work.inspect(data)
                    if args.output:
                        destination = work.new_directory(args.output)
                        work.write_json(destination/"inspection.json", result)
            elif args.command == "report":
                from gaia_accretion.reporting import build_report
                result = build_report(args.run, args.output, photometry=args.photometry, spectra=args.spectra)
            elif args.command == "gaia-select":
                from gaia_accretion.gaia_download import select_sources
                result = select_sources(args.output, source_ids=args.source_ids, ra_deg=args.ra_deg, dec_deg=args.dec_deg,
                    radius_arcmin=args.radius_arcmin, g_max=args.g_max, bp_rp_min=args.bp_rp_min,
                    bp_rp_max=args.bp_rp_max, limit=args.limit, release=args.release)
            elif args.command == "gaia-fetch":
                from gaia_accretion.gaia_download import download_xp
                result = download_xp(args.source_id, args.output, release=args.release,
                                     metadata_path=args.metadata, calibrate=not args.no_calibrate)
            elif args.command == "gaia-probe":
                from gaia_accretion.gaia_download import probe_release
                result = probe_release(args.output, release=args.release)
            elif args.command == "spectra-search":
                from gaia_accretion.spectroscopy import discover_spectra
                result = discover_spectra(args.source_id, args.output, radius_arcsec=args.radius_arcsec)
            elif args.command == "spectra-fetch":
                from gaia_accretion.spectroscopy import fetch_spectra
                result = fetch_spectra(args.discovery, args.output, product_ids=args.product_ids)
            elif args.command == "photometry":
                from gaia_accretion.photometry import fetch_photometry
                result = fetch_photometry(args.source_id, args.output, radius_arcsec=args.radius_arcsec)
            elif args.command == "review":
                result = work.review(args.run)
                if args.output:
                    destination = work.new_directory(args.output)
                    work.write_json(destination/"review.json", result)
                    work.write_report(destination/"report.md", result)
            else:
                result = work.summarize([work.review(run) for run in args.run], args.output)
    except (ValueError, OSError, RuntimeError, KeyError) as error:
        cli.exit(2, f"错误：{error}\n")
    print(json.dumps(result, ensure_ascii=False, indent=2, allow_nan=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
