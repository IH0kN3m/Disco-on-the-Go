#!/usr/bin/env python3
"""Build from the pinned Mac game. No device access or downloads during builds."""
import argparse
import datetime
import fcntl
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys

from disco_port.build_inputs import validate_sources, sha256

ROOT = Path(__file__).resolve().parent.parent


def steps(root=ROOT, platform='ipad'):
    python = sys.executable
    scene_python = str(root / '.venv/bin/python')
    def tool(name, *arguments): return [python, 'tools/' + name + '.py', *arguments]
    if platform == 'android':
        return [
            ('export-unity-android', tool('export_android_host')),
            ('android-assets', [scene_python, 'tools/prepare_android_assets.py']),
            ('android-asset-audit', [scene_python, 'tools/audit_android_assets.py']),
            ('app-branding', [scene_python, 'tools/prepare_branding.py']),
            ('android-build', tool('build_android_game', '--game-data', '--obb')),
        ]
    if platform != 'ipad': raise ValueError('Unsupported platform')
    return [
        ('inspect', tool('inspect_game')),
        ('stage-host', tool('stage_ipad_host')),
        ('export-unity', tool('export_ipad_host')),
        ('runtime', tool('prepare_ipad_runtime')),
        ('steam', tool('prepare_native_plugins')),
        ('amplify', tool('prepare_amplify_plugin')),
        ('engine', tool('prepare_ipad_game', '--game-data', '--retag-serialized')),
        ('startup-bundles', [scene_python, 'tools/retag_startup_bundles.py']),
        ('addressable-bundles', [scene_python, 'tools/retag_startup_bundles.py', '--addressables']),
        ('configure', tool('configure_ipad', '--increased-memory', '--no-debug-memory', '--amplify-cpu', '--lazy-scenes', '--landscape')),
        ('app-branding', [scene_python, 'tools/prepare_branding.py', '--ipad-project', 'artifacts/build/native-engine-ios']),
        ('native-bc', tool('enable_engine_bc')),
        ('build', tool('build_ipad_game')),
    ]


def doctor(platform='ipad'):
    if sys.platform != 'darwin' or sys.version_info < (3, 11):
        raise ValueError('Use macOS and Python 3.11 or newer')
    sources = validate_sources(ROOT / 'reference/Disco.app')
    editor = Path((ROOT / 'artifacts/toolchains/unity-editor-path.txt').read_text().strip())
    if not editor.is_file():
        raise ValueError('Missing pinned editor; run make setup-unity before building')
    toolchains = {}
    if platform == 'ipad':
        xcode = subprocess.check_output(['xcodebuild', '-version'], text=True).strip()
        if not xcode.startswith('Xcode 27.'):
            raise ValueError('The supported build toolchain is Xcode 27.x; select it with xcode-select')
        toolchains['xcode'] = xcode
    elif platform == 'android':
        from disco_port.android_build import validate_toolchains
        toolchains = validate_toolchains(ROOT, editor)
    else: raise ValueError('Unsupported platform')
    check = 'import importlib.metadata,json; print(json.dumps({n:importlib.metadata.version(n) for n in ' + repr([
        line.split('==')[0] for line in (ROOT / 'requirements.lock').read_text().splitlines() if line and not line.startswith('#')
    ]) + '}))'
    versions = json.loads(subprocess.check_output([str(ROOT / '.venv/bin/python'), '-c', check], text=True))
    for line in (ROOT / 'requirements.lock').read_text().splitlines():
        if line and not line.startswith('#'):
            name, version = line.split('==')
            if versions.get(name) != version:
                raise ValueError('Dependency versions differ; run make setup')
    free = shutil.disk_usage(ROOT).free
    if free < 60 * 1024**3:
        raise ValueError('Keep at least 60 GiB free for local generated projects/builds')
    return {'platform': platform, 'source_hashes': sources, **toolchains, 'python': sys.version.split()[0],
            'dependencies': versions, 'free_gib': round(free / 1024**3, 1),
            'note': 'Unity licensing/Rosetta are validated when the editor runs; no device checked.'}


def source_snapshot(bundle):
    result = {}
    root = bundle.resolve(strict=True)
    for path in sorted(root.rglob('*')):
        if not path.resolve().is_relative_to(root):
            raise ValueError('Reference bundle has an external symlink')
        if path.is_symlink():
            result[path.relative_to(root).as_posix()] = {'link': os.readlink(path)}
        elif path.is_file():
            result[path.relative_to(root).as_posix()] = {'size': path.stat().st_size, 'sha256': sha256(path)}
    return result


def build_unlocked(platform='ipad'):
    evidence = doctor(platform)
    output = ROOT / 'artifacts/reproducibility' / datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
    output.mkdir(parents=True)
    evidence.update(status='running', steps=[])
    report = output / 'build.json'
    bundle = ROOT / 'reference/Disco.app'
    print('Fingerprinting immutable source bundle…', flush=True)
    before = source_snapshot(bundle)
    (output / 'source-manifest.json').write_text(json.dumps(before, indent=2) + '\n')
    report.write_text(json.dumps(evidence, indent=2) + '\n')
    try:
        for name, command in steps(platform=platform):
            log_path = output / (name + '.log')
            print(f'{name}: {log_path.relative_to(ROOT)}', flush=True)
            with log_path.open('w') as log:
                result = subprocess.run(command, cwd=ROOT, stdout=log, stderr=subprocess.STDOUT)
            evidence['steps'].append({'name': name, 'exit_code': result.returncode})
            report.write_text(json.dumps(evidence, indent=2) + '\n')
            if result.returncode:
                raise ValueError(f'{name} failed; inspect {log_path.relative_to(ROOT)}. Fix the cause and rerun the build.')
        evidence['status'] = 'local development APK completed' if platform == 'android' else 'unsigned build completed'
        if platform == 'android':
            evidence['products'] = json.loads((ROOT / 'artifacts/android/build-game/build.json').read_text())
    finally:
        evidence['reference_unchanged'] = source_snapshot(bundle) == before
        if evidence['status'] == 'running': evidence['status'] = 'failed'
        report.write_text(json.dumps(evidence, indent=2) + '\n')
        if not evidence['reference_unchanged']:
            raise ValueError('Reference changed during build; investigate before continuing')
    print('Disco on the Go: artifacts/android/build-game/disco-on-the-go.apk + OBB; streaming data under artifacts/android/game-data/external. Install with make install PLATFORM=android.'
          if platform == 'android' else 'Disco on the Go unsigned app ready. Sign and install with make install.')


def build(platform='ipad'):
    lock_path = ROOT / 'artifacts/port-build.lock'
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    with lock_path.open('a') as lock:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            raise ValueError('Another port build owns this workspace; wait for it to finish') from None
        build_unlocked(platform)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command', choices=['doctor', 'plan', 'build'])
    parser.add_argument('--platform', choices=['ipad', 'android'], default='ipad')
    args = parser.parse_args()
    try:
        if args.command == 'doctor': print(json.dumps(doctor(args.platform), indent=2))
        elif args.command == 'plan':
            for name, command in steps(platform=args.platform): print(name + ': ' + ' '.join(command))
        else: build(args.platform)
    except (ValueError, OSError, subprocess.CalledProcessError, KeyError) as error:
        parser.exit(1, f'Port build failed: {error}\n')
