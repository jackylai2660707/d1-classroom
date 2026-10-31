import base64
from contextlib import ExitStack
import hashlib
import importlib.util
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch
import zipfile

REPO = Path(__file__).resolve().parents[2]


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


pc = load('pc_initialize', REPO/'scripts/initialize-robot.py')
remote = load('remote_provision', REPO/'d1-classroom/bridge/provision.py')
START = '#!/bin/bash\nexport ROBOT_TYPE=XG\ncd /opt/export/mc/bin && taskset -c 7 ./mc_ctrl r\n'
CONFIG = 'target_ip: "192.168.234.1"\ntarget_port: 43988\n'


class PCSetupTests(unittest.TestCase):
    def test_only_canonical_private_ipv4_is_accepted(self):
        self.assertEqual(pc.address(' 192.168.234.1 '), '192.168.234.1')
        self.assertEqual(pc.address('10.3.4.5'), '10.3.4.5')
        for value in ('127.0.0.1', '0.0.0.0', '8.8.8.8', '169.254.1.1', '::1', '192.168.5.1;whoami', '192.168.5.1/24'):
            with self.assertRaises(ValueError): pc.address(value)

    def test_pinned_host_key_and_password_file_not_password_argv(self):
        ssh = pc.SSH('192.168.5.22', 'SHA256:test', Path('secret.tmp'), 'plink')
        self.assertIn('-hostkey', ssh.prefix)
        self.assertIn('-pwfile', ssh.prefix)
        self.assertNotIn('-pw', ssh.prefix)
        self.assertIn('-batch', ssh.prefix)

    def test_keyscan_hash_and_ambiguous_host_keys(self):
        key = b'fake-ed25519-key-for-unit-test'
        line = b'192.168.5.22 ssh-ed25519 ' + base64.b64encode(key) + b'\n'
        with patch.object(pc, 'execute', return_value=SimpleNamespace(stdout=line)):
            actual = pc.fingerprint('192.168.5.22', 'ssh-keyscan')
        self.assertEqual(actual, 'SHA256:' + base64.b64encode(hashlib.sha256(key).digest()).decode().rstrip('='))
        other = b'192.168.5.22 ssh-ed25519 ' + base64.b64encode(b'other') + b'\n'
        with patch.object(pc, 'execute', return_value=SimpleNamespace(stdout=line + other)):
            with self.assertRaises(ValueError): pc.fingerprint('192.168.5.22', 'ssh-keyscan')

    def test_known_mac_key_change_is_not_silently_accepted(self):
        with tempfile.TemporaryDirectory() as directory:
            registry = Path(directory)/'hosts.json'
            pc.pin_identity(registry, '02:12:34:56:78:90', 'SHA256:first')
            before = registry.read_bytes()
            with self.assertRaisesRegex(ValueError, '金鑰'):
                pc.pin_identity(registry, '02:12:34:56:78:90', 'SHA256:changed')
            self.assertEqual(registry.read_bytes(), before)
            pc.pin_identity(registry, '02:12:34:56:78:91', 'SHA256:second-dog')
            self.assertEqual(len(json.loads(registry.read_text())), 2)

    def test_temporary_credential_deleted_even_on_failure(self):
        with tempfile.TemporaryDirectory() as directory, patch.object(pc, 'ROOT', Path(directory)):
            fake = SimpleNamespace(stdout=b'"user","S-1-5-21-100-200-300-400"\n')
            with patch.object(pc, 'execute', return_value=fake):
                with self.assertRaises(RuntimeError):
                    with pc.credential_file('unit-test-password') as path:
                        self.assertEqual(path.read_bytes(), b'unit-test-password\n')
                        raise RuntimeError('simulated failure')
            self.assertFalse(path.exists())

    def test_archive_extraction_rejects_traversal_before_writing(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            archive = root/'setup.zip'
            with zipfile.ZipFile(archive, 'w') as z:
                z.writestr('d1-setup/../../outside', 'bad')
            sha = hashlib.sha256(archive.read_bytes()).hexdigest()
            with self.assertRaises(AssertionError):
                exec(pc.extraction_code(archive, root/'stage', sha), {})
            self.assertFalse((root/'stage').exists())
            self.assertFalse((root/'outside').exists())

    def test_check_only_never_uploads_or_runs_sudo(self):
        with tempfile.TemporaryDirectory() as directory, ExitStack() as stack:
            root = Path(directory)
            info = {'home': '/home/firefly', 'mac': '02:12:34:56:78:90', 'motion_version': '0.5.1-xg', 'problems': []}
            calls = []
            class FakeSSH:
                def __init__(self, *args): self.prefix = ['plink']
                def run(self, command, *args, **kwargs):
                    calls.append(command)
                    return 'D1_INIT_JSON=' + json.dumps(info)
            stack.enter_context(patch.object(pc, 'ROOT', root))
            stack.enter_context(patch.object(pc, 'make_package', return_value=(root/'unused.zip', 'test-hash')))
            stack.enter_context(patch.object(pc, 'executable', side_effect=lambda name: name))
            stack.enter_context(patch.object(pc, 'fingerprint', return_value='SHA256:test'))
            stack.enter_context(patch.object(pc, 'execute', return_value=SimpleNamespace(stdout=b'-pwfile')))
            stack.enter_context(patch.object(pc, 'credential_file', return_value=__import__('contextlib').nullcontext(root/'secret.tmp')))
            stack.enter_context(patch.object(pc, 'SSH', FakeSSH))
            stack.enter_context(patch.dict(os.environ, {'D1_SSH_PASSWORD': 'not-printed-secret'}))
            stack.enter_context(patch.object(sys, 'argv', ['initialize-robot.py', '--check-only', '192.168.5.22']))
            stack.enter_context(patch('sys.stdout', new_callable=io.StringIO))
            pc.main()
            self.assertEqual(len(calls), 1)
            self.assertIn('--probe', calls[0])
            self.assertNotIn('sudo', calls[0])
            reports = list((root/'field-results/initialization').glob('*.json'))
            self.assertTrue(reports)
            self.assertTrue(all('not-printed-secret' not in p.read_text() for p in reports))


class RemoteSetupTests(unittest.TestCase):
    def test_only_reviewed_script_is_rewritten_without_changing_robot_type(self):
        with patch.object(remote, 'START_HASHES', {hashlib.sha256(START.encode()).hexdigest()}):
            config, start = remote.loopback_text(CONFIG, START)
            self.assertIn('target_ip: "127.0.0.1"', config)
            self.assertIn('export ROBOT_TYPE=XG', start)
            self.assertIn('export SDK_CLIENT_IP="127.0.0.1"', start)
            with self.assertRaises(ValueError): remote.loopback_text(CONFIG, START + '# unreviewed change\n')
            with self.assertRaises(ValueError): remote.loopback_text(CONFIG + 'extra: value\n', START)

    def transaction(self, success):
        with tempfile.TemporaryDirectory() as directory, ExitStack() as stack:
            area = Path(directory)
            runtime = area/'opt/runtime';runtime.mkdir(parents=True)
            (runtime/'bridge.py').write_text('original-runtime')
            files = {'sdk_config': area/'sdk.yaml', 'motion_start': area/'start.sh', 'unit': area/'service.unit'}
            files['sdk_config'].write_bytes(CONFIG.encode())
            files['motion_start'].write_bytes(START.encode())
            info = {'mac': '02:12:34:56:78:90', 'bridge_active': 'inactive', 'bridge_enabled': 'not-found', 'problems': []}
            calls = []
            def fake_run(args, **kwargs):
                calls.append(args)
                if args[0] == 'bash':
                    (runtime/'bridge.py').write_text('new-runtime')
                    files['unit'].write_text('new-unit')
                output = '127.0.0.1:43997' if args[0] == 'ss' else ''
                return subprocess.CompletedProcess(args, 0, stdout=output)
            stack.enter_context(patch.object(remote, 'ROOT', runtime))
            stack.enter_context(patch.object(remote, 'BACKUPS', area/'backups'))
            stack.enter_context(patch.object(remote, 'LOCK', area/'lock'))
            stack.enter_context(patch.object(remote, 'FILES', files))
            stack.enter_context(patch.object(remote, 'START_HASHES', {hashlib.sha256(START.encode()).hexdigest()}))
            stack.enter_context(patch.object(remote, 'probe', return_value=info))
            stack.enter_context(patch.object(remote, 'run', side_effect=fake_run))
            stack.enter_context(patch.object(remote.os, 'geteuid', return_value=0, create=True))
            stack.enter_context(patch.object(remote.os, 'chown', create=True))
            stack.enter_context(patch.object(remote.os, 'dup2'))
            stack.enter_context(patch.dict(sys.modules, {'fcntl': SimpleNamespace(flock=lambda *args: None, LOCK_EX=1, LOCK_NB=2),
                                                       'install': SimpleNamespace(extract_bundled_sdk=lambda *args: None, verify_sdk=lambda *args: None)}))
            stack.enter_context(patch.object(remote.time, 'sleep'))
            opener = SimpleNamespace(open=lambda *a, **kw: io.BytesIO(json.dumps({'mac': info['mac'], 'sdk_ready': True}).encode()))
            if not success:
                def fail(*args, **kwargs): raise OSError('simulated SDK health failure')
                opener.open = fail
            stack.enter_context(patch('urllib.request.build_opener', return_value=opener))
            if success:
                result = remote.apply()
                self.assertTrue(result['initialized'])
                self.assertFalse(result['autostart'])
                self.assertIn('127.0.0.1', files['sdk_config'].read_text())
                self.assertEqual((runtime/'bridge.py').read_text(), 'new-runtime')
                self.assertFalse(any(a[:2] == ['systemctl', 'enable'] for a in calls))
                count = len(calls)
                self.assertEqual(remote.restore(result['backup'], automatic=True), {'rollback': 'not_needed'})
                self.assertEqual(len(calls), count)
            else:
                with self.assertRaisesRegex(ValueError, '就緒'): remote.apply()
                self.assertEqual(files['sdk_config'].read_text(), CONFIG)
                self.assertEqual(files['motion_start'].read_text(), START)
                self.assertEqual((runtime/'bridge.py').read_text(), 'original-runtime')
                self.assertFalse(files['unit'].exists())
                self.assertTrue(list((area/'backups').glob('*/restored')))
            self.assertTrue(any(a[0] == 'systemd-run' and '--on-active=180s' in a for a in calls))
            self.assertTrue(any(a[0] == 'bash' and '--no-start' in a for a in calls))

    def test_success_checks_health_without_enabling_boot(self):
        self.transaction(True)

    def test_failed_health_restores_original_files_and_runtime(self):
        self.transaction(False)

    def test_unrecognized_profile_and_busy_robot_stop_before_backup(self):
        fake_lock = SimpleNamespace(flock=lambda *args: None, LOCK_EX=1, LOCK_NB=2)
        with tempfile.TemporaryDirectory() as directory, patch.object(remote, 'LOCK', Path(directory)/'lock'), patch.object(remote.os, 'dup2'), patch.object(remote.os, 'geteuid', return_value=0, create=True), patch.dict(sys.modules, {'fcntl': fake_lock}):
            with patch.object(remote, 'probe', return_value={'problems': ['unknown firmware']}):
                with self.assertRaisesRegex(ValueError, 'unknown firmware'): remote.apply()
            with patch.object(remote, 'probe', return_value={'problems': [], 'bridge_active': 'active'}), patch.object(remote, 'idle_state', return_value='busy'):
                with self.assertRaisesRegex(ValueError, '使用中'): remote.apply()


if __name__ == '__main__':
    unittest.main()
