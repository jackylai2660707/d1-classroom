"""Enter one robot IPv4 address to check, back up and initialize the verified image."""
import argparse
import base64
import contextlib
import csv
import hashlib
import ipaddress
import json
import os
import pathlib
import re
import shlex
import shutil
import subprocess
import sys
import tempfile
import uuid
import zipfile

ROOT = pathlib.Path(__file__).resolve().parents[1]
BRIDGE = ROOT/'d1-classroom'/'bridge'
DEFAULT_USER = 'firefly'
LAN = tuple(ipaddress.IPv4Network(n) for n in ('10.0.0.0/8', '172.16.0.0/12', '192.168.0.0/16'))


def address(value):
    ip = ipaddress.IPv4Address(value.strip())
    if not any(ip in network for network in LAN):
        raise ValueError('只接受課室私有局域網 IPv4 地址')
    return str(ip)


def execute(args, data=None, timeout=20, check=True):
    flags = subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
    try:
        result = subprocess.run(args, input=data, capture_output=True, timeout=timeout, creationflags=flags)
    except subprocess.TimeoutExpired:
        raise RuntimeError('連線步驟逾時。如果已開始機身安裝，保持狗開機至少 3 分鐘，讓保護性還原完成後再檢查；未假定成功。') from None
    if check and result.returncode:
        message = result.stderr.decode('utf-8', errors='replace')[-2000:]
        raise RuntimeError(message or '外部工具執行失敗')
    return result


def executable(name):
    found = shutil.which(name)
    if not found and name == 'plink' and os.name == 'nt':
        candidate = pathlib.Path(os.environ.get('ProgramFiles', r'C:\Program Files'))/'PuTTY'/'plink.exe'
        if candidate.is_file():
            found = str(candidate)
    if not found:
        raise ValueError('缺少 ' + name + '；此工具使用 Windows OpenSSH 與 PuTTY Plink，不自動下載依賴')
    return found


def fingerprint(ip, keyscan):
    result = execute([keyscan, '-T', '5', '-t', 'ed25519', ip], timeout=10, check=False)
    keys = set()
    for line in result.stdout.decode('ascii', errors='replace').splitlines():
        fields = line.split()
        if len(fields) == 3 and fields[1] == 'ssh-ed25519':
            blob = base64.b64decode(fields[2], validate=True)
            keys.add('SHA256:' + base64.b64encode(hashlib.sha256(blob).digest()).decode().rstrip('='))
    if len(keys) != 1:
        raise ValueError('無法唯一取得 SSH 主機金鑰，請檢查 IP、電源與局域網；未嘗試登入')
    return keys.pop()


@contextlib.contextmanager
def credential_file(password):
    """Plink reads a short-lived, ACL-restricted file; never put a password in argv."""
    directory = ROOT/'local'/'robot-init'
    directory.mkdir(parents=True, exist_ok=True)
    descriptor, name = tempfile.mkstemp(prefix='ssh-', suffix='.tmp', dir=directory)
    path = pathlib.Path(name)
    os.close(descriptor)
    try:
        if os.name == 'nt':
            who = execute(['whoami', '/user', '/fo', 'csv', '/nh']).stdout.decode(errors='replace')
            sid = next((cell for row in csv.reader(who.splitlines()) for cell in row if re.fullmatch(r'S-1-5-[0-9-]+', cell)), None)
            if not sid:
                raise ValueError('無法取得目前使用者 SID，未建立密碼檔')
            execute(['icacls', str(path), '/inheritance:r', '/grant:r', '*' + sid + ':(F)', '*S-1-5-18:(F)'])
        else:
            path.chmod(0o600)
        path.write_bytes(password.encode('utf-8') + b'\n')
        yield path
    finally:
        path.unlink(missing_ok=True)


class SSH:
    def __init__(self, ip, key, password_file, plink):
        self.prefix = [plink, '-batch', '-ssh', '-4', '-T', '-noagent', '-noshare', '-no-antispoof',
                       '-l', DEFAULT_USER, '-P', '22', '-hostkey', key, '-pwfile', str(password_file), ip]

    def run(self, command, data=None, timeout=25):
        return execute(self.prefix + [command], data, timeout).stdout.decode('utf-8', errors='replace')


def result_json(output):
    lines = [line[len('D1_INIT_JSON='):] for line in output.splitlines() if line.startswith('D1_INIT_JSON=')]
    if len(lines) != 1:
        raise ValueError('機身回覆格式無效，未假定初始化成功')
    return json.loads(lines[0])


def pin_identity(registry, mac, key):
    known = json.loads(registry.read_text(encoding='utf-8')) if registry.exists() else {}
    if mac in known and known[mac] != key:
        raise ValueError('同一 MAC 的 SSH 金鑰與記錄不符，停止；需人工核對，未覆寫信任記錄')
    known[mac] = key
    registry.parent.mkdir(parents=True, exist_ok=True)
    temporary = registry.with_suffix('.new')
    temporary.write_text(json.dumps(known, indent=2), encoding='utf-8')
    temporary.replace(registry)


def make_package():
    sdk = BRIDGE/'sdk'
    manifest = json.loads((sdk/'manifest.json').read_text(encoding='utf-8'))
    archive = sdk/manifest['archive']
    if archive.parent.resolve() != sdk.resolve() or hashlib.sha256(archive.read_bytes()).hexdigest() != manifest['sha256']:
        raise ValueError('隨包原廠 SDK 雜湊不符')
    files = [(BRIDGE/name, 'd1-setup/' + name) for name in ('install.sh', 'install.py', 'bridge.py', 'highlevel.py', 'provision.py')]
    files += [(ROOT/'d1-classroom'/'LICENSE', 'd1-setup/LICENSE')]
    files += [(sdk/name, 'd1-setup/sdk/' + name) for name in (manifest['archive'], 'manifest.json', 'LICENSE.vendor.txt', 'README.vendor.md')]
    digest = hashlib.sha256(b''.join(p.read_bytes() for p, _ in files)).hexdigest()[:12]
    folder = ROOT/'local'/'robot-init';folder.mkdir(parents=True, exist_ok=True)
    target = folder/('d1-setup-' + digest + '.zip')
    with zipfile.ZipFile(target, 'w', zipfile.ZIP_DEFLATED) as output:
        for path, name in files:
            output.write(path, name)
    with zipfile.ZipFile(target) as output:
        if output.testzip() is not None:
            raise ValueError('初始化包 CRC 檢查失敗')
        for path, name in files:
            if output.read(name) != path.read_bytes():
                raise ValueError('初始化包內容不同步：' + name)
    return target, hashlib.sha256(target.read_bytes()).hexdigest()


def extraction_code(archive, stage, sha):
    # JSON string literals are Python-compatible here; paths contain no user shell text.
    return ("import pathlib,hashlib,zipfile,stat; "
            f"p=pathlib.Path({str(archive)!r});dest=pathlib.Path({str(stage)!r}); "
            f"assert hashlib.sha256(p.read_bytes()).hexdigest()=={sha!r}; "
            "z=zipfile.ZipFile(p);names=z.namelist(); "
            "assert len(names)==len(set(names)); "
            "assert all(not pathlib.PurePosixPath(n).is_absolute() and '..' not in pathlib.PurePosixPath(n).parts and pathlib.PurePosixPath(n).parts[0]=='d1-setup' and not stat.S_ISLNK(i.external_attr>>16) for n,i in zip(names,z.infolist())); "
            "assert z.testzip() is None;dest.mkdir(exist_ok=False);z.extractall(dest);z.close()")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('ip', nargs='?')
    parser.add_argument('--check-only', action='store_true', help='只讀檢查，不上傳或安裝')
    parser.add_argument('--prepare-only', action='store_true', help='只在本機建立並核對初始化包，不連機器狗')
    args = parser.parse_args()
    archive, sha = make_package()
    if args.prepare_only:
        print('初始化包：' + str(archive));print('SHA-256：' + sha);return
    print('請先讓狗趴穩、停止程式並斷開學生工坊；現場備妥硬體停止方式。')
    print('此流程可能接管 SDK、重啟原廠運控；不測動作、不改 Wi-Fi、不新增開機自啟。')
    ip = address(args.ip or input('新機器狗 IPv4：'))
    plink, keyscan = executable('plink'), executable('ssh-keyscan')
    if '-pwfile' not in execute([plink, '--help']).stdout.decode(errors='replace'):
        raise ValueError('PuTTY Plink 版本不支援安全的密碼檔登入')
    key = fingerprint(ip, keyscan)
    print('SSH 指紋：' + key)
    # Factory credentials are supplied by the operator; never save them in results or argv.
    password = os.environ.get('D1_SSH_PASSWORD', 'firefly')
    report = {'ip': ip, 'host_key': key, 'archive_sha256': sha, 'check_only': args.check_only}
    results = ROOT/'field-results'/'initialization';results.mkdir(parents=True, exist_ok=True)
    report_path = results/(ip + '-' + uuid.uuid4().hex[:8] + '.json')
    try:
        with credential_file(password) as secret:
            ssh = SSH(ip, key, secret, plink)
            payload = base64.b64encode((BRIDGE/'provision.py').read_bytes()).decode()
            probe_command = 'python3 -c ' + shlex.quote("import base64;exec(compile(base64.b64decode(" + repr(payload) + "),'provision.py','exec'))") + ' --probe'
            if len(subprocess.list2cmdline(ssh.prefix + [probe_command])) > 30000:
                raise ValueError('檢查程式超過 Windows 命令長度限制')
            info = result_json(ssh.run(probe_command, timeout=30))
            report['preflight'] = info
            if info['problems']:
                raise ValueError('；'.join(info['problems']))
            if info['home'] != '/home/firefly':
                raise ValueError('登入家目錄不是預期位置，停止')
            pin_identity(results/'known-hosts-by-mac.json', info['mac'], key)
            print('機身 MAC：' + info['mac'] + '；運控版本：' + info['motion_version'])
            if args.check_only:
                report['result'] = {'checked': True, 'installed': False}
                print('只讀檢查通過，未上傳或修改機身。');return
            token = uuid.uuid4().hex
            remote_archive = pathlib.PurePosixPath(info['home'])/('d1-init-' + token + '.zip')
            stage = pathlib.PurePosixPath(info['home'])/('d1-init-' + token)
            print('上傳並驗證初始化包…')
            ssh.run('umask 077; cat > ' + shlex.quote(str(remote_archive)), archive.read_bytes(), timeout=90)
            ssh.run(shlex.quote(info['python']) + ' -c ' + shlex.quote(extraction_code(remote_archive, stage, sha)), timeout=30)
            command = 'sudo -S -p ' + shlex.quote('') + ' -- ' + shlex.quote(info['python']) + ' ' + shlex.quote(str(stage/'d1-setup'/'provision.py')) + ' --apply'
            print('檢查、備份與安裝中；失敗會嘗試還原，請勿關機…')
            final = result_json(ssh.run(command, (password + '\n').encode(), timeout=160))
            if not final.get('initialized') or final.get('mac') != info['mac']:
                raise ValueError('初始化回覆未通過核對')
            report['result'] = final
            print('初始化成功；MAC：' + final['mac'])
            print('備份：' + final['backup'])
            print('開機自啟：' + ('保留原有啟用狀態' if final['autostart'] else '未啟用；重開機後需手動啟動橋接'))
            print('未進行動作／停止／相機驗收。現在可到學生工坊掃描並核對 MAC。')
    except Exception as error:
        safe = str(error).replace(password, '[hidden]')
        report['error'] = safe
        raise RuntimeError(safe) from None
    finally:
        report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
        print('本機記錄：' + str(report_path))


if __name__ == '__main__':
    try:
        if hasattr(sys.stdout, 'reconfigure'):
            sys.stdout.reconfigure(encoding='utf-8')
        main()
    except (Exception, KeyboardInterrupt) as error:
        print('初始化未完成：' + str(error), file=sys.stderr)
        raise SystemExit(1)
