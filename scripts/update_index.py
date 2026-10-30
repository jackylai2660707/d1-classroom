"""Refresh the workspace file inventory using Python's standard library."""
from pathlib import Path
import csv

ROOT = Path(__file__).resolve().parents[1]
DEST = ROOT / 'docs' / '檔案索引.csv'
EXCLUDED = {'node_modules', '__pycache__', '.git', '.venv', 'venv',
            'local', 'tmp', 'downloads', 'field-results', '.previous-releases'}


def category(parts):
    if parts[0] == 'output':
        return '正式交付成品'
    if parts[0] == 'references':
        return '研究摘錄與SDK參考' if parts[1] == 'research' else '原廠與圖片參考'
    if parts[0] == 'docs':
        return '工作文件與紀錄'
    if parts[0] == 'scripts':
        return '工作區工具'
    if parts[0] == 'd1-classroom' and len(parts) > 2:
        return {
            'app': '應用程式與執行資產', 'bridge': 'Linux橋接與部署',
            'assets': '教材圖片素材', 'curriculum': '課程與模型素材',
            'tests': '軟體測試', 'config': '開發設定', 'courseware': '離線教程版式與互動',
            'build': '建置腳本、驗證證據與歷史PDF',
        }.get(parts[1], '專案設定與說明')
    return '專案設定與說明'


def walk(directory):
    for entry in sorted(directory.iterdir(), key=lambda p: p.name):
        if entry.name in EXCLUDED or entry.is_symlink():
            continue
        if entry.is_dir():
            yield from walk(entry)
        elif entry.is_file() and entry != DEST:
            yield entry


if __name__ == '__main__':
    rows = [(p.relative_to(ROOT).as_posix(), category(p.relative_to(ROOT).parts),
             p.stat().st_size) for p in walk(ROOT)]
    with DEST.open('w', encoding='utf-8-sig', newline='') as output:
        writer = csv.writer(output)
        writer.writerow(['相對路徑', '用途分類', '位元組'])
        writer.writerows(rows)
    print(f'Indexed {len(rows)} files; dependencies, caches and the index itself excluded.')
