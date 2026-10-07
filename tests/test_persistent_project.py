import copy
import unittest

from disco_port.binary import FormatError
from disco_port.persistent_project import persistent_filesystem, select_persistent_assets, select_increased_memory
from test_engine_project import project_fixture


def fixture():
    project = project_fixture(); o = project['objects']
    o['data'] = {'isa': 'PBXFileReference', 'path': 'Data'}
    o['data_build'] = {'isa': 'PBXBuildFile', 'fileRef': 'data'}
    o['resources'] = {'isa': 'PBXResourcesBuildPhase', 'files': ['data_build']}
    o['app']['buildPhases'] = ['resources']
    return project


class PersistentProjectTests(unittest.TestCase):
    def test_data_removed_only_from_app_and_engine_flag_added(self):
        project = fixture(); select_persistent_assets(project); o = project['objects']
        self.assertEqual(o['resources']['files'], [])
        self.assertEqual(o['data']['path'], 'Data')
        self.assertIn('DISCO_PERSISTENT_DATA=1', o['engine_debug']['buildSettings']['GCC_PREPROCESSOR_DEFINITIONS'])
        self.assertNotIn('GCC_PREPROCESSOR_DEFINITIONS', o['debug']['buildSettings'])

    def test_wrong_ownership_and_layout_rejected_before_changes(self):
        for change in ('owner', 'duplicate', 'type', 'definition'):
            project = fixture(); o = project['objects']
            if change == 'owner': o['engine']['buildPhases'].append('resources'); o['app']['buildPhases'] = []
            elif change == 'duplicate': o['resources']['files'].append('data_build')
            elif change == 'type': o['resources']['isa'] = 'PBXFrameworksBuildPhase'
            else: o['engine_debug']['buildSettings']['GCC_PREPROCESSOR_DEFINITIONS'] = 'CUSTOM'
            before = copy.deepcopy(project)
            with self.assertRaises(FormatError): select_persistent_assets(project)
            self.assertEqual(project, before)

    def test_filesystem_hook_is_bounded_and_single_use(self):
        text = 'extern "C" const char* UnityDataBundleDir()\n{\n    return original;\n}\n'
        changed = persistent_filesystem(text)
        self.assertIn('return DiscoNativeEngineDataRoot();', changed)
        self.assertIn('return original;', changed)
        for value in ('other', text + text, changed):
            with self.assertRaises(FormatError): persistent_filesystem(value)

    def test_memory_entitlement_belongs_only_to_app_and_preserves_other_material(self):
        project = fixture(); select_increased_memory(project); o = project['objects']
        self.assertEqual(o['debug']['buildSettings']['CODE_SIGN_ENTITLEMENTS'], 'EngineMemory.entitlements')
        self.assertNotIn('CODE_SIGN_ENTITLEMENTS', o['engine_debug']['buildSettings'])
        o['debug']['buildSettings']['CODE_SIGN_ENTITLEMENTS'] = 'Other.entitlements'
        before = copy.deepcopy(project)
        with self.assertRaises(FormatError): select_increased_memory(project)
        self.assertEqual(project, before)
