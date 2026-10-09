"""Bounded direct ARM64 call edges; indirect flow is reported, never guessed."""
from bisect import bisect_right
import struct
from .binary import FormatError
from .function_starts import function_end


def branch_target(word, address):
    if word & 0x7c000000 == 0x14000000: # B/BL
        bits, immediate = 26, word & 0x03ffffff
    elif word & 0xff000010 == 0x54000000 or word & 0x7e000000 == 0x34000000: # B.cond/CBZ/CBNZ
        bits, immediate = 19, (word >> 5) & 0x7ffff
    elif word & 0x7e000000 == 0x36000000: # TBZ/TBNZ
        bits, immediate = 14, (word >> 5) & 0x3fff
    else: return None
    if immediate & (1 << (bits - 1)): immediate -= 1 << bits
    return address + immediate * 4


def stub_slot(image, address):
    sections = [s for s in image.sections if s.name == '__stubs' and s.address <= address < s.address + s.size]
    if len(sections) != 1 or (address - sections[0].address) % 12:
        raise FormatError('Target is not an owned ARM64 import stub')
    code = struct.unpack_from('<3I', image.data, image.offset_for_address(address, 12))
    adrp, ldr, branch = code
    if adrp & 0x9f00001f != 0x90000010 or ldr & 0xffc003ff != 0xf9400210 or branch != 0xd61f0200:
        raise FormatError('Unsupported ARM64 stub instructions')
    immediate = ((adrp >> 29) & 3) | (((adrp >> 5) & 0x7ffff) << 2)
    if immediate & (1 << 20): immediate -= 1 << 21
    return (address & ~4095) + immediate * 4096 + ((ldr >> 10) & 4095) * 8


def initializer_calls(image, starts, bindings, root, limit=5000):
    if root not in starts or not 0 < limit <= 10000:
        raise FormatError('Invalid root or call-graph bound')
    bound = {}
    for record in bindings:
        address, name = record['address'], record['symbol']
        if address in bound and bound[address] != name:
            raise FormatError('Conflicting import symbols')
        bound[address] = name
    pending = [root]; visited = set(); imports = set(); unresolved = []; indirect = []
    while pending:
        begin = pending.pop()
        if begin in visited: continue
        if len(visited) >= limit:
            raise FormatError('Initializer graph exceeds bound')
        visited.add(begin)
        end = function_end(image, starts, begin)
        raw = image.data[image.offset_for_address(begin, end - begin):image.offset_for_address(begin, end - begin) + end - begin]
        for n, (word,) in enumerate(struct.iter_unpack('<I', raw)):
            at = begin + n * 4
            target = branch_target(word, at)
            if target is not None:
                if begin <= target < end: continue
                if image.executable(target):
                    index = bisect_right(starts, target) - 1
                    if index < 0 or not starts[index] <= target < function_end(image, starts, starts[index]):
                        raise FormatError('Direct branch lacks function ownership')
                    pending.append(starts[index])
                else:
                    try:
                        slot = stub_slot(image, target)
                        if slot not in bound: raise FormatError('Import stub has no binding')
                        imports.add(bound[slot])
                    except FormatError as error:
                        unresolved.append({'callsite': at, 'target': target, 'reason': str(error)})
            elif word & 0xfffffc1f in (0xd61f0000, 0xd63f0000):
                indirect.append(at)
    return {'root': root, 'function_count': len(visited), 'imports': sorted(imports),
            'unresolved_direct_edges': unresolved, 'indirect_calls_or_jumps': indirect,
            'scope': 'Conservative direct branch traversal, not complete dependency coverage; indirect targets and callbacks are unresolved'}
