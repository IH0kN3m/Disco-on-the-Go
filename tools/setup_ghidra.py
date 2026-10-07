#!/usr/bin/env python3
"""Install a checksum-pinned static decompiler under ignored artifacts."""
import hashlib
from pathlib import Path, PurePosixPath
import stat
import shutil
import subprocess
import urllib.request
import zipfile

ROOT = Path(__file__).resolve().parent.parent
VERSION = '12.1.3'
NAME = 'ghidra_12.1.3_PUBLIC_20260817'
DIRECTORY = 'ghidra_12.1.3_PUBLIC'
URL = f'https://github.com/NationalSecurityAgency/ghidra/releases/download/Ghidra_{VERSION}_build/{NAME}.zip'
SHA = '93a5d11a9ad510622acaaf908c556a7b9b764d338e78a7567f3689bf5081fd54'
SIZE = 569445154


def main():
    output = ROOT / 'artifacts/toolchains/ghidra'
    output.mkdir(parents=True, exist_ok=True)
    package = output / (NAME + '.zip')
    if not package.exists():
        temporary = package.with_suffix('.partial')
        with urllib.request.urlopen(URL, timeout=60) as source, temporary.open('wb') as target:
            total = 0
            while block := source.read(1024 * 1024):
                total += len(block)
                if total > SIZE:
                    raise ValueError('Unexpected decompiler download size')
                target.write(block)
        if total != SIZE:
            raise ValueError('Truncated decompiler download')
        temporary.replace(package)
    digest = hashlib.sha256()
    with package.open('rb') as source:
        for block in iter(lambda: source.read(1024 * 1024), b''):
            digest.update(block)
    if digest.hexdigest() != SHA:
        raise ValueError('Official decompiler checksum mismatch')
    with zipfile.ZipFile(package) as archive:
        entries = archive.infolist()
        if len(entries) > 50000 or sum(e.file_size for e in entries) > 3 * 1024**3:
            raise ValueError('Unsupported decompiler archive size')
        seen = set()
        for entry in entries:
            path = PurePosixPath(entry.filename)
            mode = entry.external_attr >> 16
            if (path.is_absolute() or '..' in path.parts or '\\' in entry.filename or not path.parts
                    or path.parts[0] != DIRECTORY or str(path) in seen or stat.S_ISLNK(mode)
                    or entry.file_size > 256 * 1024**2):
                raise ValueError('Unowned or unsupported decompiler archive entry')
            seen.add(str(path))
        archive.extractall(output)
        for entry in entries:
            if not entry.is_dir() and entry.external_attr >> 16 & 0o111:
                (output / entry.filename).chmod(0o755)
    if not (output / DIRECTORY / 'support/analyzeHeadless').is_file():
        raise ValueError('Decompiler headless entry point absent')
    # Official release ships sources rather than macOS native components.
    native = output / DIRECTORY / 'Ghidra/Features/Decompiler/build/os/mac_arm_64/decompile'
    if not native.is_file():
        source = output / DIRECTORY / 'Ghidra/Features/Decompiler/src/decompile/cpp'
        subprocess.run(['make', '-j4', 'ghidra_opt', 'ARCH_TYPE=-arch arm64',
                        'ADDITIONAL_FLAGS=-mmacosx-version-min=12.0', 'OSDIR=mac_arm_64'], cwd=source, check=True)
        native.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source / 'ghidra_opt', native)
        native.chmod(0o755)
    print('Pinned Ghidra ready; JDK required. Game inspection is static only.')


if __name__ == '__main__':
    try:
        main()
    except (OSError, ValueError, zipfile.BadZipFile, subprocess.CalledProcessError) as error:
        raise SystemExit(f'Decompiler setup failed: {error}')
