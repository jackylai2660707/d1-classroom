"""Prepare a NEW private Release; never overwrite an existing version manifest."""
from pathlib import Path
import argparse
import datetime
import hashlib
import json
import re
import shutil
import zipfile

ROOT=Path(__file__).resolve().parents[1]


def archive_references(destination):
    paths=sorted(p for p in (ROOT/'references').rglob('*') if p.is_file()
                 and not p.is_symlink() and '__pycache__' not in p.parts and 'node_modules' not in p.parts
                 and p.suffix not in ('.pyc','.previous','.log'))
    with zipfile.ZipFile(destination,'w',zipfile.ZIP_DEFLATED,compresslevel=6) as z:
        manifest=[]
        for p in paths:
            name=p.relative_to(ROOT).as_posix();z.write(p,name)
            manifest.append({'path':name,'bytes':p.stat().st_size,'sha256':hashlib.sha256(p.read_bytes()).hexdigest()})
        z.writestr('references/ARCHIVE-MANIFEST.json',json.dumps(manifest,ensure_ascii=False,indent=2))
    with zipfile.ZipFile(destination) as z:
        if z.testzip() is not None:raise ValueError('Reference archive CRC failed.')
    return len(paths)


def prepare(version,include_references=False):
    if not re.fullmatch(r'\d+\.\d+\.\d+',version):raise ValueError('Version must be MAJOR.MINOR.PATCH.')
    tag='v'+version
    manifest_path=ROOT/'releases'/(tag+'.json')
    destination=ROOT/'output/github-release'/tag
    # Check immutability before touching any existing asset or checksum file.
    if manifest_path.exists():raise ValueError('Version manifest already exists; use a NEW version: '+tag)
    if destination.exists():raise ValueError('Release work directory already exists; inspect it before retrying: '+str(destination))
    package=json.loads((ROOT/'d1-classroom/package.json').read_text(encoding='utf-8'))
    if package['version']!=version:raise ValueError('Update package.json and rebuild the delivery before preparing '+tag)
    suite=ROOT/'output/D1彩色課程完整套件.zip'
    setup=ROOT/'output/D1機器狗初始化包.zip'
    for path in (suite,setup):
        if not path.is_file():raise ValueError('Build delivery first: '+str(path))
        with zipfile.ZipFile(path) as z:
            if z.testzip() is not None:raise ValueError('Invalid delivery ZIP: '+str(path))
            if path==suite:
                title=z.read('D1彩色課程套件/先讀我.md').decode('utf-8-sig').splitlines()[0]
                if not title.endswith(' '+version):raise ValueError('Delivery version is stale; rebuild with build/deliver.py.')
    if include_references and not any((ROOT/'references').rglob('*.pdf')):
        raise ValueError('Full references are not restored; download the reference archive first or omit --include-references.')
    destination.mkdir(parents=True)
    pairs=[('classroom',destination/f'D1-Classroom-{version}-Windows-x64.zip'),
           ('setup',destination/f'D1-Robot-Setup-{version}.zip')]
    shutil.copy2(suite,pairs[0][1]);shutil.copy2(setup,pairs[1][1])
    count=0
    if include_references:
        reference=destination/f'D1-References-{version}.zip'
        count=archive_references(reference);pairs.append(('references',reference))
    assets=[{'role':role,'name':path.name,'bytes':path.stat().st_size,'sha256':hashlib.sha256(path.read_bytes()).hexdigest()}
            for role,path in pairs]
    manifest={'schemaVersion':1,'repository':'jackylai2660707/d1-classroom','tag':tag,'version':version,
              'preparedDate':datetime.date.today().isoformat(),'assets':assets}
    manifest_path.parent.mkdir(parents=True,exist_ok=True)
    # Exclusive creation is intentional: a tracked/published manifest is immutable.
    with manifest_path.open('x',encoding='utf-8') as output:
        output.write(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n')
    (destination/'SHA256SUMS.txt').write_text(''.join(a['sha256']+'  '+a['name']+'\n' for a in assets),encoding='utf-8')
    notes=f'''D1 機器狗實驗室 {version}：Windows 套件與自帶原廠 SDK 初始化包。

以 releases/{tag}.json 校驗大小與 SHA-256。此版本不覆寫任何已發佈標籤。實機驗收範圍以本版本的文檔和現場記錄為準。

維護者在確認本地成品及測試後，先 commit / push 新清單與程式，再執行：

```powershell
gh release create {tag} --repo jackylai2660707/d1-classroom --target main --draft --title "D1 {version}" --notes-file output/github-release/{tag}/release-notes.md
gh release upload {tag} --repo jackylai2660707/d1-classroom output/github-release/{tag}/*.zip output/github-release/{tag}/SHA256SUMS.txt
# 核對附件大小與 SHA-256 後才發佈
gh release edit {tag} --repo jackylai2660707/d1-classroom --draft=false
```

使用者下載：powershell -NoProfile -File scripts/fetch-release.ps1 -Manifest releases/{tag}.json -Replace
'''
    (destination/'release-notes.md').write_text(notes,encoding='utf-8')
    print(json.dumps({'tag':tag,'assets':assets,'referenceFiles':count},ensure_ascii=False))
    return manifest


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--version',required=True,help='New MAJOR.MINOR.PATCH version matching the rebuilt delivery.')
    parser.add_argument('--include-references',action='store_true')
    args=parser.parse_args()
    try:prepare(args.version,args.include_references)
    except (ValueError,OSError,KeyError,zipfile.BadZipFile) as error:raise SystemExit(str(error))


if __name__=='__main__':main()
