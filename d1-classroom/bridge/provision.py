"""Transactional setup for the field-verified XG image; no action tests."""
import argparse
import hashlib
import ipaddress
import json
import os
import pathlib
import platform
import re
import signal
import shutil
import socket
import subprocess
import sys
import time
import uuid

ROOT = pathlib.Path('/opt/d1-classroom')
BACKUPS = pathlib.Path('/var/lib/d1-classroom-init')
LOCK = pathlib.Path('/run/lock/d1-classroom-init.lock')
FILES = {
    'sdk_config': pathlib.Path('/opt/export/config/sdk_config.yaml'),
    'motion_start': pathlib.Path('/opt/app_launch/start_motion_control.sh'),
    'unit': pathlib.Path('/etc/systemd/system/d1-classroom.service'),
}
START_HASHES = {
    '64ae8c82060d0240ce4ef8db86c05e3208277d24373707d43b7217eb277e1208',
    '1c424e214983442069e324572cf21d1c944cdd8d107c9b02c62f0ac61d8cd270',
}


def run(args, timeout=15, check=True):
    return subprocess.run(args, stdin=subprocess.DEVNULL, capture_output=True, text=True, timeout=timeout, check=check)


def text(path):
    try:
        return pathlib.Path(path).read_bytes().decode('utf-8')
    except FileNotFoundError:
        return ''


def digest(path):
    return hashlib.sha256(pathlib.Path(path).read_bytes()).hexdigest()


def loopback_text(config, start):
    """Only alter the two reviewed SDK address settings, never robot type."""
    matches = re.findall(r'^target_ip:\s*"([0-9.]+)"\s*$', config, re.M)
    if len(matches) != 1 or not re.search(r'^target_port:\s*43988\s*$', config, re.M):
        raise ValueError('原廠 SDK 配置格式不同，停止；不猜測修改')
    ipaddress.IPv4Address(matches[0])
    if len([line for line in config.splitlines() if line.strip() and not line.lstrip().startswith('#')]) != 2:
        raise ValueError('原廠 SDK 配置有額外欄位，需人工核對')
    if hashlib.sha256(start.encode()).hexdigest() not in START_HASHES:
        raise ValueError('運控啟動腳本不屬於已驗證版本，未修改')
    config = re.sub(r'^(target_ip:\s*)"[0-9.]+"', r'\1"127.0.0.1"', config, flags=re.M)
    if 'SDK_CLIENT_IP' not in start:
        start = start.replace('export ROBOT_TYPE=XG', 'export ROBOT_TYPE=XG\nexport SDK_CLIENT_IP="127.0.0.1"')
    elif 'export SDK_CLIENT_IP="127.0.0.1"' not in start:
        raise ValueError('SDK_CLIENT_IP 格式未經驗證，未修改')
    return config, start


def probe():
    config, start = text(FILES['sdk_config']), text(FILES['motion_start'])
    version = text('/opt/robot/robot_version_manager/motion-control/version.yaml')
    match = re.search(r'^version:\s*(\S+)', version, re.M)
    os_release = text('/etc/os-release')
    mac = text('/sys/class/net/wlan0/address').strip().upper()
    ipv4 = []
    for device in json.loads(run(['ip', '-j', '-4', 'addr', 'show']).stdout):
        if device['ifname'] in ('wlan0', 'ap0') and 'UP' in device.get('flags', []):
            ipv4 += [a['local'] for a in device.get('addr_info', []) if a.get('family') == 'inet']
    active = run(['systemctl', 'is-active', 'd1-classroom'], check=False).stdout.strip()
    enabled = run(['systemctl', 'is-enabled', 'd1-classroom'], check=False).stdout.strip() or 'not-found'
    problems = []
    if sys.platform != 'linux' or platform.machine() != 'aarch64' or sys.version_info[:2] != (3, 10):
        problems.append('需已驗證的 Linux ARM64／CPython 3.10 環境')
    if not re.search(r'^ID=ubuntu$', os_release, re.M) or not re.search(r'^VERSION_ID="22\.04"$', os_release, re.M):
        problems.append('系統不是已驗證的 Ubuntu 22.04')
    if not match or match[1] != '0.5.1-xg' or 'export ROBOT_TYPE=XG' not in start:
        problems.append('機型／運控版本不同；目前僅自動處理已驗證的 XG 0.5.1-xg')
    try:
        loopback_text(config, start)
    except ValueError as error:
        problems.append(str(error))
    if not re.fullmatch(r'[0-9A-F]{2}(:[0-9A-F]{2}){5}', mac) or mac == '00:00:00:00:00:00' or int(mac[:2], 16) & 1:
        problems.append('找不到穩定 wlan0 MAC，未改用 AP 虛擬 MAC')
    if not ipv4:
        problems.append('wlan0／ap0 沒有啟用中的 IPv4')
    if ROOT.is_symlink() or any(p.is_symlink() for p in FILES.values()):
        problems.append('部署路徑是符號連結，需人工核對')
    if not shutil.which('python3.10') or not pathlib.Path('/usr/local/bin/robot-launch').is_file():
        problems.append('缺少 Python 3.10 或原廠 robot-launch')
    if run(['systemctl', 'is-active', 'robot-launch'], check=False).stdout.strip() != 'active':
        problems.append('原廠 robot-launch 尚未運行')
    if enabled not in ('enabled', 'disabled', 'not-found'):
        problems.append('既有橋接自啟狀態特殊，需人工核對')
    size = sum(p.stat().st_size for p in ROOT.rglob('*') if p.is_file() and not p.is_symlink()) if ROOT.exists() else 0
    if shutil.disk_usage('/opt').free < size * 2 + 256 * 1024**2:
        problems.append('空間不足以保留安裝與還原備份')
    return {'mac': mac, 'home': str(pathlib.Path.home()), 'python': shutil.which('python3.10'),
            'architecture': platform.machine(), 'python_version': platform.python_version(),
            'motion_version': match[1] if match else None, 'ipv4': ipv4,
            'bridge_active': active, 'bridge_enabled': enabled,
            'sdk_config_sha256': digest(FILES['sdk_config']) if config else None,
            'motion_start_sha256': digest(FILES['motion_start']) if start else None,
            'problems': problems}


def idle_state(info):
    """Use discovery only; never request a control lease during setup."""
    nonce = uuid.uuid4().hex
    payload = json.dumps({'type': 'd1-discover-v1', 'request': nonce}).encode()
    for address in info['ipv4']:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
            sock.settimeout(.7)
            sock.bind((address, 0))
            sock.sendto(payload, (address, 8765))
            try:
                data = json.loads(sock.recv(2048))
                if data.get('request') == nonce and data.get('mac') == info['mac']:
                    return data.get('state')
            except (OSError, ValueError):
                continue
    return 'unknown'


def atomic(path, data, mode=0o644, uid=0, gid=0):
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + '.init-new')
    temporary.write_bytes(data)
    os.chmod(temporary, mode)
    os.chown(temporary, uid, gid)
    os.replace(temporary, path)


def copy_tree(source, destination):
    shutil.copytree(source, destination, symlinks=True)
    for path in [source, *source.rglob('*')]:
        target = destination / path.relative_to(source)
        st = path.lstat()
        os.chown(target, st.st_uid, st.st_gid, follow_symlinks=False)


def restore(base, automatic=False):
    base = pathlib.Path(base).resolve()
    if base.parent != BACKUPS.resolve() or not (base/'snapshot.json').is_file():
        raise ValueError('還原目錄無效')
    if automatic and (base/'committed').exists():
        return {'rollback': 'not_needed'}
    meta = json.loads((base/'snapshot.json').read_text())
    for key, item in meta['files'].items():
        if item and digest(base/key) != item['sha256']:
            raise ValueError('備份完整性不符：' + key)
    run(['systemctl', 'stop', 'd1-classroom'], timeout=15, check=False)
    if ROOT.exists():
        shutil.move(str(ROOT), str(base/('failed-runtime-' + uuid.uuid4().hex[:8])))
    if (base/'runtime').exists():
        copy_tree(base/'runtime', ROOT)
    for key, path in FILES.items():
        item = meta['files'][key]
        if item:
            data = (base/key).read_bytes()
            if hashlib.sha256(data).hexdigest() != item['sha256']:
                raise ValueError('備份完整性不符：' + key)
            atomic(path, data, item['mode'], item['uid'], item['gid'])
        elif path.exists():
            path.unlink()  # Only the fixed classroom unit can be absent before installation.
    run(['systemctl', 'daemon-reload'])
    if meta['vendor_changed']:
        run(['/usr/local/bin/robot-launch', 'restart', 'motion_control'], timeout=30)
    run(['systemctl', 'enable' if meta['enabled'] else 'disable', 'd1-classroom'], check=False)
    if meta['active']:
        run(['systemctl', 'start', 'd1-classroom'])
    (base/'restored').write_text('Original files and service state restored; physical state requires observation.\n')
    return {'rollback': 'restored', 'backup': str(base)}


def apply():
    import fcntl
    if os.geteuid() != 0:
        raise ValueError('需要 sudo 執行初始化')
    if sys.platform == 'linux':
        # With passwordless sudo the password line can remain on stdin. Never pass it to SDK children.
        with open(os.devnull, 'rb') as empty:
            os.dup2(empty.fileno(), 0)
    with open(LOCK, 'w') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        return apply_locked()


def apply_locked():
    import urllib.request
    info = probe()
    if info['problems']:
        raise ValueError('；'.join(info['problems']))
    if info['bridge_active'] == 'active' and idle_state(info) != 'available':
        raise ValueError('既有橋接使用中或無法確認閒置，未安裝')
    source = pathlib.Path(__file__).resolve().parent
    # Verify/import SDK before touching vendor motion configuration; this constructs no robot.
    sys.path.insert(0, str(source))
    import install
    with __import__('tempfile').TemporaryDirectory(prefix='d1-sdk-preflight-') as temporary:
        install.extract_bundled_sdk(source/'sdk', pathlib.Path(temporary))
        install.verify_sdk(pathlib.Path(temporary))
    if info['bridge_active'] == 'active' and idle_state(info) != 'available':
        raise ValueError('檢查期間橋接已被占用，未安裝')
    config, start = loopback_text(text(FILES['sdk_config']), text(FILES['motion_start']))
    changed = config != text(FILES['sdk_config']) or start != text(FILES['motion_start'])
    base = BACKUPS/(time.strftime('%Y%m%d-%H%M%S', time.gmtime()) + '-' + uuid.uuid4().hex[:8])
    base.mkdir(parents=True);base.chmod(0o700)
    meta = {'files': {}, 'active': info['bridge_active'] == 'active',
            'enabled': info['bridge_enabled'] == 'enabled', 'vendor_changed': changed}
    for key, path in FILES.items():
        if path.exists():
            st = path.stat();shutil.copy2(path, base/key)
            meta['files'][key] = {'sha256': digest(path), 'mode': st.st_mode & 0o777, 'uid': st.st_uid, 'gid': st.st_gid}
        else:
            meta['files'][key] = None
    if ROOT.exists():
        copy_tree(ROOT, base/'runtime')
    (base/'snapshot.json').write_text(json.dumps(meta, indent=2))
    shutil.copy2(pathlib.Path(__file__), base/'provision.py')
    timer = 'd1-init-rollback-' + base.name
    run(['systemd-run', '--unit=' + timer, '--on-active=180s', '/usr/bin/python3.10', str(base/'provision.py'), '--rollback-if-uncommitted', str(base)])
    run(['systemctl', 'is-active', '--quiet', timer + '.timer'])
    handlers = {}
    if sys.platform == 'linux':
        def interrupted(_number, _frame):
            raise RuntimeError('初始化連線中斷，正在還原')
        for name in ('SIGINT', 'SIGTERM', 'SIGHUP'):
            number = getattr(signal, name)
            handlers[number] = signal.signal(number, interrupted)
    try:
        run(['systemctl', 'stop', 'd1-classroom'], timeout=15, check=False)
        run(['systemctl', 'disable', 'd1-classroom'], check=False)
        run(['bash', str(source/'install.sh'), '--no-start', '--interface', 'wlan0', '--user', 'firefly'], timeout=90)
        if changed:
            for key, value in [('sdk_config', config), ('motion_start', start)]:
                item = meta['files'][key]
                atomic(FILES[key], value.encode(), item['mode'], item['uid'], item['gid'])
        listening = '127.0.0.1:43997' in run(['ss', '-H', '-lun']).stdout
        if changed or not listening:
            meta['vendor_changed'] = True
            (base/'snapshot.json').write_text(json.dumps(meta, indent=2))
            run(['/usr/local/bin/robot-launch', 'restart', 'motion_control'], timeout=30)
        for _ in range(40):
            if '127.0.0.1:43997' in run(['ss', '-H', '-lun']).stdout:
                break
            time.sleep(.5)
        else:
            raise ValueError('原廠 SDK 未開始回環監聽')
        run(['systemctl', 'daemon-reload'])
        run(['systemctl', 'start', 'd1-classroom'])
        opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
        for _ in range(30):
            try:
                with opener.open('http://127.0.0.1:8765/status', timeout=1) as response:
                    status = json.load(response)
                if status.get('sdk_ready') and status.get('mac') == info['mac']:
                    break
            except (OSError, ValueError):
                pass
            time.sleep(.5)
        else:
            raise ValueError('橋接／SDK 就緒檢查失敗')
        if meta['enabled']:
            run(['systemctl', 'enable', 'd1-classroom'])
        (base/'committed').write_text('Setup health checks passed; no motion acceptance performed.\n')
        run(['systemctl', 'stop', timer + '.timer'])
        return {'initialized': True, 'mac': info['mac'], 'backup': str(base), 'sdk_ready': True,
                'autostart': meta['enabled'], 'motion_tested': False,
                'rollback_command': '/usr/bin/python3.10 ' + str(base/'provision.py') + ' --rollback ' + str(base)}
    except BaseException:
        restore(base)
        run(['systemctl', 'stop', timer + '.timer'], check=False)
        raise
    finally:
        for number, handler in handlers.items():
            signal.signal(number, handler)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument('--probe', action='store_true')
    group.add_argument('--apply', action='store_true')
    group.add_argument('--rollback')
    group.add_argument('--rollback-if-uncommitted')
    args = parser.parse_args()
    if args.probe:
        result = probe()
    elif args.apply:
        result = apply()
    else:
        if os.geteuid() != 0:
            raise ValueError('還原需要 sudo')
        result = restore(args.rollback or args.rollback_if_uncommitted, bool(args.rollback_if_uncommitted))
    print('D1_INIT_JSON=' + json.dumps(result, ensure_ascii=True), flush=True)


if __name__ == '__main__':
    try:
        main()
    except Exception as error:
        print('D1_INIT_ERROR=' + str(error), file=sys.stderr, flush=True)
        raise SystemExit(1)
