"""显式定位、核验和导入拟合资产；不回退到任何研究项目目录。"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from importlib.resources import files
from pathlib import Path
import shutil


def manifest():
    return json.loads(files('gaia_accretion').joinpath('resources/assets.json').read_text(encoding='utf-8'))


def cache_root():
    supplied = os.environ.get('GAIA_XP_ASSETS')
    if supplied:
        return Path(supplied).expanduser().resolve()
    if os.name == 'nt':
        base = Path(os.environ.get('LOCALAPPDATA', str(Path.home() / 'AppData/Local')))
    else:
        base = Path(os.environ.get('XDG_CACHE_HOME', str(Path.home() / '.cache')))
    return base / 'gaia-xp-workbench' / 'assets' / 'fang25-v1'


def _inside(root, relative):
    path = (root / relative).resolve()
    if not path.is_relative_to(root.resolve()):
        raise ValueError('资产路径超出指定目录')
    return path


def _sha(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def _valid(path, item):
    return path.is_file() and path.stat().st_size == item['size'] and _sha(path) == item['sha256']


def check(keys=None):
    root = cache_root()
    bad = []
    count = 0
    for key, group in manifest()['assets'].items():
        if keys is not None and key not in keys:
            continue
        for item in group['files']:
            count += 1
            if not _valid(_inside(root, item['path']), item):
                bad.append(item['path'])
        if group['kind'] == 'directory':
            expected = {x['path'] for x in group['files']}
            extras = [p.relative_to(root).as_posix() for p in _inside(root, group['path']).glob('*.out')
                      if p.relative_to(root).as_posix() not in expected]
            bad.extend(extras)
    return dict(status='complete' if not bad else 'invalid', root=str(root), checked_files=count, invalid=bad)


def asset_path(key):
    group = manifest()['assets'][key]
    result = check([key])
    if result['status'] != 'complete':
        raise FileNotFoundError(f"资产 {key} 缺失或校验失败；先运行 gaia-xp assets import/check。首项：{result['invalid'][0]}")
    return _inside(cache_root(), group['path'])


def import_assets(source):
    source = Path(source).expanduser().resolve()
    target = cache_root()
    plan = []
    # 先检查所有输入，再开始复制；已有正确缓存可以直接复用。
    for group in manifest()['assets'].values():
        for item in group['files']:
            dest = _inside(target, item['path'])
            if dest.exists():
                if not _valid(dest, item):
                    raise ValueError(f'已有缓存与清单不符，不覆盖：{dest}')
                continue
            candidates = [_inside(source, item['path']), _inside(source, item['source_path'])]
            origin = next((p for p in candidates if _valid(p, item)), None)
            if origin is None:
                raise FileNotFoundError(f"输入资产缺失或哈希不符：{item['path']}")
            plan.append((origin, dest))
    for origin, dest in plan:
        dest.parent.mkdir(parents=True, exist_ok=True)
        with origin.open('rb') as src, dest.open('xb') as dst:
            shutil.copyfileobj(src, dst)
    return check()


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest='command', required=True)
    commands.add_parser('list')
    commands.add_parser('check')
    sub = commands.add_parser('import')
    sub.add_argument('--from-dir', type=Path, required=True)
    args = parser.parse_args(argv)
    if args.command == 'list':
        result = {k:{field:value for field,value in v.items() if field != 'files'}
                  for k,v in manifest()['assets'].items()}
    elif args.command == 'import':
        result = import_assets(args.from_dir)
    else:
        result = check()
    print(json.dumps(result, ensure_ascii=False, indent=2))
    if result.get('status') == 'invalid':
        raise SystemExit(2)
