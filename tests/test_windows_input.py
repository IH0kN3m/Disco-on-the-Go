import struct
import unittest
from disco_port.binary import FormatError
from disco_port.windows_input import pe_info


def fixture(managed=False):
    data=bytearray(2048);data[:2]=b'MZ';struct.pack_into('<I',data,60,64)
    data[64:68]=b'PE\0\0';struct.pack_into('<HHIIIHH',data,68,0x8664,1,0,0,0,240,0)
    optional=88;struct.pack_into('<H',data,optional,0x20b);struct.pack_into('<I',data,optional+108,16)
    section=optional+240;data[section:section+5]=b'.text'
    struct.pack_into('<4I',data,section+8,1536,4096,1536,512)
    if managed:
        struct.pack_into('<II',data,optional+112+14*8,4096,72)
        struct.pack_into('<IHHII',data,512,72,2,5,4168,256)
        meta=584;data[meta:meta+4]=b'BSJB';struct.pack_into('<I',data,meta+12,4);data[meta+16:meta+20]=b'v4\0\0'
        struct.pack_into('<HH',data,meta+20,0,1)
        struct.pack_into('<II',data,meta+24,36,42);data[meta+32:meta+36]=b'#~\0\0'
        table=meta+36;struct.pack_into('<Q',data,table+8,1<<6);struct.pack_into('<I',data,table+24,1)
        struct.pack_into('<IHHHHH',data,table+28,5120,0,0,0,0,0)
        data[1536:1538]=b'\x06\x2a' # Synthetic tiny IL body: ret.
    return data


class WindowsInputTests(unittest.TestCase):
    def test_native_and_cli_bodies_are_distinguished(self):
        self.assertEqual(pe_info(fixture()),{'machine':'x64','cli':False})
        result=pe_info(fixture(True))
        self.assertTrue(result['cli']);self.assertEqual(result['il_bodies'],1)
        self.assertEqual(result['trivial_or_stub_like_bodies'],1)
        data=fixture(True);struct.pack_into('<I',data,648,0)
        self.assertEqual(pe_info(data)['il_bodies'],0)

    def test_truncated_and_ambiguous_ownership_rejected(self):
        for data in (b'',b'MZ',fixture(True)[:650]):
            with self.assertRaises(FormatError):pe_info(data)
        for where,fmt,value in ((88+108,'<I',100),(328+20,'<I',2040),(88+112+14*8,'<I',999999),
                                (584+24,'<I',1),(620+24,'<I',1000001),(648,'<I',999999)):
            data=fixture(True);struct.pack_into(fmt,data,where,value)
            with self.subTest(where=where),self.assertRaises(FormatError):pe_info(data)
        data=fixture(True);struct.pack_into('<H',data,70,2);data[368:408]=data[328:368]
        with self.assertRaises(FormatError):pe_info(data)
