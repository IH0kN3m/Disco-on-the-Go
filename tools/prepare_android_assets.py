#!/usr/bin/env python3
"""Prepare private Android assets and hash the final converted payloads."""
import argparse
import hashlib
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parent.parent
BASE=ROOT/'artifacts/android/game-data'


def inventory():
    records=[]
    for folder in ('apk','external'):
        root=BASE/folder
        if not root.is_dir():raise ValueError('Stage Android data first')
        for path in sorted(root.rglob('*')):
            if path.is_symlink():raise ValueError('Asset symlinks are unsupported')
            if not path.is_file():continue
            if path.name.endswith('-tmp'):raise ValueError('Unfinished asset conversion')
            with path.open('rb') as stream:digest=hashlib.file_digest(stream,'sha256').hexdigest()
            records.append({'path':str(path.relative_to(BASE)),'bytes':path.stat().st_size,'sha256':digest})
    report={'scope':'Final private asset bytes; hashes do not establish rendered fidelity','files':records}
    (BASE/'derived-manifest.json').write_text(json.dumps(report,indent=2)+'\n')
    print('Inventoried',len(records),'derived files.')


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--inventory-only',action='store_true');args=parser.parse_args()
    if not args.inventory_only:
        from stage_android_assets import stage
        from convert_android_shaders import main as shaders
        stage()
        for bundles in (False,True):
            shaders(bundles)
            report=json.loads((BASE/('bundle-shaders.json' if bundles else 'shaders-latest.json')).read_text())
            if report['unsupported']:raise ValueError('Unsupported shader conversion; inspect private report')
    inventory()


if __name__=='__main__':main()
