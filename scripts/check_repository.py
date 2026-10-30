"""Check the exact Git index before publishing; prints paths only on failure."""
from pathlib import Path
import hashlib
import json
import re
import subprocess
import sys

ROOT=Path(__file__).resolve().parents[1]
SECRET_PATTERNS=[re.compile(rb'gh[pousr]_[A-Za-z0-9]{30,}'),
                 re.compile(rb'github_pat_[A-Za-z0-9_]{40,}'),
                 re.compile(rb'-----BEGIN (?:RSA |OPENSSH |EC )?PRIVATE KEY-----'),
                 re.compile(rb'AKIA[0-9A-Z]{16}')]
IGNORED_PREFIXES=('output/','tmp/','downloads/','field-results/','student-work/','local/')
REQUIRED=['README.md','AGENTS.md','.gitignore','.gitattributes','docs/公司電腦實機測試.md',
          'docs/跨電腦持續開發.md','scripts/setup-dev.ps1',
          'docs/實機測試記錄範本.md','scripts/fetch-release.ps1','scripts/preflight.ps1',
          'releases/v2.0.0.json','d1-classroom/curriculum/lessons.json','d1-classroom/bridge/install.sh']


def main():
    result=subprocess.run(['git','ls-files','-z','--cached'],cwd=ROOT,capture_output=True,check=True)
    names=[name.decode('utf-8') for name in result.stdout.split(b'\0') if name]
    errors=[]
    for name in REQUIRED:
        if name not in names:errors.append('Required tracked path missing: '+name)
    for name in names:
        if ('/node_modules/' in '/'+name or name.startswith(IGNORED_PREFIXES) and name!='output/README.md'
            or name.startswith('references/') and name!='references/README.md'
            or Path(name).name in ('robot.json','robots.json','.env') or name.endswith(('.previous','.pyc','.log'))):
            errors.append('Local/generated data tracked: '+name)
        data=subprocess.run(['git','show',':'+name],cwd=ROOT,capture_output=True,check=True).stdout
        if len(data)>45*1024**2:errors.append('Oversized Git blob; use Release: '+name)
        if b'\0' not in data[:8192]:
            if any(pattern.search(data) for pattern in SECRET_PATTERNS):errors.append('Possible credential in: '+name)
        if name.endswith('.sh') and b'\r\n' in data:errors.append('Shell script must be LF: '+name)
    manifest=ROOT/'d1-classroom/bridge/sdk/manifest.json'
    sdk=json.loads(manifest.read_text(encoding='utf-8'))
    assert hashlib.sha256((manifest.parent/sdk['archive']).read_bytes()).hexdigest()==sdk['sha256']
    if errors:
        print('\n'.join(errors));return 1
    print(f'PASS: {len(names)} tracked files; required docs, size limits, credential patterns, shell line endings and SDK hash.')
    return 0


if __name__=='__main__':sys.exit(main())
