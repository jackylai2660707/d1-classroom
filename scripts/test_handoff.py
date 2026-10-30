"""Windows integration check of release restore, overwrite protection and corrupt-file refusal."""
from pathlib import Path
import json
import shutil
import subprocess
import tempfile
import sys

ROOT=Path(__file__).resolve().parents[1]


def invoke(script,*args,expect=0):
    result=subprocess.run(['powershell','-NoProfile','-File',str(script),*map(str,args)],capture_output=True,text=True,errors='replace')
    if (expect==0 and result.returncode!=0) or (expect!=0 and result.returncode==0):
        raise AssertionError(result.stdout+'\n'+result.stderr)
    return result


def main():
    if sys.platform!='win32':raise SystemExit('This integration check needs Windows PowerShell.')
    assets=ROOT/'output/github-release'
    temporary=Path(tempfile.mkdtemp(prefix='d1-handoff-'))
    assert temporary.resolve().parent==Path(tempfile.gettempdir()).resolve()
    try:
        (temporary/'scripts').mkdir();(temporary/'releases').mkdir();(temporary/'references').mkdir()
        for name in ['fetch-release.ps1','preflight.ps1','preflight.py']:
            shutil.copy2(ROOT/'scripts'/name,temporary/'scripts'/name)
        shutil.copy2(ROOT/'releases/v2.0.0.json',temporary/'releases/v2.0.0.json')
        shutil.copy2(ROOT/'references/README.md',temporary/'references/README.md')
        script=temporary/'scripts/fetch-release.ps1'
        invoke(script,'-AssetDirectory',assets,'-IncludeReferences')
        suite=temporary/'output/D1彩色課程套件'
        assert (suite/'學生工具/D1學生工坊/D1學生工坊.exe').is_file()
        assert (suite/'教程/lesson-16.html').is_file()
        assert (temporary/'references/ARCHIVE-MANIFEST.json').is_file()
        assert (temporary/'references/歷史建置/1.0-20261021/slides.mjs').is_file()
        for row in json.loads((temporary/'references/ARCHIVE-MANIFEST.json').read_text(encoding='utf-8')):
            target=temporary/row['path']
            assert target.is_file() and target.stat().st_size==row['bytes']
        sentinel=suite/'keep-local.txt';sentinel.write_text('must survive unless explicitly replaced',encoding='utf-8')
        invoke(script,'-AssetDirectory',assets)
        assert sentinel.is_file()
        invoke(script,'-AssetDirectory',assets,'-Replace')
        backups=list((temporary/'output/.previous-releases').glob('*/keep-local.txt'))
        assert len(backups)==1 and backups[0].read_text(encoding='utf-8')=='must survive unless explicitly replaced'
        assert not sentinel.exists() and (suite/'使用說明.html').is_file()
        shutil.copytree(ROOT/'d1-classroom/bridge/sdk',temporary/'d1-classroom/bridge/sdk')
        invoke(temporary/'scripts/preflight.ps1')
        bad=temporary/'bad-assets';bad.mkdir()
        (bad/'D1-Classroom-2.0.0-Windows-x64.zip').write_bytes(b'corrupt')
        result=invoke(script,'-AssetDirectory',bad,'-VerifyOnly',expect=1)
        assert 'mismatch' in result.stderr or 'mismatch' in result.stdout
        report={'date':'2026-10-30','cleanRestore':True,'references':True,'existingFilesKept':True,
                'replaceArchivesOldFiles':True,'preflightOnRestoredFiles':True,'corruptFileRejected':True,'physicalRobot':False}
        qa=ROOT/'d1-classroom/build/qa/company-handoff';qa.mkdir(parents=True,exist_ok=True)
        (qa/'restore-report.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
        print(json.dumps(report))
    finally:
        resolved=temporary.resolve()
        if resolved.parent!=Path(tempfile.gettempdir()).resolve() or not resolved.name.startswith('d1-handoff-'):
            raise RuntimeError('Unsafe test cleanup path')
        shutil.rmtree(resolved)


if __name__=='__main__':main()
