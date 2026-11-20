"""验证资产缺失、篡改和缓存迁移，不依赖实测数据。"""
import hashlib
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from gaia_accretion import assets


class AssetTests(unittest.TestCase):
    def test_import_reuse_and_reject_corruption(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            source = root/'source'
            source.mkdir()
            (source/'input.txt').write_bytes(b'known asset')
            spec = {'assets':{'test':{'kind':'file','path':'cache/input.txt','files':[
                {'path':'cache/input.txt','source_path':'input.txt','size':11,
                 'sha256':hashlib.sha256(b'known asset').hexdigest()}]}}}
            with patch.object(assets, 'manifest', return_value=spec), patch.dict(os.environ, {'GAIA_XP_ASSETS':str(root/'target')}):
                self.assertEqual(assets.check()['status'], 'invalid')
                self.assertEqual(assets.import_assets(source)['status'], 'complete')
                self.assertEqual(assets.import_assets(source)['status'], 'complete')
                dest=assets.asset_path('test')
                dest.write_bytes(b'changed')
                self.assertEqual(assets.check()['status'], 'invalid')
                with self.assertRaises(ValueError): assets.import_assets(source)
                self.assertEqual(dest.read_bytes(), b'changed')

    def test_manifest_paths_cannot_escape_root(self):
        with tempfile.TemporaryDirectory() as folder:
            with self.assertRaises(ValueError): assets._inside(Path(folder), '../outside')


class PackagedAssetTests(unittest.TestCase):
    def setUp(self):
        self.root = Path(self.enterContext(tempfile.TemporaryDirectory())).resolve()
        self.package = self.root / 'package'
        self.fang = Path('fang/example.sav')
        self.slab = Path('slab_grid/model.out')
        groups = {}
        for key, item, content in [('fang_template', self.fang, b'template'),
                                   ('slab_grid', self.slab, b'slab')]:
            is_grid = key == 'slab_grid'
            groups[key] = dict(kind='directory' if is_grid else 'file',
                               path=(item.parent if is_grid else item).as_posix(),
                               files=[dict(path=item.as_posix(), source_path='original/' + item.name,
                                           size=len(content), sha256=hashlib.sha256(content).hexdigest())])
            path = self.package / item
            path.parent.mkdir(parents=True)
            path.write_bytes(content)
        self.enterContext(patch.object(assets, 'manifest', return_value={'assets': groups}))
        self.enterContext(patch.object(assets, 'packaged_root', return_value=self.package))
        self.enterContext(patch.dict(os.environ, {'LOCALAPPDATA': str(self.root), 'XDG_CACHE_HOME': str(self.root),
                                                  'GAIA_XP_ASSETS': ''}))
        self.cache = assets.cache_root()

    def test_fresh_install_uses_packaged_groups_without_creating_cache(self):
        result = assets.check()
        self.assertEqual(result['root'], str(self.package))
        self.assertEqual(result['status'], 'complete')
        self.assertEqual(result['checked_files'], 2)
        self.assertEqual(assets.asset_path('slab_grid'), self.package / self.slab.parent)
        self.assertEqual(result['groups']['fang_template']['origin'], 'package')
        self.assertEqual(assets.import_assets(self.root)['status'], 'complete')
        self.assertFalse(self.cache.exists())

    def test_import_fang_only_into_cache_keeps_packaged_grid_in_place(self):
        (self.package / self.fang).unlink()
        self.assertEqual(assets.check()['missing'], [self.fang.as_posix()])
        source = self.root / 'backup'
        source.mkdir()
        (source / self.fang.name).write_bytes(b'template')
        result = assets.import_assets(source)
        self.assertEqual(result['status'], 'complete')
        self.assertIsNone(result['root'])
        self.assertEqual(result['groups']['fang_template']['origin'], 'cache')
        self.assertEqual(assets.asset_path('fang_template'), self.cache / self.fang)
        self.assertEqual(assets.asset_path('slab_grid'), self.package / self.slab.parent)
        self.assertFalse((self.cache / self.slab.parent).exists())
        self.assertFalse((self.package / self.fang).exists())

    def test_corrupt_or_incomplete_cache_group_remains_visible(self):
        cached = self.cache / self.slab
        cached.parent.mkdir(parents=True)
        result = assets.check()
        self.assertEqual(result['groups']['slab_grid']['origin'], 'cache')
        self.assertEqual(result['missing'], [self.slab.as_posix()])
        cached.write_bytes(b'bad!')
        self.assertEqual(assets.check()['missing'], [])
        with self.assertRaises(FileNotFoundError):
            assets.asset_path('slab_grid')
        with self.assertRaises(ValueError):
            assets.import_assets(self.package)
        self.assertEqual(cached.read_bytes(), b'bad!')
        self.assertEqual((self.package / self.slab).read_bytes(), b'slab')

    def test_interrupted_import_can_be_retried(self):
        source = self.root / 'backup'
        source.mkdir()
        (self.package / self.fang).rename(source / self.fang.name)

        def interrupted(_source, staged):
            staged.write_bytes(b'temp')
            raise OSError('copy interrupted')

        with patch.object(assets.shutil, 'copyfile', side_effect=interrupted):
            with self.assertRaises(OSError):
                assets.import_assets(source)
        self.assertFalse((self.cache / self.fang).exists())
        self.assertEqual(assets.import_assets(source)['status'], 'complete')

    def test_explicit_root_is_exclusive_and_package_is_read_only(self):
        override = self.root / 'explicit'
        with patch.dict(os.environ, {'GAIA_XP_ASSETS': str(override)}):
            result = assets.check()
            self.assertEqual(result['root'], str(override))
            self.assertEqual(result['groups']['slab_grid']['origin'], 'explicit')
            self.assertEqual(result['missing'], [self.fang.as_posix(), self.slab.as_posix()])
            self.assertEqual(assets.import_assets(self.package)['status'], 'complete')
            self.assertEqual(assets.asset_path('slab_grid'), override / self.slab.parent)
        with patch.dict(os.environ, {'GAIA_XP_ASSETS': str(self.package)}):
            with self.assertRaises(ValueError):
                assets.import_assets(override)
