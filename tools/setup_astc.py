#!/usr/bin/env python3
"""Download the checksum-pinned official macOS ASTC encoder for local asset work."""

import hashlib
from pathlib import Path, PurePosixPath
import subprocess
import urllib.request
import zipfile

ROOT = Path(__file__).resolve().parent.parent
VERSION = '5.7.0'
URL = f'https://github.com/ARM-software/astc-encoder/releases/download/{VERSION}/astcenc-{VERSION}-macos-universal.zip'
SHA256 = '374b2f0aea1d3ab5f849784666d6ece6e27b4bc1f945e5c90d6eeabf00e955f8'


def main():
    output = ROOT / 'artifacts/toolchains/astc'
    output.mkdir(parents=True, exist_ok=True)
    package = output / f'astcenc-{VERSION}.zip'
    if not package.exists():
        with urllib.request.urlopen(URL, timeout=60) as source, package.open('wb') as target:
            total = 0
            while block := source.read(1024 * 1024):
                total += len(block)
                if total > 16 * 1024 * 1024:
                    raise ValueError('Encoder download exceeds supported size')
                target.write(block)
    if hashlib.sha256(package.read_bytes()).hexdigest() != SHA256:
        raise ValueError('Encoder release checksum mismatch')
    with zipfile.ZipFile(package) as archive:
        entries = [item for item in archive.infolist() if PurePosixPath(item.filename).name == 'astcenc']
        if len(entries) != 1:
            raise ValueError('Unsupported encoder package layout')
        entry = entries[0]
        path = PurePosixPath(entry.filename)
        if path.is_absolute() or '..' in path.parts or '\\' in entry.filename or not 0 < entry.file_size <= 64 * 1024 * 1024:
            raise ValueError('Unsafe encoder package entry')
        binary = output / 'astcenc'
        binary.write_bytes(archive.read(entry))
        binary.chmod(0o755)
    result = subprocess.run([str(binary), '-version'], capture_output=True, check=True, text=True)
    if VERSION not in result.stdout:
        raise ValueError('Downloaded encoder reports an unexpected version')
    print('Official ASTC encoder ready under artifacts/toolchains/astc; release checksum verified.')


if __name__ == '__main__':
    try:
        main()
    except (OSError, ValueError, zipfile.BadZipFile, subprocess.CalledProcessError) as error:
        raise SystemExit(f'ASTC setup failed: {error}')
