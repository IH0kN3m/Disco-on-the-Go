"""Translate SHA3 three-way XOR into baseline SIMD without clobbering other registers."""
import copy
import struct
from .binary import FormatError, Segment


def branch(source, destination):
    delta = destination-source
    if source % 4 or destination % 4 or not -(1 << 27) <= delta < (1 << 27):
        raise FormatError('Unaligned/out-of-range baseline branch')
    return 0x14000000 | ((delta//4) & 0x3ffffff)


def eor3_words(word):
    if word & 0xffe08000 != 0xce000000:
        raise FormatError('Expected EOR3 instruction')
    destination = word & 31
    operands = [(word >> 5) & 31, (word >> 16) & 31, (word >> 10) & 31]
    a, b, c = operands
    if a == b or a == c or b == c:
        remaining = c if a == b else b if a == c else a
        return 0x4ea01c00 | (remaining << 16) | (remaining << 5) | destination, 0xd503201f
    # Consume any old destination value in the first XOR; otherwise the
    # first write could destroy the third operand. Repeated operands work too.
    if destination in operands:
        operands.remove(destination)
        operands.insert(0, destination)
    a, b, c = operands
    def eor(n, m):
        return 0x6e201c00 | (m << 16) | (n << 5) | destination
    return eor(a, b), eor(destination, c)


def baseline_image(image):
    patches = []
    for section in image.sections:
        if section.name not in ('__text', 'il2cpp'):
            continue
        if section.address % 4 or section.size % 4:
            raise FormatError('Unaligned executable section')
        offset = image.offset_for_address(section.address, section.size)
        if offset != section.offset:
            raise FormatError('Executable section ownership differs from segment')
        for i, (word,) in enumerate(struct.iter_unpack('<I', image.data[offset:offset+section.size])):
            if word & 0xffe08000 == 0xce000000:
                patches.append((section.address+4*i, word))
    if not patches:
        return image, []
    start = (max(s.address+s.virtual_size for s in image.segments)+16383) & ~16383
    data = bytearray(image.data)
    island = bytearray()
    for address, word in patches:
        target = start+len(island)
        a, b = eor3_words(word)
        island += struct.pack('<3I', a, b, branch(target+8, address+4))
        struct.pack_into('<I', data, image.offset_for_address(address, 4), branch(address, target))
    if len(island) > 16384:
        raise FormatError('Baseline translation island exceeds bound')
    result = copy.copy(image)
    result.segments = [*image.segments, Segment('__DISCO_BASELINE', start, 16384, len(data), len(island), 5)]
    result.data = bytes(data+island)
    return result, patches
