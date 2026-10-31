"""Publish the integrated 2.0 course, app, self-contained setup and source ZIP."""
from pathlib import Path
import csv
import hashlib
import json
import shutil
import zipfile
import runpy

R = Path(__file__).resolve().parents[1]
O = R.parent/'output'/'D1彩色課程套件'
VERSION = json.loads((R/'package.json').read_text(encoding='utf-8'))['version']


def copy(source, destination):
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, destination)


def source_files():
    files = []
    for name in ['app', 'bridge', 'tests', 'curriculum', 'courseware']:
        files += [p for p in (R/name).rglob('*') if p.is_file() and '__pycache__' not in p.parts and p.suffix not in ('.pyc', '.previous') and p.name not in ('robot.json', 'robots.json')]
    lessons = json.loads((R/'curriculum/lessons.json').read_text(encoding='utf-8'))
    images = {l['tutorial']['image'] for l in lessons} | {'robot-0.jpg', 'workshop-current.png', 'scan-current.png'}
    files += [R/'assets'/name for name in sorted(images)]
    files += [R/'build'/name for name in ['bundle.cjs', 'package.cjs', 'deliver.py', 'courseware.py', 'printables.py', 'capture-courseware.cjs', 'README.md']]
    files += [R/name for name in ['package.json', 'pnpm-lock.yaml', 'pnpm-workspace.yaml', 'requirements-author.txt', 'README.md', 'LICENSE', '技術部署與實機驗收.md', '連線使用說明.md']]
    return sorted(files)


def write_zip(destination, entries):
    temporary = destination.with_suffix('.zip.new')
    with zipfile.ZipFile(temporary, 'w', zipfile.ZIP_DEFLATED, compresslevel=6) as archive:
        for source, name in entries:
            archive.write(source, name)
    with zipfile.ZipFile(temporary) as archive:
        if archive.testzip() is not None:
            raise SystemExit('ZIP CRC failed: '+str(destination))
    temporary.replace(destination)


def main():
    if not (O/'學生工具/D1學生工坊/resources/app.asar').is_file():
        raise SystemExit('請先執行 pnpm run bundle 與 pnpm run package')
    for name in ['課堂工作紙.pdf','教師帶課手冊.pdf','操作與試教記錄.pdf']:
        p=O/'列印資料'/name
        if not p.is_file() or not p.read_bytes().startswith(b'%PDF'):
            raise SystemExit('請先用 build/printables.py 產生 '+name)
    if list(O.glob('*.docx')) or list(O.glob('*.pdf')) or (O/'投影課件').exists():
        raise SystemExit('正式目錄仍有 1.0 舊教材，先移到 references/歷史教材再發佈')
    sdk=R/'bridge/sdk'
    manifest=json.loads((sdk/'manifest.json').read_text(encoding='utf-8'))
    archive_path=sdk/manifest['archive']
    assert archive_path.parent.resolve()==sdk.resolve()
    assert hashlib.sha256(archive_path.read_bytes()).hexdigest()==manifest['sha256']
    with zipfile.ZipFile(archive_path) as archive:
        assert archive.testzip() is None
        assert archive.read('agibot_D1_Edu-Ultra/LICENSE')==(sdk/'LICENSE.vendor.txt').read_bytes()
        for arch in ['aarch64','x86_64']:
            for name in [f'libmc_sdk_zsl_1_{arch}.so',f'mc_sdk_zsl_1_py.cpython-310-{arch}-linux-gnu.so']:
                archive.getinfo(f'agibot_D1_Edu-Ultra/lib/zsl-1/{arch}/{name}')
    runpy.run_path(str(R/'build/courseware.py'),run_name='__main__')
    workspace_report=R.parent/'docs/整套教程驗收紀錄.md'
    report=workspace_report if workspace_report.is_file() else R/'courseware/驗收紀錄.md'
    if workspace_report.is_file():copy(workspace_report,R/'courseware/驗收紀錄.md')
    for source,destination in [
        (R.parent/'docs/學生工坊擴充指令.md',O/'學生工坊擴充指令.md'),
        (R.parent/'docs/2.1.0打包紀錄.md',O/'2.1.0打包紀錄.md'),
        (R.parent/'docs/一鍵初始化機器狗.md',O/'技術人員部署/一鍵初始化機器狗.md'),
        (R.parent/'docs/橋接首次連線準備.md',O/'技術人員部署/橋接首次連線準備.md'),
        (R/'技術部署與實機驗收.md',O/'技術人員部署/技術部署與實機驗收.md'),
        (R/'README.md',O/'技術人員部署/原始碼使用說明.md'),
        (R/'連線使用說明.md',O/'連線使用說明.md'),
        (R/'LICENSE',O/'LICENSE'),
        (sdk/'LICENSE.vendor.txt',O/'技術人員部署/原廠SDK授權.txt'),
        (report,O/'驗收狀態.md')]:
        copy(source,destination)
    # Preserve the PC initializer's workspace-relative layout in a self-contained folder.
    initializer=O/'技術人員部署/一鍵初始化'
    for name in ['initialize-robot.py','initialize-robot.cmd']:
        copy(R.parent/'scripts'/name,initializer/'scripts'/name)
    copy(R.parent/'初始化新機器狗.cmd',initializer/'初始化新機器狗.cmd')
    for name in ['install.sh','install.py','bridge.py','highlevel.py','provision.py']:
        copy(R/'bridge'/name,initializer/'d1-classroom/bridge'/name)
    for file in sorted(sdk.iterdir()):
        if file.is_file():copy(file,initializer/'d1-classroom/bridge/sdk'/file.name)
    copy(R/'LICENSE',initializer/'d1-classroom/LICENSE')
    (O/'先讀我.md').write_text(f'''# D1 機器狗實驗室 {VERSION}

完整解壓後，雙擊「使用說明.html」進入課程首頁。

- 學生：雙擊「啟動學生工坊.cmd」，先練習，再按 MAC 掃描連線。工具內「本課教程」可開啟對應課程。
- 新功能：上方可展開動作與 Python 範例；見「學生工坊擴充指令.md」。後空翻預設隱藏，所有高風險動作須逐次明確允許，尚未完成新動作實機驗收。
- 新狗：技術人員部署/一鍵初始化/初始化新機器狗.cmd，輸入 IP；先閱讀同目錄上層的初始化說明。只自動處理已驗證韌體，不新增開機自啟，不測動作。
- 教師：首頁的「教師帶課」包含節奏、分工、輪次、評量與備案。
- 技術人員：首頁的「設備部署」提供同一初始化命令；技術人員部署/d1-setup.zip 已含原廠 SDK。
- 列印：列印資料/ 內有 16 頁工作紙、18 頁教師手冊、5 頁操作、試教與色卡。

教程是離線網頁，不需要伺服器或帳戶。第 12 課的自主訓練需要 Teachable Machine 網站及網路；備用模型可離線完成分類測試，自主訓練另補。

學校電腦會還原時，把專案、模型、測試圖片與匯出的學習記錄保存到老師指定的持久位置。專案不包含模型。

原廠 SDK 已附，不需另找。Linux 機身仍需相容的原廠運行環境與 CPython 3.10。真機初始化、動作、停止及整班網路負載仍須按現場驗收表完成，未驗收前保持練習模式。

本版不含 Word 或 PPT。原始碼 ZIP 用來後續修改；檔案清單.csv 提供每個檔案的 SHA-256。
''',encoding='utf-8')
    (O/'套件目錄.txt').write_text('''D1 機器狗實驗室
  使用說明.html              課程首頁與統一入口
  啟動學生工坊.cmd            啟動 Windows 成品
  教程/                      16 課、學生開始、教師帶課、設備部署
  列印資料/                  三份可列印 PDF
  學生工具/D1學生工坊/        Windows x64 程式及必要檔案
  配套檔案/                  32 份起步專案、示例圖片與模型
  技術人員部署/              自帶 SDK 初始化 ZIP 與技術文件
  D1學生工坊與教材原始碼.zip   可重建的原始碼
  驗收狀態.md                軟體結果與實機待驗項目
  檔案清單.csv               檔案大小與 SHA-256
''',encoding='utf-8')
    setup=O.parent/'D1機器狗初始化包.zip'
    setup_entries=[(R/'bridge'/name,'d1-setup/'+name) for name in ['bridge.py','highlevel.py','provision.py','install.py','install.sh']]
    setup_entries += [(p,'d1-setup/sdk/'+p.name) for p in sorted(sdk.iterdir()) if p.is_file()]
    setup_entries += [(R/'bridge/README.setup.txt','d1-setup/'+name) for name in ['README.md','README.txt']]
    setup_entries += [(R/'技術部署與實機驗收.md','d1-setup/技術部署與實機驗收.md')]
    setup_entries += [(R/'LICENSE','d1-setup/LICENSE')]
    write_zip(setup,setup_entries);copy(setup,O/'技術人員部署/d1-setup.zip')
    source=O/'D1學生工坊與教材原始碼.zip'
    entries=[(p,'d1-classroom/'+p.relative_to(R).as_posix()) for p in source_files()]
    entries.append((O/'學生工具/D1學生工坊/THIRD-PARTY-NOTICES.txt','d1-classroom/THIRD-PARTY-NOTICES.txt'))
    for name in ['initialize-robot.py','initialize-robot.cmd']:
        entries.append((R.parent/'scripts'/name,'scripts/'+name))
    for name in ['一鍵初始化機器狗.md','學生工坊擴充指令.md','橋接首次連線準備.md']:
        entries.append((R.parent/'docs'/name,'docs/'+name))
    entries.append((R.parent/'初始化新機器狗.cmd','初始化新機器狗.cmd'))
    write_zip(source,entries)
    manifest_path=O/'檔案清單.csv'
    files=sorted(p for p in O.rglob('*') if p.is_file() and p!=manifest_path)
    assert not any(p.suffix in ('.docx','.pptx','.new','.previous','.pyc') or '__pycache__' in p.parts for p in files)
    assert len(list((O/'教程').glob('lesson-*.html')))==16
    with manifest_path.open('w',encoding='utf-8-sig',newline='') as output:
        writer=csv.writer(output);writer.writerow(['檔案','位元組','SHA256'])
        for p in files:writer.writerow([p.relative_to(O).as_posix(),p.stat().st_size,hashlib.sha256(p.read_bytes()).hexdigest()])
    full=O.parent/'D1彩色課程完整套件.zip'
    write_zip(full,[(p,O.name+'/'+p.relative_to(O).as_posix()) for p in files+[manifest_path]])
    print(f'Published {VERSION}: integrated website, 3 PDFs, app, full SDK, source and verified ZIP.',flush=True)


if __name__=='__main__':main()
