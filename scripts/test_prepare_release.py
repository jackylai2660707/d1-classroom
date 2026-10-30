"""Focused release tests: preserve published bytes, reject stale builds, produce new checksums."""
from pathlib import Path
import contextlib
import hashlib
import importlib.util
import io
import json
import tempfile
import unittest
from unittest.mock import patch
import zipfile

SCRIPT=Path(__file__).with_name('prepare-release.py')
spec=importlib.util.spec_from_file_location('prepare_release',SCRIPT)
release=importlib.util.module_from_spec(spec);spec.loader.exec_module(release)


class ReleaseTests(unittest.TestCase):
    def fixture(self,root,version):
        (root/'releases').mkdir();(root/'d1-classroom').mkdir();(root/'output').mkdir()
        (root/'d1-classroom/package.json').write_text(json.dumps({'version':version}),encoding='utf-8')
        with zipfile.ZipFile(root/'output/D1彩色課程完整套件.zip','w') as z:
            z.writestr('D1彩色課程套件/先讀我.md','# D1 機器狗實驗室 '+version+'\n')
        with zipfile.ZipFile(root/'output/D1機器狗初始化包.zip','w') as z:z.writestr('d1-setup/README.md','fixture')

    def test_existing_version_is_untouched(self):
        with tempfile.TemporaryDirectory(prefix='d1-release-check-') as folder:
            root=Path(folder);self.fixture(root,'2.0.0')
            manifest=root/'releases/v2.0.0.json';manifest.write_bytes(b'immutable checksum manifest')
            artifact=root/'output/github-release/v2.0.0';artifact.mkdir(parents=True)
            existing=artifact/'SHA256SUMS.txt';existing.write_bytes(b'immutable checksums')
            with patch.object(release,'ROOT',root),self.assertRaisesRegex(ValueError,'already exists'):
                release.prepare('2.0.0')
            self.assertEqual(manifest.read_bytes(),b'immutable checksum manifest')
            self.assertEqual(existing.read_bytes(),b'immutable checksums')

    def test_new_version_and_stale_build(self):
        with tempfile.TemporaryDirectory(prefix='d1-release-check-') as folder:
            root=Path(folder);self.fixture(root,'2.0.1')
            with patch.object(release,'ROOT',root),contextlib.redirect_stdout(io.StringIO()):
                manifest=release.prepare('2.0.1')
                self.assertEqual(manifest['tag'],'v2.0.1')
                self.assertEqual(len(manifest['assets']),2)
                for asset in manifest['assets']:
                    path=root/'output/github-release/v2.0.1'/asset['name']
                    self.assertEqual(hashlib.sha256(path.read_bytes()).hexdigest(),asset['sha256'])
                (root/'d1-classroom/package.json').write_text('{"version":"2.0.2"}',encoding='utf-8')
                with self.assertRaisesRegex(ValueError,'stale'):
                    release.prepare('2.0.2')
                self.assertFalse((root/'releases/v2.0.2.json').exists())


if __name__=='__main__':unittest.main()
