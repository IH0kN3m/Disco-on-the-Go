#!/usr/bin/env python3
"""Export a separate, empty Android Unity host; never alter the iPad project."""
import json
import os
from pathlib import Path
import shutil
import subprocess
from disco_port.android_build import export_paths

ROOT = Path(__file__).resolve().parent.parent


def export():
    base = ROOT / 'artifacts/android'
    project = base / 'unity-host'
    for folder in ('Assets/Editor', 'Packages', 'ProjectSettings'):
        (project / folder).mkdir(parents=True, exist_ok=True)
    shutil.copyfile(ROOT/'runtime/AndroidHost/Editor/ExportAndroidHost.cs', project/'Assets/Editor/ExportAndroidHost.cs')
    (project/'ProjectSettings/ProjectVersion.txt').write_text('m_EditorVersion: 2020.3.12f1\nm_EditorVersionWithRevision: 2020.3.12f1 (b3b2c6512326)\n')
    (project/'Packages/manifest.json').write_text(json.dumps({'dependencies': {'com.unity.modules.'+m: '1.0.0' for m in ('imgui', 'jsonserialize', 'imageconversion', 'screencapture')}})+'\n')
    editor = Path((ROOT/'artifacts/toolchains/unity-editor-path.txt').read_text().strip())
    env = os.environ.copy()
    for name, path in export_paths(ROOT).items(): env['DISCO_ANDROID_' + name.upper()] = str(path)
    env['DISCO_ANDROID_EXPORT'] = str(base/'unity-export')
    with (base/'unity-export-process.log').open('w') as log:
        result = subprocess.run([str(editor), '-batchmode', '-nographics', '-quit', '-projectPath', str(project),
                                 '-buildTarget', 'Android', '-executeMethod', 'ExportAndroidHost.Export',
                                 '-logFile', str(base/'unity-export.log')], env=env, stdout=log, stderr=subprocess.STDOUT)
    if result.returncode or 'DISCO_ANDROID_EXPORT_SUCCEEDED' not in (base/'unity-export.log').read_text():
        raise ValueError('Unity export failed; inspect artifacts/android/unity-export.log')
    print('Unity Android host exported; runtime replacement and APK packaging remain separate steps.')


if __name__ == '__main__':
    export()
