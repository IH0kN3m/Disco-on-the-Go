import unittest
from disco_port.shader_registry import merge_builtin_registry,disabled_android_builtin

class ShaderRegistryTests(unittest.TestCase):
    def test_android_exclusions_require_exact_builtin_identity(self):
        self.assertIsNotNone(disabled_android_builtin('Hidden/VideoDecodeOSX',16002))
        self.assertIsNotNone(disabled_android_builtin('Hidden/VR/BlitFromTex2DToTexArraySlice',15312))
        self.assertIsNone(disabled_android_builtin('FO/Object',16002))
        self.assertIsNone(disabled_android_builtin('Hidden/VideoDecodeAndroid',16003))
        with self.assertRaises(ValueError):disabled_android_builtin('Hidden/VideoDecodeOSX',16003)
    def test_remaps_ownership_and_preserves_custom(self):
        custom = ({'m_FileID': 1, 'm_PathID': 19}, 'Custom')
        current = [custom, ({'m_FileID': 0, 'm_PathID': 0}, 'Video')]
        donor = [({'m_FileID': 7, 'm_PathID': 16003}, 'Video')]
        result = merge_builtin_registry(current, donor, 7, 2, {16003: 'Video'})
        self.assertEqual(result, [custom, ({'m_FileID': 2, 'm_PathID': 16003}, 'Video')])
        self.assertEqual(current[1][0]['m_PathID'], 0)

    def test_rejects_bad_object_or_collision(self):
        donor = [({'m_FileID': 2, 'm_PathID': 16}, 'Video')]
        with self.assertRaises(ValueError):
            merge_builtin_registry([], donor, 2, 3, {16: 'Wrong'})
        with self.assertRaises(ValueError):
            merge_builtin_registry([({'m_FileID': 3, 'm_PathID': 17}, 'Video')], donor, 2, 3, {16: 'Video'})

    def test_ignores_other_file_and_is_idempotent(self):
        donor = [({'m_FileID': 2, 'm_PathID': 16}, 'Video'), ({'m_FileID': 1, 'm_PathID': 8}, 'Custom')]
        result = merge_builtin_registry([], donor, 2, 3, {16: 'Video'})
        self.assertEqual(len(result), 1)
        self.assertEqual(merge_builtin_registry(result, donor, 2, 3, {16: 'Video'}), result)
        custom = [({'m_FileID': 1, 'm_PathID': 8}, 'Video')]
        self.assertEqual(merge_builtin_registry(custom, donor, 2, 3, {16: 'Video'}), custom)
