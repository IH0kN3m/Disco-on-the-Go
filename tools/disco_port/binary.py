"""Bounded Mach-O reading and VA translation; does not execute inspected code."""

from dataclasses import dataclass
import struct


class FormatError(ValueError):
    pass


def unpack(data, fmt, offset):
    size = struct.calcsize(fmt)
    if offset < 0 or offset + size > len(data):
        raise FormatError(f"Read outside file at {offset:#x}, size {size}")
    return struct.unpack_from(fmt, data, offset)


def read_string(data, offset, limit=None):
    end_limit = len(data) if limit is None else min(limit, len(data))
    if not 0 <= offset < end_limit:
        raise FormatError(f"String offset outside data: {offset:#x}")
    end = data.find(b"\0", offset, end_limit)
    if end == -1:
        raise FormatError(f"Unterminated string at {offset:#x}")
    try:
        return data[offset:end].decode("utf-8")
    except UnicodeDecodeError as error:
        raise FormatError(f"Invalid UTF-8 at {offset:#x}") from error


@dataclass(frozen=True)
class Segment:
    name: str
    address: int
    virtual_size: int
    offset: int
    file_size: int
    protection: int


@dataclass(frozen=True)
class Section:
    name: str
    segment: str
    address: int
    size: int
    offset: int


class MachO:
    def __init__(self, data, architecture="arm64"):
        cpu = {"arm64": 0x100000c, "x86_64": 0x1000007}[architecture]
        base, size = 0, len(data)
        magic = data[:4]
        if magic in (b"\xca\xfe\xba\xbe", b"\xca\xfe\xba\xbf"):
            count, = unpack(data, ">I", 4)
            fat64 = magic == b"\xca\xfe\xba\xbf"
            stride = 32 if fat64 else 20
            matches = []
            for i in range(count):
                values = unpack(data, ">IIQQII" if fat64 else ">IIIII", 8 + i * stride)
                if values[0] == cpu:
                    matches.append((values[2], values[3]))
            if len(matches) != 1:
                raise FormatError(f"Expected one {architecture} slice, found {len(matches)}")
            base, size = matches[0]
        if base < 0 or size < 32 or base + size > len(data):
            raise FormatError("Invalid Mach-O slice bounds")
        self.data = data[base:base + size]
        if self.data[:4] != b"\xcf\xfa\xed\xfe":
            raise FormatError("Only little-endian 64-bit Mach-O is supported")
        header = unpack(self.data, "<8I", 0)
        if header[1] != cpu:
            raise FormatError(f"Mach-O does not contain requested architecture {architecture}")
        self.architecture = architecture
        self.slice_offset = base
        self.segments = []
        self.sections = []
        cursor = 32
        command_end = cursor + header[5]
        if command_end > size:
            raise FormatError("Load commands exceed slice")
        for _ in range(header[4]):
            command, length = unpack(self.data, "<II", cursor)
            if length < 8 or cursor + length > command_end:
                raise FormatError("Invalid load command size")
            if command == 0x19:
                if length < 72:
                    raise FormatError("Truncated segment command")
                name = self.data[cursor + 8:cursor + 24].split(b"\0")[0].decode("ascii")
                address, vs, offset, fs, maximum, protection, count, flags = unpack(self.data, "<4Q4I", cursor + 24)
                if offset + fs > size or 72 + count * 80 > length or fs > vs:
                    raise FormatError("Invalid segment bounds")
                self.segments.append(Segment(name, address, vs, offset, fs, protection))
                for j in range(count):
                    start = cursor + 72 + j * 80
                    names = [self.data[start + k:start + k + 16].split(b"\0")[0].decode("ascii") for k in (0, 16)]
                    va, section_size, section_offset = unpack(self.data, "<QQI", start + 32)
                    self.sections.append(Section(names[0], names[1], va, section_size, section_offset))
            cursor += length
        if cursor != command_end:
            raise FormatError("Load command count and size disagree")

    def offset_for_address(self, address, size=1):
        if size < 0:
            raise FormatError("Negative address span")
        for segment in self.segments:
            relative = address - segment.address
            if 0 <= relative and relative + size <= segment.file_size:
                return segment.offset + relative
        raise FormatError(f"Address {address:#x} is not file-backed for {size} bytes")

    def address_for_offset(self, offset):
        for segment in self.segments:
            if segment.offset <= offset < segment.offset + segment.file_size:
                return segment.address + offset - segment.offset
        raise FormatError(f"Offset {offset:#x} does not belong to a segment")

    def pointers(self, address, count):
        offset = self.offset_for_address(address, count * 8)
        return unpack(self.data, f"<{count}Q", offset)

    def executable(self, address):
        # Unity places generated gameplay code in a dedicated `il2cpp` section.
        return any(s.name in ("__text", "il2cpp") and s.address <= address < s.address + s.size
                   for s in self.sections)

    def find_modules(self, images):
        """Identify CodeGenModule prefixes using name, token coverage, and code VAs.

        The first three 64-bit fields are stable for the v27 build. No claim is
        made about other registration structures or generic method tables.
        """
        result = {}
        for image in images:
            needle = image["name"].encode() + b"\0"
            string_offset = self.data.find(needle)
            candidates = {}
            while string_offset != -1:
                try:
                    name_address = self.address_for_offset(string_offset)
                except FormatError:
                    string_offset = self.data.find(needle, string_offset + 1)
                    continue
                pattern = struct.pack("<Q", name_address)
                for segment in self.segments:
                    if segment.protection & 4 or segment.file_size == 0:
                        continue
                    at = self.data.find(pattern, segment.offset, segment.offset + segment.file_size)
                    while at != -1:
                        if at % 8 == 0 and at + 24 <= segment.offset + segment.file_size:
                            _, count, table = unpack(self.data, "<3Q", at)
                            if 0 < count <= 1_000_000 and count == image["max_method_rid"]:
                                try:
                                    pointers = self.pointers(table, count)
                                    nonzero = [p for p in pointers if p]
                                    if nonzero and all(self.executable(p) for p in nonzero):
                                        candidates[at] = {"module_address": self.address_for_offset(at),
                                                          "pointer_table_address": table, "pointers": pointers}
                                except FormatError:
                                    pass
                        at = self.data.find(pattern, at + 1, segment.offset + segment.file_size)
                string_offset = self.data.find(needle, string_offset + 1)
            if len(candidates) > 1:
                raise FormatError(f"Ambiguous CodeGenModule for {image['name']}")
            if candidates:
                result[image["name"]] = next(iter(candidates.values()))
        return result
