import struct
import unittest
from disco_port.binary import FormatError, MachO
from disco_port.function_starts import function_starts, function_end
from test_inspection import macho_fixture


def fixture(table=b'\x80\x04\x04\0'):
    data = macho_fixture()
    data.extend(b'\0' * 256)
    # Add link-edit and starts commands in the unused load-command space.
    old = 32 + 232 + 72
    struct.pack_into('<II16s4Q4I', data, old, 0x19, 72, b'__LINKEDIT', 0x10002000, 256, 1280, 256, 1, 1, 0, 0)
    struct.pack_into('<4I', data, old + 72, 0x26, 16, 1280, len(table))
    struct.pack_into('<II', data, 16, 4, 232 + 72 + 72 + 16)
    data[1280:1280 + len(table)] = table
    return data


class FunctionStartTests(unittest.TestCase):
    def test_exact_code_owner_and_function_boundaries(self):
        image = MachO(fixture())
        starts = function_starts(image)
        self.assertEqual(starts, [0x10000200, 0x10000204])
        self.assertEqual(function_end(image, starts, starts[0]), 0x10000204)
        self.assertEqual(function_end(image, starts, starts[1]), 0x10000210)
        with self.assertRaises(FormatError): function_end(image, starts, 0x10000208)

    def test_malformed_deltas_terminators_and_section_ownership(self):
        for table in [b'', b'\x80', b'\x80\0', b'\xff' * 11, b'\x80\x04',
                      b'\x80\x04\0\x01', b'\x81\x04\0', b'\x80\x06\0']:
            with self.subTest(table=table), self.assertRaises(FormatError): function_starts(MachO(fixture(table)))
        data = fixture()
        struct.pack_into('<I', data, 32 + 232 + 72 + 72 + 8, 512)
        with self.assertRaises(FormatError): function_starts(MachO(data))


if __name__ == '__main__': unittest.main()
