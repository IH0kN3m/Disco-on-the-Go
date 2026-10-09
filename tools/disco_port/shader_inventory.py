"""Validate and fingerprint serialized shader platform payloads without decoding."""
import hashlib
from .binary import FormatError


def platform_fingerprints(platforms, offsets, lengths, blob):
    if not 0 < len(platforms) <= 32 or len(set(platforms)) != len(platforms):
        raise FormatError('Invalid or duplicate shader platforms')
    if len(offsets) != len(platforms) or len(lengths) != len(platforms):
        raise FormatError('Shader platform tables differ in length')
    result = {}
    ranges = []
    for platform, starts, sizes in zip(platforms, offsets, lengths):
        if not 0 < len(starts) <= 64 or len(starts) != len(sizes):
            raise FormatError('Invalid shader segment table')
        segments = []
        for start, size in zip(starts, sizes):
            if start < 0 or size <= 0 or start + size > len(blob):
                raise FormatError('Shader segment escapes blob')
            ranges.append((start, start + size))
            segments.append({'bytes': size, 'sha256': hashlib.sha256(blob[start:start + size]).hexdigest()})
        result[platform] = segments
    ranges.sort()
    if any(a[1] > b[0] for a, b in zip(ranges, ranges[1:])):
        raise FormatError('Shader segments overlap')
    return result
