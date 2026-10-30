"""Audit the final manifest, every ZIP member and the nested original SDK; standard library."""
from pathlib import Path
import csv
import hashlib
import io
import json
import zipfile

R=Path(__file__).resolve().parents[1]
O=R.parent/'output/D1彩色課程套件'


def sha(data):
    return hashlib.sha256(data).hexdigest()


def audit():
    rows=list(csv.DictReader((O/'檔案清單.csv').open(encoding='utf-8-sig')))
    names=[r['檔案'] for r in rows]
    assert len(names)==len(set(names))
    actual={p.relative_to(O).as_posix() for p in O.rglob('*') if p.is_file() and p.name!='檔案清單.csv'}
    assert actual==set(names)
    for row in rows:
        file=O/row['檔案'];assert file.resolve().is_relative_to(O.resolve())
        assert file.stat().st_size==int(row['位元組'])
        assert sha(file.read_bytes())==row['SHA256'],row['檔案']
        assert file.suffix not in ('.pptx','.docx','.previous','.pyc','.new')
    full=O.parent/'D1彩色課程完整套件.zip'
    with zipfile.ZipFile(full) as archive:
        assert archive.testzip() is None
        prefix=O.name+'/'
        assert set(archive.namelist())=={prefix+n for n in names+['檔案清單.csv']}
        for row in rows:
            with archive.open(prefix+row['檔案']) as member:
                assert hashlib.file_digest(member,'sha256').hexdigest()==row['SHA256']
        assert archive.read(prefix+'檔案清單.csv')==(O/'檔案清單.csv').read_bytes()
    setup=O/'技術人員部署/d1-setup.zip'
    assert setup.read_bytes()==(O.parent/'D1機器狗初始化包.zip').read_bytes()
    sdk_manifest=json.loads((R/'bridge/sdk/manifest.json').read_text(encoding='utf-8'))
    with zipfile.ZipFile(setup) as archive:
        assert archive.testzip() is None
        vendor=archive.read('d1-setup/sdk/'+sdk_manifest['archive'])
        assert sha(vendor)==sdk_manifest['sha256']
        assert vendor==(R/'bridge/sdk'/sdk_manifest['archive']).read_bytes()
        assert archive.read('d1-setup/sdk/LICENSE.vendor.txt')==(R/'bridge/sdk/LICENSE.vendor.txt').read_bytes()
    source=O/'D1學生工坊與教材原始碼.zip'
    with zipfile.ZipFile(source) as archive:
        assert archive.testzip() is None
        required=['courseware/style.css','courseware/course.js','courseware/驗收紀錄.md','requirements-author.txt',
                  'build/courseware.py','build/printables.py','build/deliver.py','curriculum/lessons.json','app/main.cjs']
        for name in required:assert 'd1-classroom/'+name in archive.namelist()
        for file in archive.namelist():
            assert 'node_modules/' not in file and not file.endswith(('.docx','.pptx','.previous','.pyc'))
        assert archive.read('d1-classroom/curriculum/lessons.json')==(R/'curriculum/lessons.json').read_bytes()
    for l in json.loads((R/'curriculum/lessons.json').read_text(encoding='utf-8')):
        base=f'第{l["id"]:02}課'
        project=json.loads((O/'配套檔案/課程專案'/(base+'.d1.json')).read_text(encoding='utf-8'))
        assert project['blocks']==l['blocks'] and project['python']==l['code']
        assert (O/'配套檔案/課程專案'/(base+'.py')).read_text(encoding='utf-8')==l['code']
    result={'version':'2.0.0','files':len(rows),'manifest':'all hashes matched','fullZip':'all members matched manifest',
            'setupZip':'CRC and byte-identical original SDK','sourceZip':'CRC and required rebuild assets',
            'curriculum':'16 JSON and 16 Python match canonical source','legacyOfficeFiles':0,'fullZipBytes':full.stat().st_size,
            'sdkSha256':sdk_manifest['sha256']}
    target=R/'build/qa/courseware/delivery-report.json';target.parent.mkdir(parents=True,exist_ok=True)
    target.write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps(result,ensure_ascii=False))


if __name__=='__main__':audit()
