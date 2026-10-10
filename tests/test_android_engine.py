import struct
import unittest
from disco_port.android_engine import executable_offset,adapt_desktop_audio
from disco_port.binary import FormatError

class AndroidEngineTests(unittest.TestCase):
    def test_executable_ownership(self):
        data=bytearray(256);data[:7]=b'\x7fELF\x02\x01\x01'
        struct.pack_into('<H',data,18,183);struct.pack_into('<Q',data,32,64);struct.pack_into('<HH',data,54,56,1)
        struct.pack_into('<IIQQQQQQ',data,64,1,5,128,0x1000,0,128,128,4096)
        self.assertEqual(executable_offset(data,0x1010,12),144)
        for address,size in ((0xfff,4),(0x107f,4),(0x1000,0)):
            with self.assertRaises(FormatError):executable_offset(data,address,size)
        data[68]=4
        with self.assertRaises(FormatError):executable_offset(data,0x1010,12)
        with self.assertRaises(FormatError):adapt_desktop_audio(data)
    def test_malformed_elf(self):
        for data in (b'',bytes(64),b'\x7fELF\x02\x01\x01'+bytes(200)):
            with self.assertRaises(FormatError):executable_offset(data,0,4)
