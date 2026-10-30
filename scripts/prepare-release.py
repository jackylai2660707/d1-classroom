"""Prepare private Release assets and their committed checksum manifest."""
from pathlib import Path
import hashlib
import json
import shutil
import zipfile

ROOT=Path(__file__).resolve().parents[1]
DEST=ROOT/'output/github-release'
TAG='v2.0.0'


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
    with zipfile.ZipFile(destination) as z:assert z.testzip() is None
    return len(paths)


def main():
    DEST.mkdir(parents=True,exist_ok=True)
    suite=ROOT/'output/D1彩色課程完整套件.zip'
    setup=ROOT/'output/D1機器狗初始化包.zip'
    for path in (suite,setup):assert path.is_file(),f'Build delivery first: {path}'
    classroom=DEST/'D1-Classroom-2.0.0-Windows-x64.zip'
    robot=DEST/'D1-Robot-Setup-2.0.0.zip'
    references=DEST/'D1-References-2026-10-30.zip'
    shutil.copy2(suite,classroom);shutil.copy2(setup,robot)
    count=archive_references(references)
    assets=[]
    for role,path in [('classroom',classroom),('setup',robot),('references',references)]:
        with zipfile.ZipFile(path) as z:assert z.testzip() is None
        assets.append({'role':role,'name':path.name,'bytes':path.stat().st_size,'sha256':hashlib.sha256(path.read_bytes()).hexdigest()})
    manifest={'schemaVersion':1,'repository':'jackylai2660707/d1-classroom','tag':TAG,'version':'2.0.0','preparedDate':'2026-10-30','assets':assets}
    (ROOT/'releases').mkdir(exist_ok=True)
    (ROOT/'releases/v2.0.0.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    (DEST/'SHA256SUMS.txt').write_text(''.join(a['sha256']+'  '+a['name']+'\n' for a in assets),encoding='utf-8')
    (DEST/'release-notes.md').write_text('''D1 機器狗實驗室 2.0：公司電腦接手與實機驗收版本。

包含 16 課離線教程、Windows x64 工具、三份列印資料、32 份起步檔、示例圖片、備用模型、自帶原廠 SDK 的初始化包。參考資料 ZIP 完整保留原廠手冊、三維模型與歷史教材 / 建置。

先 clone 私人倉庫，再執行 scripts/fetch-release.ps1；需要原廠完整參考資料時加 -IncludeReferences。腳本依 Git 內的 releases/v2.0.0.json 核對 SHA-256。完整步驟見 docs/公司電腦實機測試.md。

軟體與假 SDK 已驗證；沒有連接實體機器狗。韌體相容、初始化自啟、動作、物理停止、RTSP 與整班負載須在公司現場驗收。未驗收前保持練習模式。
''',encoding='utf-8')
    print(json.dumps({'tag':TAG,'assets':assets,'referenceFiles':count},ensure_ascii=False))


if __name__=='__main__':main()
