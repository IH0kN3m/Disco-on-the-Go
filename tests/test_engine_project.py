import copy
import unittest

from disco_port.binary import FormatError
from disco_port.engine_project import binding_registrations, select_original_provider


def project_fixture():
    objects = {
        'engine': {'isa': 'PBXNativeTarget', 'name': 'UnityFramework', 'buildPhases': ['sources', 'link'], 'buildConfigurationList': 'engine_configs'},
        'app': {'isa': 'PBXNativeTarget', 'name': 'Unity-iPhone', 'buildPhases': [], 'buildConfigurationList': 'configs'},
        'configs': {'isa': 'XCConfigurationList', 'buildConfigurations': ['debug']},
        'debug': {'isa': 'XCBuildConfiguration', 'buildSettings': {}},
        'engine_configs': {'isa': 'XCConfigurationList', 'buildConfigurations': ['engine_debug']},
        'engine_debug': {'isa': 'XCBuildConfiguration', 'buildSettings': {}},
        'sources': {'isa': 'PBXSourcesBuildPhase', 'files': ['managed_build', 'class_build', 'binding_build', 'options_build']},
        'link': {'isa': 'PBXFrameworksBuildPhase', 'files': ['provider_build']},
    }
    for name, path in (('managed', 'Classes/Native/Example.cpp'),
                       ('class', 'Classes/Native/UnityClassRegistration.cpp'),
                       ('binding', 'Classes/Native/UnityICallRegistration.cpp'),
                       ('options', 'Il2CppOptions.cpp'), ('provider', 'Libraries/libil2cpp.a')):
        objects[name] = {'isa': 'PBXFileReference', 'path': path}
        objects[name + '_build'] = {'isa': 'PBXBuildFile', 'fileRef': name}
    return {'objects': objects}


class EngineProjectTests(unittest.TestCase):
    def test_one_provider_and_source_ownership(self):
        project = project_fixture()
        self.assertEqual(select_original_provider(project), 1)
        objects = project['objects']
        self.assertNotIn('managed_build', objects['sources']['files'])
        self.assertIn('class_build', objects['sources']['files'])
        self.assertEqual(objects['provider']['path'], 'Frameworks/GameAssembly.framework')
        self.assertEqual(len(objects['app']['buildPhases']), 1)
        self.assertEqual(objects['debug']['buildSettings']['PRODUCT_BUNDLE_IDENTIFIER'], 'org.discoport.engineprobe')

    def test_rejects_missing_duplicate_or_wrong_owner(self):
        for change in ('missing', 'duplicate', 'owner', 'registration', 'options', 'config', 'target'):
            project = project_fixture()
            objects = project['objects']
            if change == 'missing':
                objects['provider']['path'] = 'Other.a'
            elif change == 'duplicate':
                objects['another'] = copy.deepcopy(objects['provider'])
            elif change == 'owner':
                objects['link']['files'] = []
            elif change == 'registration':
                objects['sources']['files'].remove('class_build')
            elif change == 'options':
                objects['sources']['files'].remove('options_build')
            elif change == 'config':
                objects['debug']['buildSettings'] = None
            else:
                objects['app2'] = copy.deepcopy(objects['app'])
            before = copy.deepcopy(project)
            with self.assertRaises(FormatError):
                select_original_provider(project)
            self.assertEqual(project, before)

    def test_bounded_symbol_names_and_empty_registration_set(self):
        symbol = '__Z14Register_TestAv'
        self.assertEqual(binding_registrations([symbol, symbol, '_irrelevant']), [symbol])
        with self.assertRaises(FormatError):
            binding_registrations(['__Z999Register_TestAv'])
        with self.assertRaises(FormatError):
            binding_registrations(['_irrelevant'])


class AppIdentifierTests(unittest.TestCase):
    def test_app_target_only_and_repeatable(self):
        from disco_port.engine_project import set_app_bundle_identifier
        project = project_fixture()
        engine = copy.deepcopy(project['objects']['engine_debug'])
        for _ in range(2): set_app_bundle_identifier(project, 'org.example.disco')
        self.assertEqual(project['objects']['debug']['buildSettings']['PRODUCT_BUNDLE_IDENTIFIER'], 'org.example.disco')
        self.assertEqual(project['objects']['engine_debug'], engine)

    def test_rejects_invalid_and_shared_configuration_without_mutating(self):
        from disco_port.engine_project import set_app_bundle_identifier
        for value in ('', 'single', 'com..bad', 'com/escape', 'com.bad;argument', None):
            project = project_fixture(); before = copy.deepcopy(project)
            with self.assertRaises(FormatError): set_app_bundle_identifier(project, value)
            self.assertEqual(project, before)
        project = project_fixture()
        project['objects']['engine_configs']['buildConfigurations'] = ['debug']
        before = copy.deepcopy(project)
        with self.assertRaises(FormatError): set_app_bundle_identifier(project, 'org.example.disco')
        self.assertEqual(project, before)
