import struct
import unittest
from disco_port.binary import FormatError
from disco_port.native_literals import NativeLiterals


def fixture():
    data = bytearray(264) + bytearray('room\0α', 'utf-8')
    struct.pack_into('<6I', data, 0, 0xfab11baf, 27, 256, 8, 264, 7)
    struct.pack_into('<II', data, 256, 7, 0)
    return data


class NativeLiteralTests(unittest.TestCase):
    def test_encoded_string_resolves_exact_owned_bytes(self):
        self.assertEqual(NativeLiterals(fixture()).resolve(0xa0000001), 'room\0α')

    def test_invalid_usage_and_heap_ranges_are_rejected(self):
        for value in [True, -1, 2**32, 0xa0000000, 0x60000001, 0xa0000003]:
            with self.subTest(value=value), self.assertRaises(FormatError):
                NativeLiterals(fixture()).resolve(value)
        for position, value in [(4, 29), (12, 7), (16, 256), (20, 8), (256, 8), (260, 1)]:
            data = fixture()
            struct.pack_into('<I', data, position, value)
            with self.subTest(position=position), self.assertRaises(FormatError):
                NativeLiterals(data).resolve(0xa0000001)
        data = fixture(); data[-1] = 0xff
        with self.assertRaises(FormatError): NativeLiterals(data).resolve(0xa0000001)
