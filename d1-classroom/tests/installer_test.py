import pathlib
import sys
import tempfile
import unittest
import hashlib
import json
import zipfile
import subprocess
import os
from unittest.mock import patch

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]/'bridge'))
from install import wifi_interface, sdk_directory, write_changed, service_text, extract_bundled_sdk, install_bundled_sdk, BUNDLE
from bridge import read_mac


class InstallerTests(unittest.TestCase):
    def make_bundle(self, root):
        root.mkdir()
        archive = root/'vendor.zip'
        with zipfile.ZipFile(archive, 'w') as output:
            for arch in ['aarch64', 'x86_64']:
                for name in [f'libmc_sdk_zsl_1_{arch}.so', f'mc_sdk_zsl_1_py.cpython-310-{arch}-linux-gnu.so']:
                    output.writestr(f'agibot_D1_Edu-Ultra/lib/zsl-1/{arch}/{name}', b'test-binary-'+arch.encode())
            output.writestr('agibot_D1_Edu-Ultra/LICENSE', 'test-license')
            output.writestr('../../outside', 'must never extract')
        (root/'manifest.json').write_text(json.dumps({'archive': 'vendor.zip', 'sha256': hashlib.sha256(archive.read_bytes()).hexdigest()}))
        (root/'LICENSE.vendor.txt').write_text('test-license')
        return root

    def test_real_vendor_archive_has_both_architectures_and_original_license(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = pathlib.Path(temporary)
            for arch in ['aarch64', 'x86_64']:
                destination = root/arch
                extract_bundled_sdk(BUNDLE, destination, arch)
                self.assertEqual(len(list(destination.glob('*.so'))), 2)
                for binary in destination.glob('*.so'):
                    self.assertEqual(binary.read_bytes()[:4], b'\x7fELF')
                self.assertEqual((destination/'LICENSE.vendor.txt').read_bytes(), (BUNDLE/'LICENSE.vendor.txt').read_bytes())

    def test_corrupt_sdk_refused_before_destination_is_created(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = pathlib.Path(temporary)
            bundle = self.make_bundle(root/'bundle')
            with (bundle/'vendor.zip').open('ab') as output: output.write(b'corruption')
            with self.assertRaisesRegex(ValueError, '完整性'):
                extract_bundled_sdk(bundle, root/'installed', 'aarch64')
            self.assertFalse((root/'installed').exists())

    def test_unsupported_cpu_refused_and_archive_paths_are_not_extracted(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = pathlib.Path(temporary)
            bundle = self.make_bundle(root/'bundle')
            with self.assertRaisesRegex(ValueError, 'CPU'):
                extract_bundled_sdk(bundle, root/'stage', 'armv7l')
            extract_bundled_sdk(bundle, root/'stage', 'aarch64')
            self.assertFalse((root/'outside').exists())

    def test_bundled_sdk_installs_to_stable_path_and_repeat_is_unchanged(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = pathlib.Path(temporary)
            bundle = self.make_bundle(root/'bundle')
            with patch('install.ROOT', root/'opt'), patch('install.platform.machine', return_value='aarch64'), patch('install.verify_sdk'):
                installed = install_bundled_sdk(bundle)
                binary = next(installed.glob('mc_sdk*.so'))
                before = binary.stat().st_mtime_ns
                self.assertEqual(install_bundled_sdk(bundle), installed)
                self.assertEqual(binary.stat().st_mtime_ns, before)
                self.assertFalse(list(installed.glob('*.previous')))
                self.assertEqual((root/'opt/vendor/vendor.zip').read_bytes(), (bundle/'vendor.zip').read_bytes())
                self.assertNotIn(str(bundle), service_text('/usr/bin/python3.10', installed.as_posix(), 'root'))

    def test_sdk_abi_failure_does_not_replace_installed_sdk(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = pathlib.Path(temporary)
            bundle = self.make_bundle(root/'bundle')
            with patch('install.ROOT', root/'opt'), patch('install.platform.machine', return_value='aarch64'), patch('install.verify_sdk', side_effect=subprocess.CalledProcessError(1, 'import')):
                with self.assertRaises(subprocess.CalledProcessError): install_bundled_sdk(bundle)
                self.assertFalse((root/'opt').exists())

    @unittest.skipUnless(sys.platform == 'linux', 'Linux shell wrapper')
    def test_shell_automatically_selects_cpython310(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = pathlib.Path(temporary)
            python = root/'python3.10'
            python.write_text('#!/bin/sh\nif [ "$1" = "-c" ]; then exit 0; fi\nprintf "selected-python310\\n"\n')
            python.chmod(0o755)
            env = {**os.environ, 'PATH': str(root)+os.pathsep+os.environ['PATH']}
            env.pop('D1_PYTHON', None)
            result = subprocess.run(['bash', str(pathlib.Path(__file__).resolve().parents[1]/'bridge/install.sh')], env=env, capture_output=True, text=True, check=True)
            self.assertIn('selected-python310', result.stdout)

    def test_select_wifi_and_reject_ambiguous_hardware(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = pathlib.Path(temporary)
            (root/'wlan0'/'wireless').mkdir(parents=True)
            (root/'eth0').mkdir()
            (root/'wlan0'/'address').write_text('02:12:34:56:78:90\n')
            self.assertEqual(wifi_interface(root=root), 'wlan0')
            self.assertEqual(read_mac('wlan0', root), '02:12:34:56:78:90')
            (root/'wlan1'/'wireless').mkdir(parents=True)
            with self.assertRaises(ValueError): wifi_interface(root=root)
            self.assertEqual(wifi_interface('wlan0', root), 'wlan0')
            with self.assertRaises(ValueError): wifi_interface('eth0', root)
            with self.assertRaises(ValueError): read_mac('../secret', root)

    def test_repeat_install_preserves_current_files_and_one_backup(self):
        with tempfile.TemporaryDirectory() as temporary:
            path = pathlib.Path(temporary)/'robot.json'
            write_changed(path, 'first')
            before = path.stat().st_mtime_ns
            write_changed(path, 'first')
            self.assertEqual(path.stat().st_mtime_ns, before)
            self.assertFalse(path.with_name('robot.json.previous').exists())
            write_changed(path, 'second')
            self.assertEqual(path.read_text(), 'second')
            self.assertEqual(path.with_name('robot.json.previous').read_text(), 'first')

    def test_resolve_sdk_root_by_machine_and_reject_missing_module(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = pathlib.Path(temporary)
            directory = root/'lib'/'zsl-1'/'aarch64'
            directory.mkdir(parents=True)
            (directory/'mc_sdk_zsl_1_py.cpython-310-aarch64-linux-gnu.so').touch()
            with patch('install.platform.machine', return_value='aarch64'):
                self.assertEqual(sdk_directory(str(root)), directory)
            with patch('install.platform.machine', return_value='x86_64'):
                with self.assertRaises(ValueError): sdk_directory(str(root))

    def test_unit_has_exact_runtime_and_rejects_directive_injection(self):
        unit = service_text('/usr/bin/python3.10', '/opt/vendor SDK', 'firefly')
        self.assertIn('ExecStart="/usr/bin/python3.10"', unit)
        self.assertIn('Restart=on-failure', unit)
        with self.assertRaises(ValueError): service_text('/usr/bin/python\nExecStart=bad', '/opt/sdk', 'root')


if __name__ == '__main__': unittest.main()
