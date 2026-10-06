import struct
import tempfile
from pathlib import Path
import unittest

from disco_port.binary import FormatError
from disco_port.vtc import PageFile, crunch_header


def fixture():
    # Deliberately unordered block IDs and page IDs; each file owns its offsets.
    return (struct.pack("<II", 2, 2) + struct.pack("<IQI", 9, 5, 5) + struct.pack("<IQI", 2, 0, 5)
            + struct.pack("<III5H", 11, 9, 0, 1, 1, 1, 1, 1)
            + struct.pack("<III5H", 7, 2, 0, 1, 1, 1, 1, 1) + b"abcdefghij")


class VTCTests(unittest.TestCase):
    def test_owning_block_offsets_and_plane_prefix_sums(self):
        raw = fixture()
        parsed = PageFile(raw[:-10], len(raw))
        self.assertEqual(parsed.plane_span(7, 3), (87, 1))
        self.assertEqual(parsed.plane_span(11, 2), (91, 1))
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "test.vtc2"
            path.write_bytes(raw)
            opened = PageFile.open(path)
            self.assertEqual(opened.read_plane(path, 11, 2), b"h")
            other = Path(directory) / "other.vtc2"
            other.write_bytes(raw)
            with self.assertRaises(FormatError):
                opened.read_plane(other, 11, 2)
            path.write_bytes(raw[:-1])
            with self.assertRaises(FormatError):
                parsed.read_plane(path, 11, 2)

    def test_table_truncation_and_unsupported_counts(self):
        raw = fixture()
        for data in (b"", raw[:8], struct.pack("<II", 0, 2), struct.pack("<II", 2, 4_000_001), raw[:83]):
            with self.assertRaises(FormatError):
                PageFile(data, len(raw))

    def test_duplicate_missing_and_overlapping_ownership(self):
        raw = fixture()
        cases = [(24, "<I", 9), (40, "<I", 7), (44, "<I", 100),
                 (48, "<I", 1), (28, "<Q", 4), (20, "<I", 6)]
        for offset, fmt, value in cases:
            data = bytearray(raw[:-10])
            struct.pack_into(fmt, data, offset, value)
            with self.assertRaises(FormatError):
                PageFile(data, len(raw))

    def test_plane_and_page_bounds(self):
        raw = fixture()
        parsed = PageFile(raw[:-10], len(raw))
        for page, plane in ((99, 0), (7, -1), (7, 5), (7, True)):
            with self.assertRaises(FormatError):
                parsed.plane_span(page, plane)

    def test_crunch_rejects_non_crunch_and_unsafe_headers(self):
        data = bytearray(80)
        data[:2] = b"Hx"
        struct.pack_into(">H", data, 2, 74)
        struct.pack_into(">I", data, 6, 80)
        struct.pack_into(">HHBBB", data, 12, 136, 136, 1, 1, 0)
        data[65:67] = (1).to_bytes(2, "big")
        data[67:70] = (74).to_bytes(3, "big")
        data[70:74] = (75).to_bytes(4, "big")
        self.assertEqual(crunch_header(data)["block_bytes"], 8)
        for offset, fmt, value in ((6, ">I", 100), (12, ">H", 513), (16, "B", 2), (17, "B", 6),
                                   (18, "B", 20), (19, ">H", 1), (70, ">I", 90)):
            bad = bytearray(data)
            struct.pack_into(fmt, bad, offset, value)
            with self.assertRaises(FormatError):
                crunch_header(bad)
        for bad in (b"", b"not crunch", data[:73]):
            with self.assertRaises(FormatError):
                crunch_header(bad)
