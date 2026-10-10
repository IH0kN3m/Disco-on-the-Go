import unittest

from disco_port.unity_stage import modernize_ios_project, modernize_ios_trampoline, modernize_orientation_transition


class HierarchyTests(unittest.TestCase):
    def test_delegate_controller_is_updated_before_uikit_setter(self):
        original = '    _rootController = _window.rootViewController = vc;'
        changed = modernize_orientation_transition(original)
        self.assertLess(changed.index('_rootController = vc;'), changed.index('_window.rootViewController = vc;'))
        self.assertEqual(modernize_orientation_transition(changed), changed)
        for text in ('', original + original, changed + original):
            with self.assertRaises(ValueError): modernize_orientation_transition(text)

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
