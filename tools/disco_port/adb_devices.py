"""Validate authorized ADB selections without guessing a device."""
from .binary import FormatError


def authorized_devices(output):
    """No guessing when more than one Android device is connected."""
    lines = output.splitlines()
    if not lines or lines[0].strip() != 'List of devices attached':
        raise FormatError('Unsupported ADB device list')
    result = []
    for line in lines[1:]:
        if not line.strip(): continue
        fields = line.split()
        if len(fields) < 2 or fields[0].startswith('-'):
            raise FormatError('Malformed ADB device entry')
        if fields[1] == 'device': result.append(fields[0])
    if len(result) != len(set(result)):
        raise FormatError('Duplicate ADB device identity')
    return result
