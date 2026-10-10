from types import SimpleNamespace
import random
import struct
import unittest
from disco_port.arm64_baseline import branch, eor3_words, baseline_image
from disco_port.arm64_calls import branch_target
from disco_port.binary import FormatError, Section, Segment


class BaselineTests(unittest.TestCase):
    def test_all_operand_aliases_preserve_registers(self):
        randomizer = random.Random(123)
        for destination in range(4):
            for a in range(4):
                for b in range(4):
                    for c in range(4):
                        before = [randomizer.getrandbits(128) for _ in range(32)]
                        registers = before.copy()
                        word = 0xce000000 | destination | (a << 5) | (b << 16) | (c << 10)
                        for instruction in eor3_words(word):
                            if instruction == 0xd503201f: continue
                            kind = instruction & 0xffe0fc00
                            self.assertIn(kind, (0x6e201c00,0x4ea01c00))
                            n, m = registers[(instruction >> 5) & 31], registers[(instruction >> 16) & 31]
                            registers[instruction & 31] = n ^ m if kind == 0x6e201c00 else n | m
                        before[destination] = before[a] ^ before[b] ^ before[c]
                        self.assertEqual(registers, before)

    def test_branch_bounds_and_private_segment_ownership(self):
        for source, target in [(4, 0), (0, (1 << 27)-4)]:
            self.assertEqual(branch_target(branch(source, target), source), target)
        for source, target in [(0, 1 << 27), (1, 4)]:
            with self.assertRaises(FormatError): branch(source, target)
        with self.assertRaises(FormatError): eor3_words(0xd503201f)
        raw = struct.pack('<2I', 0xce140400, 0xd65f03c0)
        image = SimpleNamespace(data=raw, segments=[Segment('__TEXT',0,16384,0,8,5)],
            sections=[Section('__text','__TEXT',0,8,0)], offset_for_address=lambda a,n:a)
        adapted, patches = baseline_image(image)
        self.assertEqual(image.data, raw)
        self.assertEqual(patches, [(0,0xce140400)])
        self.assertEqual(branch_target(struct.unpack_from('<I',adapted.data)[0],0),16384)
        self.assertEqual(branch_target(struct.unpack_from('<I',adapted.data,16)[0],16392),4)
        self.assertEqual(adapted.segments[-1].protection,5)
        image.sections[0] = Section('__text','__TEXT',0,8,4)
        with self.assertRaises(FormatError): baseline_image(image)
