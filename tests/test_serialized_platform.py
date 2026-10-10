import struct
import unittest

from disco_port.binary import FormatError
from disco_port.serialized_platform import retag_serialized


def fixture():
    data = bytearray(128)
    struct.pack_into('>I', data, 8, 22)
    struct.pack_into('>IQQQ', data, 20, 32, len(data), 96, 0)
    data[48:60] = b'2020.3.12f1\0'
    struct.pack_into('<i', data, 60, 2)
    data[96:] = bytes(range(32))
    return data


class SerializedPlatformTests(unittest.TestCase):
    def test_only_platform_field_changes(self):
        data = fixture()
        output, offset = retag_serialized(data)
        self.assertEqual(offset, 60)
        self.assertEqual(struct.unpack_from('<i', output, offset)[0], 9)
        self.assertEqual(output[:offset], data[:offset])
        self.assertEqual(output[offset + 4:], data[offset + 4:])

    def test_android_and_unsupported_targets(self):
        data=fixture();output,offset=retag_serialized(data,13)
        self.assertEqual(struct.unpack_from("<i",output,offset)[0],13)
        self.assertEqual(output[offset+4:],data[offset+4:])
        with self.assertRaises(FormatError):retag_serialized(data,42)

    def test_metadata_bounds_size_and_version(self):
        for location, fmt, value in ((8, '>I', 21), (20, '>I', 1000), (20, '>I', 14),
                                     (24, '>Q', 127), (32, '>Q', 64), (40, '>Q', 1),
                                     (60, '<i', 9), (64, 'B', 2), (16, 'B', 1)):
            data = fixture()
            struct.pack_into(fmt, data, location, value)
            with self.assertRaises(FormatError):
                retag_serialized(data)
        with self.assertRaises(FormatError):
            retag_serialized(fixture()[:47])
        data = fixture()
        data[48:60] = b'2021.3.12f1\0'
        with self.assertRaises(FormatError):
            retag_serialized(data)
