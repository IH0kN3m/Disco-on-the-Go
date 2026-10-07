import unittest

from disco_port.binary import FormatError
from disco_port.texture_memory import estimate_bc, mip_sizes


class TextureMemoryTests(unittest.TestCase):
    def test_full_chain_and_block_tail(self):
        value = estimate_bc('DXT1', 4096, 4096, 13)
        self.assertEqual(value['bc_bytes'], 11184824)
        self.assertEqual(value['fallback_bytes'], 89478484)
        self.assertEqual(value['levels'][-1]['bc_bytes'], 8)
        self.assertEqual(value['levels'][-1]['fallback_bytes'], 4)
        self.assertEqual(estimate_bc('BC6H', 4, 4, 1)['fallback_bytes'], 128)
        self.assertIsNone(estimate_bc('RGBA32', 4, 4, 1))

    def test_non_power_of_two_and_invalid_layouts(self):
        self.assertEqual(mip_sizes(5, 3, 1, 16, 4)['bc_bytes'], 32)
        for dimensions in [(0, 4, 1, 8, 4), (4, 4, 4, 8, 4), (4, 4, 0, 8, 4),
                           (True, 4, 1, 8, 4), (32769, 4, 1, 8, 4), (4, 4, 1, 9, 4)]:
            with self.assertRaises(FormatError):
                mip_sizes(*dimensions)
