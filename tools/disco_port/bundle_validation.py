"""Validate the pinned UnityFS child scope and fingerprint owned data bodies."""

import hashlib
from pathlib import PurePosixPath

from .binary import FormatError


def bundle_bodies(bundle, platform):
    if bundle.signature != 'UnityFS' or bundle.version != 7 or not 0 < len(bundle.files) <= 65536:
        raise FormatError('Unsupported UnityFS container layout')
    result, serialized = {}, 0
    for name, child in bundle.files.items():
        path = PurePosixPath(name)
        if not name or path.is_absolute() or '..' in path.parts or '\\' in name:
            raise FormatError('Unsupported owned bundle child name')
        if hasattr(child, 'objects'):
            if child.header.version != 22 or child.unity_version != '2020.3.12f1' or child._m_target_platform != platform:
                raise FormatError('Unsupported startup serialized child')
            if len(child.objects) > 1000000:
                raise FormatError('Startup object count exceeds scope')
            serialized += 1
            for key, obj in child.objects.items():
                if type(key) is not int or not -(2**63) <= key < 2**63:
                    raise FormatError('Unsupported owned object identifier')
                result[name, key] = (int(obj.type), hashlib.sha256(obj.get_raw_data()).hexdigest())
        else:
            result[name, None] = hashlib.sha256(child.bytes).hexdigest()
    if not serialized:
        raise FormatError('Startup bundle has no serialized child')
    return result
