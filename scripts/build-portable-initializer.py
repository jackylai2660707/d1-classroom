"""Build a fully offline Windows x64 robot initializer. Never connects to a robot."""
import argparse
import hashlib
import json
import pathlib
import shutil
import struct
import urllib.request
import zipfile

ROOT = pathlib.Path(__file__).resolve().parents[1]
DOWNLOADS = ROOT/'local/bootstrap-downloads'
COMPONENTS = {
    'python-3.13.12-embed-amd64.zip': {
        'url': 'https://www.python.org/ftp/python/3.13.12/python-3.13.12-embed-amd64.zip',
        'sha256': '76f238f606250c87c6beac75dccd35ee99070a13490555936abb6cb64ecce3d0',
    },
    'plink-0.85-x64.exe': {
        'url': 'https://the.earth.li/~sgtatham/putty/0.85/w64/plink.exe',
        'sha256': '969f36879d5716aa1a9811f43a6a6510e8f08372dbeb9695b810b9c776f39c75',
    },
    'putty-LICENCE.html': {
        'url': 'https://www.chiark.greenend.org.uk/~sgtatham/putty/licence.html',
        'sha256': '643a9142655b672ef53f729dded917cff6e0f9dfa22d32629ff5ec137e15e3c5',
    },
}


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def x64(path):
    data = path.read_bytes()
    offset = struct.unpack_from('<I', data, 0x3c)[0]
    if data[:2] != b'MZ' or data[offset:offset+4] != b'PE\0\0' or struct.unpack_from('<H', data, offset+4)[0] != 0x8664:
        raise ValueError('Portable requires Windows x64 binary: ' + path.name)


def build(download=False):
    DOWNLOADS.mkdir(parents=True, exist_ok=True)
    for name, meta in COMPONENTS.items():
        target = DOWNLOADS/name
        if not target.exists():
            if not download:
                raise ValueError('Missing official component; run with --download: ' + name)
            with urllib.request.urlopen(meta['url'], timeout=45) as response:
                data = response.read()
            if hashlib.sha256(data).hexdigest() != meta['sha256']:
                raise ValueError('Official download hash mismatch: ' + name)
            target.write_bytes(data)
        if sha(target) != meta['sha256']:
            raise ValueError('Cached official component hash mismatch: ' + name)
    sdk = ROOT/'d1-classroom/bridge/sdk'
    vendor = json.loads((sdk/'manifest.json').read_text(encoding='utf-8'))
    if pathlib.Path(vendor['archive']).name != vendor['archive'] or sha(sdk/vendor['archive']) != vendor['sha256']:
        raise ValueError('Vendor SDK archive integrity failure')
    entries = [(ROOT/'scripts'/name, 'scripts/' + name) for name in ('initialize-robot.py', 'portable-launch.ps1')]
    entries += [(ROOT/'d1-classroom/bridge'/name, 'd1-classroom/bridge/' + name) for name in ('install.sh', 'install.py', 'provision.py', 'bridge.py', 'highlevel.py', 'README.setup.txt')]
    entries += [(sdk/name, 'd1-classroom/bridge/sdk/' + name) for name in (vendor['archive'], 'manifest.json', 'LICENSE.vendor.txt', 'README.vendor.md')]
    entries += [(ROOT/'d1-classroom/LICENSE', 'd1-classroom/LICENSE'), (ROOT/'docs/Portable初始化說明.txt', '先讀我.txt')]
    content_hash = hashlib.sha256(b''.join(p.read_bytes() for p, _ in entries) + json.dumps(COMPONENTS, sort_keys=True).encode() + pathlib.Path(__file__).read_bytes()).hexdigest()[:12]
    folder = ROOT/'output/portable'/('D1-Robot-Initializer-Portable-' + content_hash)
    if folder.exists():
        raise ValueError('Build directory already exists; preserving previous portable: ' + str(folder))
    folder.mkdir(parents=True)
    for source, name in entries:
        destination = folder/name;destination.parent.mkdir(parents=True, exist_ok=True);shutil.copy2(source, destination)
    python = folder/'runtime/python';python.mkdir(parents=True)
    with zipfile.ZipFile(DOWNLOADS/'python-3.13.12-embed-amd64.zip') as archive:
        for name in archive.namelist():
            path = pathlib.PurePosixPath(name)
            if path.is_absolute() or '..' in path.parts or len(path.parts) != 1:
                raise ValueError('Unexpected Python distribution entry')
        archive.extractall(python)
    putty = folder/'runtime/putty';putty.mkdir(parents=True)
    shutil.copy2(DOWNLOADS/'plink-0.85-x64.exe', putty/'plink.exe')
    shutil.copy2(DOWNLOADS/'putty-LICENCE.html', putty/'LICENCE.html')
    x64(python/'python.exe');x64(putty/'plink.exe')
    command = '@echo off\r\nsetlocal\r\n"%SystemRoot%\\System32\\chcp.com" 65001 >nul\r\n"%SystemRoot%\\System32\\WindowsPowerShell\\v1.0\\powershell.exe" -NoProfile -ExecutionPolicy Bypass -File "%~dp0scripts\\portable-launch.ps1" %*\r\nset "D1_EXIT=%errorlevel%"\r\necho.\r\npause\r\nexit /b %D1_EXIT%\r\n'
    (folder/'初始化新機器狗.cmd').write_bytes(command.encode('utf-8'))
    (folder/'檢查工具.cmd').write_bytes(command.replace(' %*', ' --portable-self-test').encode('utf-8'))
    manifest = {'format': 'd1-robot-initializer-portable', 'build': content_hash, 'target': 'Windows-x64',
                'components': COMPONENTS, 'files': [{'path': p.relative_to(folder).as_posix(), 'sha256': sha(p)} for p in sorted(folder.rglob('*')) if p.is_file()]}
    (folder/'PORTABLE-MANIFEST.json').write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding='utf-8')
    output = folder.with_suffix('.zip')
    with zipfile.ZipFile(output, 'x', zipfile.ZIP_DEFLATED, compresslevel=6) as archive:
        for path in sorted(folder.rglob('*')):
            if path.is_file():archive.write(path, folder.name + '/' + path.relative_to(folder).as_posix())
    with zipfile.ZipFile(output) as archive:
        if archive.testzip() is not None:raise ValueError('Portable ZIP CRC failure')
    output.with_suffix('.sha256').write_text(sha(output) + '  ' + output.name + '\n', encoding='ascii')
    print(json.dumps({'directory': str(folder), 'zip': str(output), 'sha256': sha(output), 'bytes': output.stat().st_size}, ensure_ascii=False))
    return folder, output


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--download', action='store_true', help='Only build-time downloads from pinned official URLs')
    build(parser.parse_args().download)
