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
    cli.add_argument("--version", action="version", version="gaia-xp-workbench 0.1.0")
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
            elif args.command == "review":
                result = work.review(args.run)
                if args.output:
                    destination = work.new_directory(args.output)
                    work.write_json(destination/"review.json", result)
                    work.write_report(destination/"report.md", result)
            else:
                result = work.summarize([work.review(run) for run in args.run], args.output)
    except (ValueError, FileNotFoundError, RuntimeError, KeyError) as error:
        cli.exit(2, f"错误：{error}\n")
    print(json.dumps(result, ensure_ascii=False, indent=2, allow_nan=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
