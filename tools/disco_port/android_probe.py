"""Static ownership checks for the narrowly pinned Android arithmetic probe."""
import hashlib
from .binary import FormatError
from .function_starts import function_end

DOT_ADDRESS = 0xf0f600
DOT_SHA256 = 'a259a63eb207a9a30b8701675f704d7c079989a8048cbce0909039b7694e0d5e'


def checked_leaf(image, starts, address, size, expected_hash):
    if image.architecture != 'arm64' or type(size) is not int or not 0 < size <= 64 or size % 4:
        raise FormatError('Unsupported isolated ARM64 leaf size or architecture')
    end = function_end(image, starts, address)
    if end - address != size:
        raise FormatError('Isolated leaf does not match exact function boundaries')
    offset = image.offset_for_address(address, size)
    sections = [s for s in image.sections if s.name in ('__text', 'il2cpp') and s.address <= address and end <= s.address + s.size]
    if len(sections) != 1 or sections[0].offset + address - sections[0].address != offset:
        raise FormatError('Isolated leaf file/address ownership mismatch')
    code = image.data[offset:offset + size]
    if hashlib.sha256(code).hexdigest() != expected_hash:
        raise FormatError('Isolated leaf differs from the inspected, dependency-free function')
    return code


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
