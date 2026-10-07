import copy
import unittest

from disco_port.binary import FormatError
from disco_port.device_launch import launch_arguments, validate_launch


class DeviceLaunchTests(unittest.TestCase):
    def test_lazy_scene_mode_reaches_device_environment(self):
        import json
        args = launch_arguments('fixture-device', 'org.fixture.game', 'fixture.json', 0, True)
        environment = json.loads(args[args.index('--environment-variables') + 1])
        self.assertEqual(environment, {'DISCO_TEXTURE_MIP_LIMIT': '0', 'DISCO_LAZY_SCENES': '1'})
        value = {'launchOptions': {'terminateExistingInstances': True, 'arguments': [],
                                  'environmentVariables': environment}, 'process': {'processIdentifier': 123}}
        self.assertEqual(validate_launch(value, 0, True), 123)
        value['launchOptions']['environmentVariables'].pop('DISCO_LAZY_SCENES')
        with self.assertRaises(FormatError): validate_launch(value, 0, True)
        with self.assertRaises(FormatError): launch_arguments('fixture-device', 'org.fixture.game', 'fixture.json', 0, 1)

    def test_coredevice_options_precede_application_argument_boundary(self):
        args = launch_arguments('fixture-device', 'org.fixture.game', 'fixture.json', 2)
        self.assertEqual(args[-1], 'org.fixture.game')
        self.assertLess(args.index('--environment-variables'), args.index('org.fixture.game'))
        value = {'launchOptions': {'terminateExistingInstances': True, 'arguments': [],
                                  'environmentVariables': {'DISCO_TEXTURE_MIP_LIMIT': '2'}},
                 'process': {'processIdentifier': 123}}
        self.assertEqual(validate_launch(value, 2), 123)
        for change in ('argument', 'restart', 'environment', 'pid'):
            wrong = copy.deepcopy(value)
            if change == 'argument': wrong['launchOptions']['arguments'] = ['--terminate-existing']
            elif change == 'restart': wrong['launchOptions']['terminateExistingInstances'] = False
            elif change == 'environment': wrong['launchOptions']['environmentVariables'] = {}
            else: wrong['process']['processIdentifier'] = True
            with self.assertRaises(FormatError): validate_launch(wrong, 2)

    def test_physical_ipads_and_both_coredevice_envelopes(self):
        from disco_port.device_launch import validate_ipad
        for model in ('iPad16,6', 'iPad16,3', 'iPad14,8', 'iPad99,1'):
            hardware = {'productType': model, 'reality': 'physical'}
            self.assertEqual(validate_ipad({'properties': {'hardware': hardware, 'software': {'osVersionNumber': '27.0'}}}), model)
            self.assertEqual(validate_ipad({'device': {'hardwareProperties': hardware, 'deviceProperties': {'osVersionNumber': '17.4.1'}}}), model)
        for model, reality, version in [('iPhone17,1', 'physical', '27.0'), ('iPad16,6', 'simulated', '27.0'),
                                         ('iPad16,6', 'physical', '16.6'), ('iPad16,6', 'physical', ''),
                                         ('iPad16,6', 'physical', 'garbage'), (None, 'physical', '27')]:
            with self.assertRaises(FormatError):
                validate_ipad({'properties': {'hardware': {'productType': model, 'reality': reality}, 'software': {'osVersionNumber': version}}})

    def test_structured_coredevice_os_version(self):
        from disco_port.device_launch import validate_ipad
        result = {'properties': {'hardware': {'productType': 'iPad16,6', 'reality': 'physical'},
                                 'software': {'osVersionNumber': {'components': [27, 0, 0, 0, 0],
                                                                 'originalComponentsCount': 2, 'stringValue': '27.0'}}}}
        self.assertEqual(validate_ipad(result), 'iPad16,6')
        for version in ({}, {'stringValue': None}, {'stringValue': '16.6'}, {'stringValue': '27garbage'}):
            result['properties']['software']['osVersionNumber'] = version
            with self.assertRaises(FormatError): validate_ipad(result)
