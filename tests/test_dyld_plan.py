import struct
from types import SimpleNamespace
import unittest
from disco_port.binary import FormatError, Segment
from disco_port.dyld_plan import Stream, fixups, exports


def fixture():
    data = bytearray(64)
    struct.pack_into('<QQQ', data, 32, 8, 16 | 1 << 63, 24)
    return SimpleNamespace(data=data, segments=[Segment('code', 0, 32, 0, 32, 5),
                            Segment('data', 32, 32, 32, 32, 3)], offset_for_address=lambda a, n: a)


def uleb(value):
    result = bytearray()
    while value >= 128:
        result.append((value & 127) | 128); value >>= 7
    result.append(value)
    return bytes(result)


class DyldPlanTests(unittest.TestCase):
    def test_leb_signed_overflow_and_truncation(self):
        self.assertEqual(Stream(b'\x7e').leb(True), -2)
        self.assertEqual(Stream(uleb(2**64-1)).leb(), 2**64-1)
        for raw in (b'\x80', b'\x80'*11, b'\xff'*9+b'\x02'):
            with self.assertRaises(FormatError): Stream(raw).leb()
        with self.assertRaises(FormatError): Stream(b'nonterminated').string()

    def test_rebases_preserve_tagged_targets_and_owned_slots(self):
        rows = fixups(fixture(), b'\x11\x21\x00\x53\x00', 'rebase')
        self.assertEqual(rows, [{'address': 32, 'target': 8}, {'address': 40, 'target': 16 | 1 << 63}, {'address': 48, 'target': 24}])
        for raw in (b'\x11\x22\x00\x51\x00', b'\x11\x20\x00\x51\x00',
                    b'\x12\x21\x00\x51\x00', b'\x11\x21\x01\x51\x00',
                    b'\x11\x21\x18\x52\x00', b'\x11\x21\x00\x51',
                    b'\x11\x21\x00\x51\x00\x11', b'\x11\x21\x00\x60'+uleb(1000001)+b'\0'):
            with self.subTest(raw=raw), self.assertRaises(FormatError): fixups(fixture(), raw, 'rebase')
        image = fixture(); struct.pack_into('<Q', image.data, 32, 1000)
        with self.assertRaises(FormatError): fixups(image, b'\x11\x21\x00\x51\x00', 'rebase')

    def test_bind_wraparound_lazy_reset_and_conflicting_duplicates(self):
        start = b'\x11\x40_malloc\0\x51\x71\x08\x90'
        # Dyld emits unsigned wraparound to walk backward through a segment.
        raw = start + b'\x80' + uleb(2**64-16) + b'\x90\0'
        self.assertEqual([v['address'] for v in fixups(fixture(), raw, 'bind', 1)], [40, 32])
        duplicate = start + b'\x80' + uleb(2**64-8) + b'\x90\0'
        self.assertEqual(len(fixups(fixture(), duplicate, 'bind', 1)), 1)
        conflict = start + b'\x40_free\0\x80' + uleb(2**64-8) + b'\x90\0'
        with self.assertRaises(FormatError): fixups(fixture(), conflict, 'bind', 1)
        lazy = b'\x11\x40_malloc\0\x71\0\x90\0\x11\x40_free\0\x71\x08\x90\0'
        self.assertEqual([v['symbol'] for v in fixups(fixture(), lazy, 'lazy', 1)], ['_malloc', '_free'])
        for raw in (b'\xd0\0', b'\x11\x40_x\0\x51\x71\x20\x90\0', start+b'\0\x90'):
            with self.assertRaises(FormatError): fixups(fixture(), raw, 'bind', 1)

    def test_export_trie_ownership_and_cycles(self):
        # Root -> '_a' terminal -> address 8.
        data = b'\0\x01_a\0\x06\x02\0\x08\0'
        self.assertEqual(exports(fixture(), data), {'_a': 8})
        for raw in (data[:8], b'\0\x01_a\0\0', b'\0\x01_a\0\x7f',
                    data[:7]+b'\x08'+data[8:], data[:8]+b'\x7f\0'):
            with self.assertRaises(FormatError): exports(fixture(), raw)

    def test_empty_edge_prefix_terminal(self):
        # Root -> _a -> empty terminal. A bounded leaf is valid dyld output.
        data=b'\0\1_a\0\6\0\1\0\x0a\2\0\x08\0'
        self.assertEqual(exports(fixture(),data),{'_a':8})
        with self.assertRaises(FormatError):exports(fixture(),data[:-1]+b'\1')
