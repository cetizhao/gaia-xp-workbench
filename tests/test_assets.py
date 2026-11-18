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
