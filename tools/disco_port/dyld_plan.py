"""Strict classic-dyld pointer fixup plan. Static parsing only; no native loading."""
from .binary import FormatError, unpack

MASK = (1 << 64) - 1
LIMIT = 1_000_000


class Stream:
    def __init__(self, data):
        self.data, self.at = data, 0

    def byte(self):
        if self.at >= len(self.data):
            raise FormatError('Truncated dyld stream')
        value = self.data[self.at]; self.at += 1
        return value

    def leb(self, signed=False):
        result = 0
        for n in range(10):
            b = self.byte(); result |= (b & 127) << (7 * n)
            if not b & 128:
                if signed and b & 64:
                    result -= 1 << (7 * (n + 1))
                if not (-(1 << 63) <= result < (1 << 63) if signed else 0 <= result <= MASK):
                    raise FormatError('Dyld LEB overflows 64 bits')
                return result
        raise FormatError('Oversized dyld LEB')

    def string(self):
        end = self.data.find(b'\0', self.at, min(len(self.data), self.at + 4096))
        if end < 0:
            raise FormatError('Unterminated dyld symbol')
        try:
            result = self.data[self.at:end].decode('ascii')
        except UnicodeDecodeError as error:
            raise FormatError('Non-ASCII dyld symbol') from error
        self.at = end + 1
        return result


def owner(image, address, size=8, writable=False):
    segments = [s for s in image.segments if s.address <= address and address + size <= s.address + s.virtual_size]
    if size <= 0 or len(segments) != 1 or (writable and not segments[0].protection & 2):
        raise FormatError('Missing, ambiguous or nonwritable fixup ownership')
    return segments[0]


def fixups(image, data, kind, libraries=0):
    if kind not in ('rebase', 'bind', 'lazy', 'weak'):
        raise FormatError('Unsupported dyld stream kind')
    if not data:
        return []
    stream = Stream(data)
    segment = None; relative = 0; pointer_type = 1 if kind == 'lazy' else 0
    symbol = ''; ordinal = 0; addend = 0; flags = 0
    result = []; seen = {}; done = False

    def emit():
        if pointer_type != 1 or segment is None or relative % 8:
            raise FormatError('Unsupported or unaligned pointer fixup')
        s = image.segments[segment]
        if relative + 8 > s.virtual_size:
            raise FormatError('Fixup escapes selected segment')
        address = s.address + relative
        owner(image, address, writable=True)
        if len(result) >= LIMIT:
            raise FormatError('Excessive fixups')
        if kind == 'rebase':
            value = unpack(image.data, '<Q', image.offset_for_address(address, 8))[0]
            # libc++ non-unique RTTI names use bit 63 as a tag. dyld adds the
            # slide while preserving that bit; it is not part of the address.
            owner(image, value & ~(1 << 63), 1)
            record = {'address': address, 'target': value}
        else:
            if not symbol or not -3 <= ordinal <= libraries or flags & ~9:
                raise FormatError('Invalid bind symbol, flags or ordinal')
            record = {'address': address, 'symbol': symbol, 'ordinal': ordinal,
                      'addend': addend, 'flags': flags, 'kind': kind}
        if address in seen:
            if kind == 'rebase' or seen[address] != record:
                raise FormatError('Conflicting or repeated rebase fixup')
            return # Some linkers emit an identical binding twice.
        seen[address] = record; result.append(record)

    while stream.at < len(data):
        byte = stream.byte(); op, imm = byte & 240, byte & 15
        if op == 0:
            if imm:
                raise FormatError('Invalid dyld DONE immediate')
            done = True
            if kind != 'lazy':
                if any(data[stream.at:]):
                    raise FormatError('Data follows dyld terminator')
                break
            segment = None; relative = 0; symbol = ''; ordinal = 0; addend = 0; flags = 0; pointer_type = 1
            continue
        done = False
        if kind == 'rebase':
            if op == 0x10:
                pointer_type = imm
            elif op == 0x20:
                segment = imm; relative = stream.leb()
            elif op == 0x30:
                relative = (relative + stream.leb()) & MASK
            elif op == 0x40:
                relative = (relative + imm * 8) & MASK
            elif op in (0x50, 0x60, 0x70, 0x80):
                count = imm if op == 0x50 else stream.leb() if op in (0x60, 0x80) else 1
                skip = stream.leb() if op in (0x70, 0x80) else 0
                if count > LIMIT - len(result):
                    raise FormatError('Rebase count exceeds limit')
                for _ in range(count):
                    emit(); relative = (relative + 8 + skip) & MASK
            else:
                raise FormatError('Unsupported rebase opcode')
        else:
            if op == 0x10: ordinal = imm
            elif op == 0x20: ordinal = stream.leb()
            elif op == 0x30: ordinal = imm - 16 if imm else 0
            elif op == 0x40: flags = imm; symbol = stream.string()
            elif op == 0x50: pointer_type = imm
            elif op == 0x60: addend = stream.leb(signed=True)
            elif op == 0x70: segment = imm; relative = stream.leb()
            elif op == 0x80: relative = (relative + stream.leb()) & MASK
            elif op in (0x90, 0xa0, 0xb0, 0xc0):
                count = stream.leb() if op == 0xc0 else 1
                skip = stream.leb() if op in (0xa0, 0xc0) else imm * 8 if op == 0xb0 else 0
                if count > LIMIT - len(result):
                    raise FormatError('Bind count exceeds limit')
                for _ in range(count):
                    emit(); relative = (relative + 8 + skip) & MASK
            else:
                raise FormatError('Unsupported bind opcode (including threaded binding)')
        if segment is not None and segment >= len(image.segments):
            raise FormatError('Invalid dyld segment index')
    if not done:
        raise FormatError('Missing dyld terminator')
    return result


def exports(image, data):
    result = {}; visited = set(); pending = [(0, '')]
    while pending:
        offset, prefix = pending.pop()
        if offset in visited or not 0 <= offset < len(data) or len(prefix) > 4096:
            raise FormatError('Cyclic, shared or out-of-bounds export trie')
        visited.add(offset)
        if len(visited) > 100000:
            raise FormatError('Export trie exceeds bound')
        stream = Stream(data); stream.at = offset
        size = stream.leb(); end = stream.at + size
        if end >= len(data): raise FormatError('Export terminal escapes trie')
        if size:
            terminal = Stream(data[stream.at:end]); flags = terminal.leb()
            if flags & ~4: raise FormatError('Unsupported export kind, re-export or resolver')
            address = terminal.leb()
            if terminal.at != size or not prefix or prefix in result:
                raise FormatError('Invalid export terminal')
            owner(image, address, 1); result[prefix] = address
        stream.at = end
        for _ in range(stream.byte()):
            edge = stream.string(); child = stream.leb()
            if not edge:
                # Apple may encode a prefix export in an empty-edge terminal
                # alongside a longer sibling (e.g. Foo and FooBar).
                leaf = Stream(data); leaf.at = child
                if not 0 <= child < len(data): raise FormatError('Empty edge escapes trie')
                terminal_size = leaf.leb(); leaf.at += terminal_size
                if not terminal_size or leaf.byte() != 0: raise FormatError('Empty edge must own a terminal leaf')
            pending.append((child, prefix + edge))
    return result


def load_plan(image):
    if image.architecture != 'arm64' or unpack(image.data, '<I', 12)[0] != 6:
        raise FormatError('Expected ARM64 Mach-O dylib')
    if not 0 < len(image.segments) <= 16 or min(s.address for s in image.segments) != 0:
        raise FormatError('Unsupported image segment layout')
    for s in image.segments:
        if not s.virtual_size or (s.address | s.virtual_size) % 16384 or s.protection not in (1, 3, 5):
            raise FormatError('Unsupported segment alignment/protection')
        owner(image, s.address, s.virtual_size)
    ordered = sorted(image.segments, key=lambda s: s.address)
    if any(a.address + a.virtual_size > b.address for a, b in zip(ordered, ordered[1:])):
        raise FormatError('Overlapping image segments')
    if max(s.address + s.virtual_size for s in image.segments) > 256 * 1024**2:
        raise FormatError('Image exceeds mapping bound')
    cursor = 32; streams = []; libraries = 0
    for _ in range(unpack(image.data, '<I', 16)[0]):
        command, size = unpack(image.data, '<II', cursor)
        if command in (0x80000034, 0x80000033): raise FormatError('Chained fixups/separate exports unsupported')
        if command in (0xc, 0x80000018, 0x8000001f): libraries += 1
        if command == 0x80000022:
            if size != 48: raise FormatError('Invalid dyld-info command size')
            streams.append(unpack(image.data, '<10I', cursor + 8))
        cursor += size
    if len(streams) != 1: raise FormatError('Expected one classic dyld-info table')
    payloads = []
    for offset, size in zip(streams[0][::2], streams[0][1::2]):
        if size and (size > 16 * 1024**2 or len([s for s in image.segments if s.name == '__LINKEDIT' and s.offset <= offset and offset + size <= s.offset + s.file_size]) != 1):
            raise FormatError('Dyld stream escapes linkedit')
        payloads.append(image.data[offset:offset + size])
    rebases = fixups(image, payloads[0], 'rebase')
    bindings = [f for k, blob in zip(('bind', 'weak', 'lazy'), payloads[1:4]) for f in fixups(image, blob, k, libraries)]
    # Weak bindings may intentionally replace regular/lazy slots; retain ordering.
    bindings.sort(key=lambda f: f['kind'] == 'weak')
    exported = exports(image, payloads[4])
    initializers = []
    for section in image.sections:
        if section.name == '__mod_init_func':
            if section.size % 8: raise FormatError('Misaligned initializer table')
            for i in range(section.size // 8):
                address = image.pointers(section.address + 8 * i, 1)[0]
                if not image.executable(address): raise FormatError('Initializer outside executable code')
                initializers.append(address)
    return {'rebases': rebases, 'bindings': bindings, 'exports': exported, 'initializers': initializers}
