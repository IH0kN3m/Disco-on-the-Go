import hashlib
import struct
import unittest
from disco_port.binary import FormatError, MachO
from disco_port.function_starts import function_starts
from disco_port.android_probe import checked_leaf, authorized_devices
from test_function_starts import fixture

class AndroidProbeTests(unittest.TestCase):
    def test_exact_leaf_bounds_and_digest(self):
        image=MachO(fixture()); starts=function_starts(image)
        digest=hashlib.sha256(image.data[512:516]).hexdigest()
        self.assertEqual(checked_leaf(image,starts,starts[0],4,digest),image.data[512:516])
        for address,size,hash_value in [(starts[0]+2,4,digest),(starts[0],8,digest),(starts[0],0,digest),
                                       (starts[0],128,digest),(starts[0],4,'0'*64)]:
            with self.assertRaises(FormatError): checked_leaf(image,starts,address,size,hash_value)
        data=bytearray(image.data);struct.pack_into('<I',data,32+72+48,513)
        with self.assertRaises(FormatError): checked_leaf(MachO(data),starts,starts[0],4,digest)

    def test_adb_states_and_ambiguous_or_malformed_input(self):
        self.assertEqual(authorized_devices('List of devices attached\nfixture-a device model:Tablet\nfixture-b unauthorized\nfixture-c offline\n'),['fixture-a'])
        self.assertEqual(authorized_devices('List of devices attached\n'),[])
        for value in ('bad header','List of devices attached\n-only device\n','List of devices attached\none\n',
                      'List of devices attached\na device\na device\n'):
            with self.assertRaises(FormatError): authorized_devices(value)
