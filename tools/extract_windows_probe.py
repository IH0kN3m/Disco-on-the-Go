#!/usr/bin/env python3
"""Extract inspection inputs from a supplied GOG installer; never execute it."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parent.parent
INCLUDES = ('GameAssembly.dll', 'UnityPlayer.dll', 'Disco Elysium.exe',
            'Disco Elysium_Data/globalgamemanagers', 'Disco Elysium_Data/globalgamemanagers.assets',
            'Disco Elysium_Data/resources.assets', 'Disco Elysium_Data/sharedassets0.assets',
            'Disco Elysium_Data/Resources/unity_builtin_extra', 'Disco Elysium_Data/Plugins',
            'Disco Elysium_Data/il2cpp_data/Metadata/global-metadata.dat', 'Disco Elysium_Data/boot.config')


def fingerprint(path):
    with path.open('rb') as stream:
        digest = hashlib.file_digest(stream, 'sha256').hexdigest()
    return {'name': path.name, 'bytes': path.stat().st_size, 'sha256': digest}


def main(directory):
    directory = directory.resolve(strict=True)
    installers = sorted(directory.glob('setup_*.exe'))
    if len(installers) != 1:
        raise ValueError('Expected exactly one GOG setup_*.exe installer')
    installer = installers[0]
    parts = sorted(directory.glob(installer.stem + '-*.bin'))
    if not parts:
        raise ValueError('Installer data parts are missing')
    inputs = [installer, *parts]
    if any(p.is_symlink() or not p.is_file() for p in inputs):
        raise ValueError('Installer inputs must be regular files')
    before = [fingerprint(p) for p in inputs]
    base = ROOT / 'artifacts/android'
    output = base / 'windows-extracted'
    base.mkdir(parents=True, exist_ok=True)
    marker = base / 'windows-extraction.json'
    if output.exists():
        if not marker.exists() or json.loads(marker.read_text())['inputs'] != before:
            raise ValueError('Existing extraction has no matching input manifest; move it aside before retrying')
    version = subprocess.check_output(['innoextract', '--version'], text=True).splitlines()[0]
    with (base / 'windows-installer-list.txt').open('w') as log:
        subprocess.run(['innoextract', '--list', '--color=0', str(installer)],
                       check=True, stdout=log, stderr=subprocess.STDOUT)
    command = ['innoextract', '--extract', '--exclude-temp', '--color=0', '--progress=0',
               '--output-dir', str(output)]
    for name in INCLUDES:
        command += ['--include', name]
    with (base / 'windows-extraction.log').open('w') as log:
        subprocess.run([*command, str(installer)], check=True, stdout=log, stderr=subprocess.STDOUT)
    if before != [fingerprint(p) for p in inputs]:
        raise ValueError('Supplied installer changed during extraction')
    for name in INCLUDES:
        if not (output / name).exists():
            raise ValueError('Missing required extracted input: ' + name)
    marker.write_text(json.dumps({'scope': 'Selected static inspection files only, not a full game installation',
                                 'tool': version, 'inputs': before, 'included_paths': INCLUDES}, indent=2) + '\n')
    print('Inspection inputs extracted under artifacts/android/windows-extracted; source hashes unchanged.')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('directory', type=Path, nargs='?', default=ROOT / 'reference/disco-win')
    args = parser.parse_args()
    try:
        main(args.directory)
    except (ValueError, OSError, subprocess.SubprocessError) as error:
        parser.exit(1, f'Windows extraction failed: {error}\n')
