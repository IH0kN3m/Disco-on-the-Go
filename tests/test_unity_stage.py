import unittest

from disco_port.binary import FormatError
from disco_port.unity_stage import flatten_normals, index_owned_components, modernize_ios_project, modernize_ios_trampoline, validate_parents


class HierarchyTests(unittest.TestCase):
    def test_local_component_ownership_and_duplicates(self):
        def component(file_id, owner):
            return {'type': 'MeshFilter', 'data': {'m_GameObject': {'m_FileID': file_id, 'm_PathID': owner}}}
        record = component(0, 7)
        self.assertEqual(index_owned_components([record], 'MeshFilter', {7: {}}), {7: record['data']})
        for records in ([component(1, 7)], [component(0, 8)], [record, record], [component(False, 7)]):
            with self.assertRaises(FormatError):
                index_owned_components(records, 'MeshFilter', {7: {}})

    def test_normal_count_and_malformed_values(self):
        self.assertEqual(flatten_normals(None, 2), [])
        self.assertEqual(flatten_normals([[0, 1, 0, 0]], 1), [0, 1, 0])
        for normals in (1, [None], [[0, 1]], [[0, float('nan'), 0]], [[0, True, 0]], [[0, '1', 0]], [[0, 1, 0], [0, 1, 0]]):
            with self.assertRaises(FormatError):
                flatten_normals(normals, 1)

    def test_shared_ancestors_and_unordered_nodes(self):
        validate_parents({4: 2, 3: 2, 2: 1, 1: None, 5: None})

    def test_cycles_and_missing_parent_fail(self):
        for parents in ({1: 1}, {1: 2, 2: 3, 3: 1}, {1: 2}):
            with self.assertRaises(FormatError):
                validate_parents(parents)

    def test_pinned_export_flags_and_unknown_layout(self):
        flag = '\t\t\t\t\t"-mno-thumb",\n'
        patched = modernize_ios_project(flag * 4 + 'ENABLE_BITCODE = YES;')
        self.assertNotIn('-mno-thumb', patched)
        self.assertEqual(patched, 'ENABLE_BITCODE = NO;')
        for unsupported in (flag * 3, flag * 4 + '-mno-thumb'):
            with self.assertRaises(ValueError):
                modernize_ios_project(unsupported)

    def test_scene_window_startup_and_unknown_layout(self):
        source = '- (BOOL)application:(UIApplication*)application didFinishLaunchingWithOptions:(NSDictionary*)launchOptions\n_window         = [[UIWindow alloc] initWithFrame: [UIScreen mainScreen].bounds];'
        patched = modernize_ios_trampoline(source, '// original scene adapter')
        self.assertIn('discoStartWithScene:', patched)
        self.assertIn('initWithWindowScene: scene', patched)
        for unsupported in ('', source + source, patched):
            with self.assertRaises(ValueError):
                modernize_ios_trampoline(unsupported, '')
