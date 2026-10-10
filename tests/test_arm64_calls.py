from types import SimpleNamespace
import struct
import unittest
from disco_port.arm64_calls import branch_target, stub_slot
from disco_port.binary import FormatError, Section


class Arm64CallTests(unittest.TestCase):
    def test_forward_and_backward_direct_branches(self):
        self.assertEqual(branch_target(0x94000004, 0x1000), 0x1010)
        self.assertEqual(branch_target(0x17ffffff, 0x1000), 0xffc)
        self.assertEqual(branch_target(0x54000080, 0x1000), 0x1010)
        self.assertEqual(branch_target(0x35ffffe0, 0x1000), 0xffc)
        self.assertEqual(branch_target(0x36000080, 0x1000), 0x1010)
        self.assertIsNone(branch_target(0xd65f03c0, 0x1000))

    def test_stub_instruction_and_address_ownership(self):
        # ADRP x16, page+1; LDR x16,[x16,#24]; BR x16.
        raw = struct.pack('<3I', 0xb0000010, 0xf9400e10, 0xd61f0200)
        image = SimpleNamespace(data=raw, sections=[Section('__stubs','__TEXT',0x1000,12,0)],
                                offset_for_address=lambda a,n:a-0x1000)
        self.assertEqual(stub_slot(image,0x1000),0x2018)
        literal=struct.pack('<3I',0xd503201f,0x58000010|(7<<5),0xd61f0200)
        image.data=literal;self.assertEqual(stub_slot(image,0x1000),0x1020)
        image.data=raw
        for address in (0x1004,0x0ffc,0x100c):
            with self.assertRaises(FormatError):stub_slot(image,address)
        image.data=raw[:8]+struct.pack('<I',0xd65f03c0)
        with self.assertRaises(FormatError):stub_slot(image,0x1000)
