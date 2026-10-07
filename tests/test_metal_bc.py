import struct
import unittest

from disco_port.binary import FormatError
from disco_port.metal_bc import embedded_bitcode, rename_metal_definitions
from test_inspection import macho_fixture


class MetalBCTests(unittest.TestCase):
    def test_bitcode_requires_owned_object_section(self):
        data = macho_fixture()
        struct.pack_into('<I', data, 12, 1)
        section = 32 + 72
        data[section:section + 16] = b'__bitcode' + bytes(7)
        data[section + 16:section + 32] = b'__LLVM' + bytes(10)
        size = struct.unpack_from('<Q', data, section + 40)[0]
        self.assertEqual(embedded_bitcode(data), data[512:512 + size])
        for location, value in ((12, 6), (section + 48, 0), (section + 48, 10000), (section + 40, 0)):
            bad = bytearray(data); struct.pack_into('<I', bad, location, value)
            with self.assertRaises(FormatError): embedded_bitcode(bad)

    def test_definitions_and_references_reject_ambiguous_replacements(self):
        prefix = '[151 x i32]\ngetelementptr inbounds %struct.GraphicsCaps, ptr %0, i64 0, i32 52\n'
        body = 'define hidden i32 @metalFoo(i64 %0) {\nret i32 0\n}\ncall i32 @metalFoo(i64 4)\n@switch.table.metalFoo = constant i32 0\n'
        actual = rename_metal_definitions(prefix + body, {'Foo': 'metalFoo'})
        self.assertIn('call i32 @DiscoOriginalMetalFoo(i64 4)', actual)
        self.assertIn('@switch.table.metalFoo', actual)
        for text in (body, prefix, prefix + body + body, actual):
            with self.assertRaises(FormatError): rename_metal_definitions(text, {'Foo': 'metalFoo'})
