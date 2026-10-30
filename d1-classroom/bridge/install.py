"""Run on the robot: sudo bash install.sh. Vendor SDK is bundled. Standard library only."""
import argparse
import importlib.util
import json
import os
import pathlib
import platform
import re
import shutil
import subprocess
import sys
import time
import urllib.request
import hashlib
import tempfile
import zipfile

ROOT = pathlib.Path('/opt/d1-classroom')
NET = pathlib.Path('/sys/class/net')
BUNDLE = pathlib.Path(__file__).resolve().parent/'sdk'


def architecture(machine=None):
    name = machine or platform.machine()
    if name in ('aarch64', 'arm64'):
        return 'aarch64'
    if name in ('x86_64', 'AMD64'):
        return 'x86_64'
    raise ValueError('原廠 SDK 不支援此 CPU 架構：'+name)


def extract_bundled_sdk(bundle, destination, machine=None):
    """Check the original archive and extract only the exact files for this robot."""
    arch = architecture(machine)
    manifest = json.loads((bundle/'manifest.json').read_text(encoding='utf-8'))
    name = manifest['archive']
    if pathlib.Path(name).name != name or '/' in name or '\\' in name:
        raise ValueError('SDK 壓縮檔名稱無效')
    archive = bundle/name
    if hashlib.sha256(archive.read_bytes()).hexdigest() != manifest['sha256']:
        raise ValueError('原廠 SDK 完整性檢查失敗，請重新解壓完整初始化包')
    names = [f'libmc_sdk_zsl_1_{arch}.so', f'mc_sdk_zsl_1_py.cpython-310-{arch}-linux-gnu.so']
    with zipfile.ZipFile(archive) as source:
        # Exact entries only: never extract arbitrary archive paths onto the robot.
        contents = {name: source.read(f'agibot_D1_Edu-Ultra/lib/zsl-1/{arch}/{name}') for name in names}
        contents['LICENSE.vendor.txt'] = source.read('agibot_D1_Edu-Ultra/LICENSE')
    destination.mkdir(parents=True, exist_ok=True)
    for name, data in contents.items():
        (destination/name).write_bytes(data)
        (destination/name).chmod(0o644)
    return archive


def write_binary_changed(path, source):
    if path.exists() and hashlib.sha256(path.read_bytes()).digest() == hashlib.sha256(source.read_bytes()).digest():
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        shutil.copy2(path, path.with_name(path.name+'.previous'))
    temporary = path.with_name(path.name+'.new')
    shutil.copyfile(source, temporary)
    temporary.chmod(0o644)
    temporary.replace(path)


def verify_sdk(directory):
    env = {**os.environ, 'PYTHONPATH': str(directory), 'LD_LIBRARY_PATH': f'{directory}:/opt/export/mc/bin'}
    subprocess.run([sys.executable, '-c', 'import mc_sdk_zsl_1_py'], env=env, check=True, timeout=15)


def install_bundled_sdk(bundle=BUNDLE):
    if not (bundle/'manifest.json').is_file():
        raise ValueError('初始化包缺少 sdk/manifest.json，請重新解壓完整包，勿只複製 install.sh')
    with tempfile.TemporaryDirectory(prefix='d1-sdk-') as temporary:
        stage = pathlib.Path(temporary)
        archive = extract_bundled_sdk(bundle, stage)
        verify_sdk(stage)  # Check ABI and dependent libraries before replacing the installed SDK.
        for source in stage.iterdir():
            write_binary_changed(ROOT/'sdk'/source.name, source)
        write_binary_changed(ROOT/'vendor'/archive.name, archive)
        write_binary_changed(ROOT/'vendor'/'manifest.json', bundle/'manifest.json')
        write_binary_changed(ROOT/'vendor'/'LICENSE.vendor.txt', bundle/'LICENSE.vendor.txt')
    return ROOT/'sdk'


def wifi_interface(requested=None, root=NET):
    choices = [p.name for p in root.iterdir() if (p/'wireless').exists() or (p/'phy80211').exists()]
    if requested:
        if requested not in choices:
            raise ValueError('指定網卡不是可識別的 Wi-Fi 網卡')
        return requested
    if len(choices) != 1:
        raise ValueError('無法唯一選出 Wi-Fi 網卡，請用 --interface 指定：' + ', '.join(choices))
    return choices[0]


def sdk_directory(requested=None):
    if requested:
        base = pathlib.Path(requested).resolve()
        arch = architecture()
        for candidate in [base, base/'lib'/'zsl-1'/arch]:
            if list(candidate.glob('mc_sdk_zsl_1_py*.so')):
                return candidate
        raise ValueError('SDK 目錄內找不到本機型的 mc_sdk_zsl_1_py*.so')
    if list((ROOT/'sdk').glob('mc_sdk_zsl_1_py*.so')):
        return ROOT/'sdk'
    spec = importlib.util.find_spec('mc_sdk_zsl_1_py')
    if spec and spec.origin:
        return pathlib.Path(spec.origin).parent
    raise ValueError('找不到指定 SDK；正常安裝請使用完整初始化包，不需要 --sdk-dir')


def service_text(python, sdk, user):
    # systemd Environment uses quoted assignments; reject control characters in supplied paths.
    for value in [str(python), str(sdk), user]:
        if any(c in value for c in '\n\r"%\\'):
            raise ValueError('Python／SDK 路徑或帳號包含不支援的字元')
    return f'''[Unit]
Description=D1 classroom MAC discovery and control bridge
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
User={user}
WorkingDirectory=/opt/d1-classroom
Environment="PYTHONPATH={sdk}" "LD_LIBRARY_PATH={sdk}:/opt/export/mc/bin" "PYTHONUNBUFFERED=1"
ExecStart="{python}" /opt/d1-classroom/bridge.py --config /opt/d1-classroom/robot.json
Restart=on-failure
RestartSec=2
TimeoutStopSec=5
NoNewPrivileges=true

[Install]
WantedBy=multi-user.target
'''


def write_changed(path, text):
    """Idempotent install with one previous-version backup, never touch vendor configuration."""
    if path.exists() and path.read_text(encoding='utf-8') == text:
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        shutil.copy2(path, path.with_name(path.name+'.previous'))
    temporary = path.with_name(path.name+'.new')
    temporary.write_text(text, encoding='utf-8', newline='\n')
    temporary.chmod(0o644)
    temporary.replace(path)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--interface')
    parser.add_argument('--sdk-dir', help='僅供技術人員覆寫；預設自動安裝隨包原廠 SDK')
    parser.add_argument('--sdk-address', help='SDK 的機內地址；auto 代表使用 Wi-Fi 當前地址')
    parser.add_argument('--user', default=os.environ.get('SUDO_USER') or 'root')
    args = parser.parse_args()
    if sys.platform != 'linux' or os.geteuid() != 0:
        raise SystemExit('請在機器狗 Linux 上執行 sudo bash install.sh')
    if sys.version_info[:2] != (3, 10):
        raise SystemExit('隨附原廠 SDK 需要 CPython 3.10。例：sudo D1_PYTHON=/usr/bin/python3.10 bash install.sh')
    if not shutil.which('systemctl'):
        raise SystemExit('需要 systemd；未安裝服務')
    import pwd
    pwd.getpwnam(args.user)
    old_path = ROOT/'robot.json'
    old = json.loads(old_path.read_text(encoding='utf-8-sig')) if old_path.exists() else {}
    interface = wifi_interface(args.interface or old.get('interface'))
    from bridge import read_mac, interface_ip
    mac = read_mac(interface)
    interface_ip(interface)  # Require DHCP to have supplied an IPv4 address before claiming success.
    sdk = sdk_directory(args.sdk_dir) if args.sdk_dir else install_bundled_sdk()
    if args.sdk_dir:
        verify_sdk(sdk)
    local = args.sdk_address or old.get('sdk_local_ip', '127.0.0.1')
    robot = args.sdk_address or old.get('sdk_robot_ip', '127.0.0.1')
    import ipaddress
    for address in [local, robot]:
        if address != 'auto':
            ipaddress.IPv4Address(address)
    config = {'interface': interface, 'sdk_local_ip': local, 'sdk_robot_ip': robot, 'sdk_dir': str(sdk)}
    unit = service_text(pathlib.Path(sys.executable).resolve(), sdk, args.user)
    # Resolve all prerequisites before replacing the installed application.
    source = pathlib.Path(__file__).resolve().parent/'bridge.py'
    write_changed(ROOT/'bridge.py', source.read_text(encoding='utf-8'))
    write_changed(old_path, json.dumps(config, ensure_ascii=False, indent=2)+'\n')
    write_changed(pathlib.Path('/etc/systemd/system/d1-classroom.service'), unit)
    write_changed(ROOT/'機身標籤.txt', f'機器狗 · {mac[-5:]}\nWi-Fi MAC: {mac}\n')
    subprocess.run(['systemctl', 'daemon-reload'], check=True)
    subprocess.run(['systemctl', 'enable', 'd1-classroom.service'], check=True)
    subprocess.run(['systemctl', 'restart', 'd1-classroom.service'], check=True)
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
    ready = False
    for _ in range(30):
        try:
            with opener.open('http://127.0.0.1:8765/status', timeout=1) as response:
                status = json.load(response)
            if status.get('sdk_ready') and status.get('mac') == mac:
                ready = True
                break
        except (OSError, ValueError):
            pass
        time.sleep(1)
    if not ready:
        # A failed install must not leave a partially configured bridge advertising itself.
        subprocess.run(['systemctl', 'disable', '--now', 'd1-classroom.service'], check=False)
        raise SystemExit('初始化未通過，服務已停用。請查 journalctl -u d1-classroom -n 50，核對原廠 SDK 機內地址與通訊配置；修正後重跑本腳本。未執行任何動作測試。')
    print(f'初始化成功\n機身標籤：機器狗 · {mac[-5:]}\nWi-Fi MAC：{mac}\n橋接／SDK：正常\nSDK 目錄：{sdk}\n開機自啟：已啟用\n標籤檔：{ROOT}/機身標籤.txt\n尚需另一台電腦掃描及現場停止驗收。')


if __name__ == '__main__':
    try:
        main()
    except (ValueError, OSError, subprocess.SubprocessError, KeyError, zipfile.BadZipFile) as error:
        raise SystemExit(f'初始化失敗：{error}')
