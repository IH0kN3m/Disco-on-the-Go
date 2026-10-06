"""Bounded reader for the supplied build's five-plane VTC2 page containers."""

from dataclasses import dataclass
import hashlib
from pathlib import Path
import struct

from .binary import FormatError, unpack


@dataclass(frozen=True)
class Block:
    identifier: int
    offset: int
    size: int


@dataclass(frozen=True)
class Page:
    identifier: int
    block: int
    offset: int
    plane_sizes: tuple


class PageFile:
    def __init__(self, header, file_size):
        block_count, page_count = unpack(header, "<II", 0)
        if not 0 < block_count <= 1_000_000 or not 0 < page_count <= 4_000_000:
            raise FormatError("Unsupported VTC2 block/page counts")
        self.payload_offset = 8 + 16 * block_count + 22 * page_count
        if len(header) != self.payload_offset or self.payload_offset >= file_size:
            raise FormatError("Truncated or unsupported five-plane VTC2 tables")
        self.file_size = file_size
        self.path = None
        self.table_sha256 = hashlib.sha256(header).hexdigest()
        self.blocks, self.pages = {}, {}
        cursor = 8
        for _ in range(block_count):
            identifier, offset, size = unpack(header, "<IQI", cursor)
            cursor += 16
            if identifier in self.blocks or not size or offset + size > file_size - self.payload_offset:
                raise FormatError("Duplicate block or block outside payload")
            self.blocks[identifier] = Block(identifier, offset, size)
        self._coverage([(b.offset, b.size) for b in self.blocks.values()], file_size - self.payload_offset, "block")
        spans = {i: [] for i in self.blocks}
        for _ in range(page_count):
            identifier, block, offset, *sizes = unpack(header, "<III5H", cursor)
            cursor += 22
            if identifier in self.pages or block not in self.blocks or not sum(sizes):
                raise FormatError("Duplicate page, missing block, or empty page")
            if offset + sum(sizes) > self.blocks[block].size:
                raise FormatError("Page exceeds its owning block")
            self.pages[identifier] = Page(identifier, block, offset, tuple(sizes))
            spans[block].append((offset, sum(sizes)))
        for identifier, block in self.blocks.items():
            self._coverage(spans[identifier], block.size, "page")

    @staticmethod
    def _coverage(spans, length, kind):
        cursor = 0
        for offset, size in sorted(spans):
            if offset != cursor:
                raise FormatError(f"Overlapping or uncovered VTC2 {kind} spans")
            cursor += size
        if cursor != length:
            raise FormatError(f"Uncovered VTC2 {kind} payload")

    @classmethod
    def open(cls, path):
        with Path(path).open("rb") as stream:
            counts = stream.read(8)
            a, b = unpack(counts, "<II", 0)
            length = 8 + 16 * a + 22 * b
            size = Path(path).stat().st_size
            if length > min(size, 128 * 1024 * 1024):
                raise FormatError("VTC2 tables exceed file or inspection limit")
            header = counts + stream.read(length - 8)
        result = cls(header, size)
        result.path = Path(path).resolve()
        return result

    def plane_span(self, page_id, plane):
        if type(plane) is not int or not 0 <= plane < 5:
            raise FormatError("VTC2 plane must be 0..4")
        if page_id not in self.pages:
            raise FormatError(f"Unknown page index {page_id}")
        page = self.pages[page_id]
        block = self.blocks[page.block]
        return (self.payload_offset + block.offset + page.offset + sum(page.plane_sizes[:plane]), page.plane_sizes[plane])

    def read_plane(self, path, page_id, plane):
        if self.path is not None and Path(path).resolve() != self.path:
            raise FormatError("Page payload must be read from its owning container")
        offset, size = self.plane_span(page_id, plane)
        with Path(path).open("rb") as stream:
            stream.seek(0, 2)
            if stream.tell() != self.file_size:
                raise FormatError("VTC2 file size changed since inspection")
            stream.seek(offset)
            data = stream.read(size)
        if len(data) != size:
            raise FormatError("VTC2 plane truncated while reading")
        return data


def crunch_header(data):
    if len(data) < 74 or data[:2] != b"Hx":
        raise FormatError("Plane is not a supported Crunch stream")
    header_size, = unpack(data, ">H", 2)
    data_size, = unpack(data, ">I", 6)
    width, height, levels, faces, format_id = unpack(data, ">HHBBB", 12)
    flags, = unpack(data, ">H", 19)
    if header_size != 74 or data_size != len(data) or levels != 1 or faces != 1 or flags:
        raise FormatError("Unsupported Crunch header, faces, levels, or segmented layout")
    if not 0 < width <= 512 or not 0 < height <= 512 or format_id not in (0, 2, 7, 8):
        raise FormatError("Unsupported Crunch page dimensions or BC format")
    for start in (33, 41, 49, 57):
        offset = int.from_bytes(data[start:start + 3], "big")
        size = int.from_bytes(data[start + 3:start + 6], "big")
        count = int.from_bytes(data[start + 6:start + 8], "big")
        if offset + size > len(data) or count > 8192 or (size and offset < header_size):
            raise FormatError("Crunch palette outside plane")
    tables_size = int.from_bytes(data[65:67], "big")
    tables_offset = int.from_bytes(data[67:70], "big")
    level_offset = int.from_bytes(data[70:74], "big")
    if tables_offset < header_size or tables_offset + tables_size > len(data) or not header_size <= level_offset < len(data):
        raise FormatError("Crunch tables or mip payload outside plane")
    return {"width": width, "height": height, "format": format_id,
            "block_bytes": 8 if format_id == 0 else 16}


def decode_crunch(data):
    from importlib.metadata import version
    if version("texture2ddecoder") != "1.0.6":
        raise FormatError("Expected texture2ddecoder 1.0.6; run make setup-scenes")
    import texture2ddecoder
    info = crunch_header(data)
    try:
        # This Unity build uses Unity's Crunch bitstream variant. The generic
        # decoder can return the same byte count while producing scrambled BC blocks.
        blocks = texture2ddecoder.unpack_unity_crunch(data)
        expected = ((info["width"] + 3) // 4) * ((info["height"] + 3) // 4) * info["block_bytes"]
        if len(blocks) != expected:
            raise FormatError("Decoded BC payload length disagrees with Crunch header")
        function = {0: texture2ddecoder.decode_bc1, 2: texture2ddecoder.decode_bc3,
                    7: texture2ddecoder.decode_bc5, 8: texture2ddecoder.decode_bc5}[info["format"]]
        pixels = function(blocks, info["width"], info["height"])
    except RuntimeError as error:
        raise FormatError(f"Crunch decoding failed: {error}") from error
    if len(pixels) != info["width"] * info["height"] * 4:
        raise FormatError("Decoded pixel count disagrees with Crunch header")
    # Decoder output is BGRA. DXN_YX has its two channels reversed.
    if info["format"] == 8:
        swapped = bytearray(pixels)
        for i in range(0, len(swapped), 4):
            swapped[i + 1], swapped[i + 2] = swapped[i + 2], swapped[i + 1]
        pixels = bytes(swapped)
    info["codec"] = "Unity Crunch"
    return info, pixels
