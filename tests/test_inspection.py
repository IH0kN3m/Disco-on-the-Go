import struct
import unittest

from disco_port.binary import FormatError, MachO
from disco_port.metadata import Metadata


def metadata_fixture():
    data = bytearray(256)
    struct.pack_into("<II", data, 0, 0xfab11baf, 27)
    strings = b"\0Example.dll\0Example\0Game\0Run\0amount\0value\0"
    string_indexes = {name: strings.index(name.encode() + b"\0") for name in ["Example.dll", "Example", "Game", "Run", "amount", "value"]}
    def table(index, content):
        struct.pack_into("<II", data, 8 + index * 8, len(data), len(content))
        data.extend(content)
    table(2, strings)
    table(5, struct.pack("<IiiiiI4H", string_indexes["Run"], 0, 2, 0, -1, 0x06000001, 0, 0, 0, 1))
    table(10, struct.pack("<IIi", string_indexes["amount"], 0x08000001, 3))
    table(11, struct.pack("<IiI", string_indexes["value"], 3, 0x04000001))
    row = [string_indexes["Example"], string_indexes["Game"], 0, -1, -1, -1, -1, 0,
           0, 0, -1, -1, -1, -1, -1, -1, 1, 0, 1, 0, 0, 0, 0, 0, 0, 0x02000001]
    table(19, struct.pack("<IIiiiiiI8i8HII", *row))
    table(20, struct.pack("<IiIiIiiIiI", string_indexes["Example.dll"], 0, 0, 1, 0, 0, -1, 0x20000001, 0, 0))
    return data


def macho_fixture(pointer=0x10000200):
    data = bytearray(1280)
    text_length = 72 + 2 * 80
    struct.pack_into("<8I", data, 0, 0xfeedfacf, 0x100000c, 0, 6, 2, text_length + 72, 0, 0)
    struct.pack_into("<II16s4Q4I", data, 32, 0x19, text_length, b"__TEXT", 0x10000000, 1024, 0, 1024, 5, 5, 2, 0)
    for j, (name, address, size, offset) in enumerate([(b"il2cpp", 0x10000200, 16, 512), (b"__cstring", 0x10000300, 32, 768)]):
        at = 32 + 72 + j * 80
        struct.pack_into("<16s16sQQI", data, at, name, b"__TEXT", address, size, offset)
    struct.pack_into("<II16s4Q4I", data, 32 + text_length, 0x19, 72, b"__DATA", 0x10001000, 512, 1024, 256, 3, 3, 0, 0)
    data[768:780] = b"Example.dll\0"
    struct.pack_into("<3Q", data, 1024, 0x10000300, 1, 0x10001040)
    struct.pack_into("<Q", data, 1088, pointer)
    return data


class MetadataTests(unittest.TestCase):
    def test_resolves_ownership_and_parameters(self):
        m = Metadata(metadata_fixture())
        self.assertEqual(m.methods[0]["qualified_name"], "Game.Example::Run")
        self.assertEqual(m.methods[0]["image"], "Example.dll")
        self.assertEqual(m.parameters[0]["name"], "amount")
        self.assertEqual(m.fields[0]["name"], "value")
        self.assertEqual(m.images[0]["max_method_rid"], 1)

    def test_rejects_version_and_truncated_tables(self):
        data = metadata_fixture()
        struct.pack_into("<I", data, 4, 29)
        with self.assertRaises(FormatError):
            Metadata(data)
        with self.assertRaises(FormatError):
            Metadata(metadata_fixture()[:-1])

    def test_rejects_invalid_method_owner(self):
        data = metadata_fixture()
        offset = struct.unpack_from("<I", data, 48)[0]
        struct.pack_into("<i", data, offset + 4, 20)
        with self.assertRaises(FormatError):
            Metadata(data)

    def test_rejects_invalid_parameter_range(self):
        data = metadata_fixture()
        offset = struct.unpack_from("<I", data, 48)[0]
        struct.pack_into("<H", data, offset + 30, 2)
        with self.assertRaises(FormatError):
            Metadata(data)


class MachOTests(unittest.TestCase):
    def test_address_translation_and_zero_fill(self):
        binary = MachO(macho_fixture())
        self.assertEqual(binary.offset_for_address(0x10001040, 8), 1088)
        self.assertEqual(binary.address_for_offset(1088), 0x10001040)
        with self.assertRaises(FormatError):
            binary.offset_for_address(0x10001100)
        with self.assertRaises(FormatError):
            binary.offset_for_address(0x100010f8, 16)

    def test_module_uses_il2cpp_section_and_token_coverage(self):
        binary = MachO(macho_fixture())
        modules = binary.find_modules([{"name": "Example.dll", "max_method_rid": 1}])
        self.assertEqual(modules["Example.dll"]["pointers"], (0x10000200,))
        self.assertFalse(binary.find_modules([{"name": "Example.dll", "max_method_rid": 2}]))

    def test_rejects_data_addresses_as_method_code(self):
        binary = MachO(macho_fixture(pointer=0x10000300))
        self.assertFalse(binary.find_modules([{"name": "Example.dll", "max_method_rid": 1}]))

    def test_fat_slice_offset_is_preserved(self):
        thin = macho_fixture()
        fat = bytearray(4096) + thin
        struct.pack_into(">II", fat, 0, 0xcafebabe, 1)
        struct.pack_into(">5I", fat, 8, 0x100000c, 0, 4096, len(thin), 12)
        binary = MachO(fat)
        self.assertEqual(binary.slice_offset, 4096)
        self.assertEqual(binary.offset_for_address(0x10001040), 1088)
        struct.pack_into(">I", fat, 16, len(fat))
        with self.assertRaises(FormatError):
            MachO(fat)

    def test_rejects_corrupt_load_commands(self):
        data = macho_fixture()
        struct.pack_into("<I", data, 36, 4)
        with self.assertRaises(FormatError):
            MachO(data)


if __name__ == "__main__":
    unittest.main()
