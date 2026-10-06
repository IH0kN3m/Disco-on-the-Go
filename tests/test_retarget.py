import struct
import unittest

from disco_port.binary import FormatError
from disco_port.retarget import ios_dependency, loader_info
from test_inspection import macho_fixture


def fixture():
    data = macho_fixture()
    end = 32 + struct.unpack_from('<I', data, 20)[0]
    name = b'/usr/lib/libSystem.B.dylib\0'
    length = (24 + len(name) + 7) & ~7
    command = struct.pack('<6I', 0xC, length, 24, 0, 0, 0) + name
    command += bytes(length - len(command))
    build = struct.pack('<6I', 0x32, 24, 1, 0xB0000, 0xD0000, 0)
    data[end:end + length + 24] = command + build
    struct.pack_into('<II', data, 16, 4, end - 32 + length + 24)
    return data, end


class RetargetTests(unittest.TestCase):
    def test_library_and_executable_ownership(self):
        data, _ = fixture()
        _, info = loader_info(data)
        self.assertEqual(info['platform'], 1)
        self.assertEqual(info['dependencies'], ['/usr/lib/libSystem.B.dylib'])
        self.assertIn('il2cpp', info['executable_sha256'])
        bad = bytearray(data)
        struct.pack_into('<I', bad, 32 + 72 + 48, 513)
        with self.assertRaises(FormatError):
            loader_info(bad)
        duplicate = bytearray(data)
        # Give the second, otherwise valid section the same executable name.
        duplicate[184:200] = b'il2cpp' + bytes(10)
        with self.assertRaisesRegex(FormatError, 'Duplicate executable'):
            loader_info(duplicate)

    def test_malformed_library_names_and_platform_layout(self):
        data, offset = fixture()
        for location, value in ((offset + 8, 8), (offset + 8, 10000), (12, 2), (offset + 56 + 20, 1)):
            bad = bytearray(data)
            struct.pack_into('<I', bad, location, value)
            with self.assertRaises(FormatError):
                loader_info(bad)
        bad = bytearray(data)
        # Remove the name terminator and command padding without touching the next command.
        length = struct.unpack_from('<I', bad, offset + 4)[0]
        bad[offset + 24:offset + length] = b'x' * (length - 24)
        with self.assertRaises(FormatError):
            loader_info(bad)

    def test_supported_dependency_translation_and_explicit_rejection(self):
        self.assertEqual(ios_dependency('/System/Library/Frameworks/Foundation.framework/Versions/C/Foundation'),
                         '/System/Library/Frameworks/Foundation.framework/Foundation')
        self.assertEqual(ios_dependency('/usr/lib/libc++.1.dylib'), '/usr/lib/libc++.1.dylib')
        for name in ('/System/Library/Frameworks/AppKit.framework/Versions/C/AppKit', '@rpath/Unknown.dylib',
                     '/System/Library/Frameworks/Foundation.framework/Versions/C/Security'):
            with self.assertRaises(FormatError):
                ios_dependency(name)
