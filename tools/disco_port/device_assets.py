"""Own and fingerprint the derived data tree used by persistent device assets."""

import hashlib
import json
from pathlib import PurePosixPath
import re

from .binary import FormatError


def validate_manifest(value):
    if not isinstance(value, dict) or type(value.get('format')) is not int or value.get('format') != 1:
        raise FormatError('Unsupported device asset manifest')
    files = value.get('files')
    if not isinstance(files, list) or not 0 < len(files) <= 20000:
        raise FormatError('Unsupported device asset count')
    seen = set()
    for entry in files:
        if not isinstance(entry, dict):
            raise FormatError('Invalid device asset entry')
        name = entry.get('path')
        if not isinstance(name, str) or not name or '\\' in name or '\0' in name:
            raise FormatError('Invalid device asset path')
        path = PurePosixPath(name)
        if not path.parts or path.is_absolute() or '..' in path.parts or str(path) != name or name in seen:
            raise FormatError('Device asset path escapes ownership or is duplicated')
        seen.add(name)
        size = entry.get('size')
        if type(size) is not int or not 0 <= size <= 16 * 1024**3:
            raise FormatError('Unsupported device asset size')
        digest = entry.get('sha256')
        if not isinstance(digest, str) or not re.fullmatch('[0-9a-f]{64}', digest):
            raise FormatError('Invalid device asset digest')
    required = {'globalgamemanagers', 'Managed/Metadata/global-metadata.dat'}
    if not required <= seen:
        raise FormatError('Device assets lack required settings or metadata')
    return value


def data_manifest(root):
    root = root.resolve()
    if not root.is_dir():
        raise FormatError('Derived data directory is absent')
    files = []
    for path in sorted(root.rglob('*')):
        if path.is_symlink() or not path.resolve().is_relative_to(root):
            raise FormatError('Device data contains a symlink or unowned path')
        if not path.is_file():
            continue
        digest = hashlib.sha256()
        with path.open('rb') as stream:
            for block in iter(lambda: stream.read(1024 * 1024), b''):
                digest.update(block)
        files.append({'path': path.relative_to(root).as_posix(), 'size': path.stat().st_size, 'sha256': digest.hexdigest()})
    return validate_manifest({'format': 1, 'files': files})


def manifest_bytes(value):
    validate_manifest(value)
    return (json.dumps(value, sort_keys=True, separators=(',', ':')) + '\n').encode()
