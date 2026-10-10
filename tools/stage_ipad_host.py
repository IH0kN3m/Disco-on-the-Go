#!/usr/bin/env python3
"""Stage an empty original Unity host; gameplay comes from local inputs later."""
import json
from pathlib import Path
import shutil

ROOT = Path(__file__).resolve().parent.parent


def stage(root=ROOT):
    output = root / 'artifacts/recovered-unity'
    assets = output / 'Assets'
    if assets.exists():shutil.rmtree(assets)
    for directory in (assets / 'Editor', assets / 'Resources', output / 'Packages', output / 'ProjectSettings'):
        directory.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(root / 'runtime/UnityHost/Editor/ExportIPadHost.cs', assets / 'Editor/ExportIPadHost.cs')
    (output / 'Packages/manifest.json').write_text(json.dumps({'dependencies': {
        'com.unity.modules.' + name: '1.0.0' for name in ('imgui', 'jsonserialize', 'imageconversion', 'screencapture')
    }}) + '\n')
    (output / 'ProjectSettings/ProjectVersion.txt').write_text('m_EditorVersion: 2020.3.12f1\nm_EditorVersionWithRevision: 2020.3.12f1 (b3b2c6512326)\n')
    (output / 'staging.json').write_text(json.dumps({'scope': 'Empty original host for local engine export', 'empty_host': True}) + '\n')
    print('Empty host staged; scene recovery and decompilation are not build prerequisites.')


if __name__ == '__main__':
    stage()
