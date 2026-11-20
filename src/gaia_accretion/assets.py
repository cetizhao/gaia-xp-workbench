"""显式定位、核验和导入拟合资产；不回退到任何研究项目目录。"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from importlib.resources import files
from pathlib import Path
import shutil
import sysconfig
import tempfile


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
    return (base / 'gaia-xp-workbench' / 'assets' / 'fang25-v1').resolve()


def packaged_root():
    return Path(__file__).resolve().parent / 'resources' / 'models' / 'fang25-v1'


def _location(group):
    cache = cache_root()
    if os.environ.get('GAIA_XP_ASSETS'):
        return 'explicit', cache
    # 缓存中只要存在该组，就检查用户的版本，不能用内置副本掩盖损坏。
    if os.path.lexists(cache / group['path']):
        return 'cache', cache
    packaged = packaged_root()
    if os.path.lexists(packaged / group['path']):
        return 'package', packaged
    return 'cache', cache


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


def _check_group(root, group):
    invalid, missing = [], []
    for item in group['files']:
        path = _inside(root, item['path'])
        if not _valid(path, item):
            invalid.append(item['path'])
            if not path.exists():
                missing.append(item['path'])
    if group['kind'] == 'directory':
        expected = {item['path'] for item in group['files']}
        for path in sorted(_inside(root, group['path']).glob('*.out')):
            relative = path.relative_to(root).as_posix()
            if relative not in expected:
                invalid.append(relative)
    return invalid, missing


def check(keys=None):
    groups, roots = {}, set()
    invalid, missing = [], []
    count = 0
    for key, group in manifest()['assets'].items():
        if keys is not None and key not in keys:
            continue
        origin, root = _location(group)
        bad, absent = _check_group(root, group)
        groups[key] = dict(origin=origin, path=str(_inside(root, group['path'])),
                           status='invalid' if bad else 'complete')
        roots.add(root)
        count += len(group['files'])
        invalid.extend(bad)
        missing.extend(absent)
    shared_root = str(next(iter(roots))) if len(roots) == 1 else None
    return dict(status='invalid' if invalid else 'complete', root=shared_root,
                cache_root=str(cache_root()), groups=groups, checked_files=count,
                invalid=invalid, missing=missing)


def asset_path(key):
    result = check([key])
    if result['status'] != 'complete':
        raise FileNotFoundError(f"资产 {key} 缺失或校验失败；先运行 gaia-xp assets import/check。首项：{result['invalid'][0]}")
    return Path(result['groups'][key]['path'])


def import_assets(source):
    source = Path(source).expanduser().resolve()
    target = cache_root()
    readonly_roots = [packaged_root(), Path(sysconfig.get_path('purelib')), Path(sysconfig.get_path('platlib'))]
    if any(target.is_relative_to(path.resolve()) for path in readonly_roots):
        raise ValueError(f'资产缓存不能写入 Python 安装包目录：{target}')
    plan = []
    # 先检查所有输入，再开始复制；已有正确缓存可以直接复用。
    for key, group in manifest()['assets'].items():
        origin, root = _location(group)
        if origin == 'package':
            bad, _ = _check_group(root, group)
            if bad:
                raise ValueError(f'安装包中的资产校验失败：{_inside(root, bad[0])}')
            continue
        for item in group['files']:
            dest = _inside(target, item['path'])
            if dest.exists():
                if not _valid(dest, item):
                    raise ValueError(f'已有缓存与清单不符，不覆盖：{dest}')
                continue
            candidates = [_inside(source, item['path']), _inside(source, item['source_path'])]
            if key == 'fang_template':
                candidates.append(_inside(source, Path(item['path']).name))
            source_path = next((p for p in candidates if _valid(p, item)), None)
            if source_path is None:
                raise FileNotFoundError(f"输入资产缺失或哈希不符：{item['path']}")
            plan.append((source_path, dest, item))
    for source_path, dest, item in plan:
        dest.parent.mkdir(parents=True, exist_ok=True)
        # 校验完成后才公布副本，避免中断时留下无法重试的半个文件。
        with tempfile.TemporaryDirectory(dir=dest.parent) as temporary:
            staged = Path(temporary) / dest.name
            shutil.copyfile(source_path, staged)
            if not _valid(staged, item):
                raise ValueError(f'复制后的资产校验失败：{source_path}')
            if dest.exists():
                if not _valid(dest, item):
                    raise ValueError(f'已有缓存与清单不符，不覆盖：{dest}')
            else:
                staged.replace(dest)
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
