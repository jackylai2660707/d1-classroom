"""Read-only workstation checks; never connects to a robot or changes a firewall."""
from pathlib import Path
import argparse
import datetime
import hashlib
import json
import platform
import shutil
import subprocess
import sys
import zipfile

ROOT=Path(__file__).resolve().parents[1]


def run(strict_delivery=False):
    checks=[]
    def check(name,passed,detail):
        checks.append({'name':name,'passed':bool(passed),'detail':detail})
    check('Python',sys.version_info>=(3,10),platform.python_version())
    check('Windows workstation',platform.system()=='Windows' and platform.machine().lower() in ('amd64','x86_64','arm64','aarch64'),'{} {}; delivery target remains Windows x64'.format(platform.system(),platform.machine()))
    sdk=ROOT/'d1-classroom/bridge/sdk'
    try:
        manifest=json.loads((sdk/'manifest.json').read_text(encoding='utf-8'))
        archive=sdk/manifest['archive']
        assert archive.parent.resolve()==sdk.resolve()
        assert hashlib.sha256(archive.read_bytes()).hexdigest()==manifest['sha256']
        with zipfile.ZipFile(archive) as z:
            assert z.testzip() is None
            assert z.read('agibot_D1_Edu-Ultra/LICENSE')==(sdk/'LICENSE.vendor.txt').read_bytes()
        check('Bundled original SDK',True,manifest['sha256'])
    except Exception as error:check('Bundled original SDK',False,str(error))
    suite=ROOT/'output/D1彩色課程套件'
    files=['使用說明.html','教程/lesson-03.html','學生工具/D1學生工坊/D1學生工坊.exe',
           '學生工具/D1學生工坊/resources/app.asar','學生工具/D1學生工坊/resources/ffmpeg.exe',
           '技術人員部署/d1-setup.zip','配套檔案/備用色卡模型.zip','列印資料/操作與試教記錄.pdf']
    missing=[name for name in files if not (suite/name).is_file()]
    check('Windows delivery',not missing,missing or 'All required files present')
    if not missing:
        with zipfile.ZipFile(suite/'技術人員部署/d1-setup.zip') as archive:
            check('Robot setup package',archive.testzip() is None,'ZIP CRC')
    tools={name:shutil.which(name) for name in ['git','gh','node','pnpm','ssh','scp']}
    try:
        network=subprocess.run(['ipconfig'],capture_output=True,text=True,errors='replace',timeout=10).stdout
    except (OSError,subprocess.TimeoutExpired):network='Unavailable; inspect workstation network settings.'
    report={'createdAt':datetime.datetime.now(datetime.timezone.utc).isoformat(),'checks':checks,'tools':tools,
            'network':network,'physicalRobotTested':False,
            'next':'Follow docs/公司電腦實機測試.md. Verify MAC, network, stop procedure and robot compatibility on site.'}
    destination=ROOT/'field-results';destination.mkdir(exist_ok=True)
    output=destination/('preflight-'+datetime.datetime.now().strftime('%Y%m%d-%H%M%S')+'.json')
    output.write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    for c in checks:print(('PASS' if c['passed'] else 'CHECK')+': '+c['name'])
    print('Local report: '+str(output))
    failures=[c for c in checks if not c['passed'] and (strict_delivery or c['name']!='Windows delivery')]
    return 1 if failures else 0


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--strict-delivery',action='store_true')
    sys.exit(run(parser.parse_args().strict_delivery))
