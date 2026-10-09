#!/usr/bin/env python3
"""Inventory a supplied Windows game without executing or copying its binaries."""
import argparse
import hashlib
import json
from pathlib import Path
from disco_port.windows_input import pe_info

ROOT=Path(__file__).resolve().parent.parent

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('directory',type=Path);a=p.parse_args()
    root=a.directory.resolve(strict=True)
    records=[]
    for path in sorted(root.rglob('*')):
        if path.suffix.lower() not in ('.dll','.exe') or not path.is_file():continue
        if path.is_symlink() or not path.resolve().is_relative_to(root):raise SystemExit('Windows input escapes selected directory')
        if path.stat().st_size>512*1024**2:raise SystemExit('Windows input exceeds bounded binary size')
        raw=path.read_bytes()
        record={'path':path.relative_to(root).as_posix(),'bytes':len(raw),'sha256':hashlib.sha256(raw).hexdigest()}
        try:record.update(pe_info(raw))
        except ValueError as error:record['inspection_error']=str(error)
        records.append(record)
    if not records:raise SystemExit('No Windows executable/library inputs found')
    output=ROOT/'artifacts/android/windows-input.json';output.parent.mkdir(parents=True,exist_ok=True)
    output.write_text(json.dumps({'scope':'Static PE/CLI inventory; no supplied executable was loaded','binaries':records},indent=2)+'\n')
    print('Inspected',len(records),'binaries; managed assemblies:',sum(r.get('cli',False) for r in records))
    for r in records:
        if r['path'].endswith(('Assembly-CSharp.dll','GameAssembly.dll','UnityPlayer.dll')):
            print(json.dumps(r))
