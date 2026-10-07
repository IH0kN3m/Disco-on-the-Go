"""Bounded ARM64 Mach-O function starts; no game code is executed."""
from .binary import FormatError, unpack


def function_starts(image):
    if image.architecture != 'arm64':
        raise FormatError('Native analysis requires ARM64')
    command_count, command_bytes = unpack(image.data, '<II', 16)
    cursor = 32
    found = []
    for _ in range(command_count):
        command, length = unpack(image.data, '<II', cursor)
        if length < 8 or cursor + length > 32 + command_bytes:
            raise FormatError('Unowned function-start command')
        if command == 0x26:
            if length != 16:
                raise FormatError('Unsupported function-start layout')
            found.append(unpack(image.data, '<II', cursor + 8))
        cursor += length
    if len(found) != 1:
        raise FormatError('Expected one function-start table')
    offset, size = found[0]
    if not 0 < size <= 2 * 1024**2 or offset + size > len(image.data) or not any(
            s.name == '__LINKEDIT' and s.offset <= offset and offset + size <= s.offset + s.file_size
            for s in image.segments):
        raise FormatError('Function-start bytes escape link-edit ownership')
    text = [s for s in image.segments if s.name == '__TEXT']
    if len(text) != 1:
        raise FormatError('Expected one text base')
    table = image.data[offset:offset + size]
    at = 0
    address = text[0].address
    starts = []
    while at < len(table):
        value = shift = 0
        begin = at
        while True:
            if at >= len(table) or shift >= 64:
                raise FormatError('Truncated or oversized ULEB function delta')
            byte = table[at]; at += 1
            if shift == 63 and byte & 0x7e:
                raise FormatError('Function delta overflows UInt64')
            value |= (byte & 0x7f) << shift
            if not byte & 0x80:
                if at - begin > 1 and byte == 0:
                    raise FormatError('Noncanonical function delta')
                break
            shift += 7
        if value == 0:
            if any(table[at:]) or not starts:
                raise FormatError('Malformed function-start terminator')
            return starts
        address += value
        if address >= 2**64 or address % 4 or not image.executable(address):
            raise FormatError('Function start is not owned ARM64 code')
        image.offset_for_address(address, 4)
        starts.append(address)
        if len(starts) > 250000:
            raise FormatError('Unsupported function count')
    raise FormatError('Missing function-start terminator')


def function_end(image, starts, address):
    from bisect import bisect_left
    index = bisect_left(starts, address)
    if index == len(starts) or starts[index] != address:
        raise FormatError('Target is not an exact function start')
    sections = [s for s in image.sections if s.name in ('__text', 'il2cpp') and s.address <= address < s.address + s.size]
    if len(sections) != 1:
        raise FormatError('Ambiguous target code ownership')
    end = sections[0].address + sections[0].size
    if index + 1 < len(starts):
        end = min(end, starts[index + 1])
    if not address < end or end - address > 1024**2:
        raise FormatError('Unsupported target function size')
    image.offset_for_address(address, end - address)
    return end
