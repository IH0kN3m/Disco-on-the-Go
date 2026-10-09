import hashlib
import unittest
from disco_port.binary import FormatError
from disco_port.shader_inventory import platform_fingerprints


class ShaderInventoryTests(unittest.TestCase):
    def test_platform_and_segment_ownership(self):
        result = platform_fingerprints([4, 15], [[0], [2, 4]], [[2], [2, 2]], b'abcdef')
        self.assertEqual(result[4], [{'bytes': 2, 'sha256': hashlib.sha256(b'ab').hexdigest()}])
        self.assertEqual(len(result[15]), 2)

    def test_malformed_and_overlapping_ranges(self):
        cases = [([], [], []), ([15, 15], [[0], [2]], [[2], [2]]),
                 ([15], [], [[2]]), ([15], [[]], [[]]), ([15], [[0]], [[2, 2]]),
                 ([15], [[-1]], [[2]]), ([15], [[0]], [[0]]), ([15], [[5]], [[2]]),
                 ([4, 15], [[0], [1]], [[2], [2]])]
        for args in cases:
            with self.subTest(args=args), self.assertRaises(FormatError):
                platform_fingerprints(*args, b'abcdef')
