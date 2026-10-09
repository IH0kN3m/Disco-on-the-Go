#!/usr/bin/env python3
"""Audit source files and every reachable Git tree; print paths, never secret values."""
import argparse
import json
from pathlib import Path
import subprocess
from disco_port.release_audit import check_source

ROOT = Path(__file__).resolve().parent.parent


def git(*args):
    return subprocess.run(['git', *args], cwd=ROOT, check=True, capture_output=True).stdout


def audit(history=False):
    private = []
    for name in ('local-ipad.json', 'local-android.json'):
        config = ROOT / 'artifacts' / name
        if config.exists():
            value = json.loads(config.read_text())
            private.extend(value[k] for k in ('team_id', 'device_identifier') if isinstance(value.get(k), str))
    findings, checked = [], 0
    for name in git('ls-files', '-z', '--cached', '--others', '--exclude-standard').decode().split('\0'):
        if not name:
            continue
        path = ROOT / name
        if not path.exists() and not path.is_symlink():
            findings.append({'path': name, 'where': 'working tree', 'issues': ['tracked file missing']})
            continue
        mode, data = '100644', b''
        if path.is_symlink():
            mode = '120000'
        elif not path.is_file():
            mode = '160000'
        else:
            with path.open('rb') as stream:
                data = stream.read(256 * 1024 + 1)
        issues = check_source(name, data, mode, private)
        checked += 1
        if issues:
            findings.append({'path': name, 'where': 'working tree', 'issues': issues})
    commits, pairs, blobs = [], set(), {}
    if history:
        commits = git('rev-list', '--all').decode().splitlines()
        for commit in commits:
            for record in git('ls-tree', '-rz', commit).split(b'\0'):
                if not record:
                    continue
                meta, raw_name = record.split(b'\t', 1)
                mode, kind, oid = meta.decode().split()
                name = raw_name.decode()
                key = (mode, oid, name)
                if key in pairs:
                    continue
                pairs.add(key)
                if kind != 'blob':
                    data = b''
                elif oid in blobs:
                    data = blobs[oid]
                else:
                    size = int(git('cat-file', '-s', oid))
                    data = git('cat-file', 'blob', oid) if size <= 256 * 1024 else b'x' * (256 * 1024 + 1)
                    blobs[oid] = data
                issues = check_source(name, data, mode, private)
                if issues:
                    findings.append({'path': name, 'where': commit[:12], 'issues': issues})
    report = {'working_files': checked, 'reachable_commits': len(commits), 'historical_path_versions': len(pairs),
              'findings': findings, 'scope': 'Source allowlist and leak checks; authorship and licensing require review.'}
    output = ROOT / 'artifacts/release/audit.json'
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps(report, indent=2))
    return not findings


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--history', action='store_true', help='Include every tree reachable from local Git refs')
    args = parser.parse_args()
    raise SystemExit(0 if audit(args.history) else 1)
