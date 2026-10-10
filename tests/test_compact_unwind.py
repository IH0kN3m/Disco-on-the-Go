import struct
import unittest
from disco_port.binary import FormatError
from disco_port.compact_unwind import records


def fixture():
    data=bytearray(96)
    struct.pack_into('<7I',data,0,1,28,1,32,1,36,2)
    struct.pack_into('<2I',data,28,0x54000003,0x2000)
    struct.pack_into('<6I',data,36,0x100,68,60,0x140,0,68)
    struct.pack_into('<2I',data,60,0x100,0x3000)
    struct.pack_into('<I4H',data,68,3,12,1,16,0)
    struct.pack_into('<I',data,80,0)
    return data


class CompactUnwindTests(unittest.TestCase):
    def test_compressed_ownership_and_personality(self):
        r=records(fixture())
        self.assertEqual(r,[dict(start=0x100,end=0x140,encoding=0x54000003,lsda=0x3000,personality_slot=0x2000)])
    def test_bounds_indices_and_lsda(self):
        mutations=[(0,'<I',2),(40,'<I',200),(80,'<I',0xff000000),(60,'<I',0x90),(28,'<I',0x04000003),(76,'<H',500)]
        for at,fmt,value in mutations:
            data=fixture();struct.pack_into(fmt,data,at,value)
            with self.assertRaises(FormatError):records(data)
        for size in (0,20,60,80):
            with self.assertRaises(FormatError):records(fixture()[:size])
