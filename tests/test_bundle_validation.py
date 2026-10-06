from types import SimpleNamespace
import unittest

from disco_port.binary import FormatError
from disco_port.bundle_validation import bundle_bodies


def fixture():
    obj = SimpleNamespace(type=28, get_raw_data=lambda: b'object bytes')
    child = SimpleNamespace(header=SimpleNamespace(version=22), unity_version='2020.3.12f1',
                            _m_target_platform=2, objects={17: obj})
    return SimpleNamespace(signature='UnityFS', version=7, files={'CAB-A': child, 'CAB-A.resS': SimpleNamespace(bytes=b'resource')})


class BundleValidationTests(unittest.TestCase):
    def test_owned_object_and_resource_fingerprints(self):
        bundle = fixture()
        before = bundle_bodies(bundle, 2)
        self.assertEqual(set(before), {('CAB-A', 17), ('CAB-A.resS', None)})
        bundle.files['CAB-A']._m_target_platform = 9
        self.assertEqual(bundle_bodies(bundle, 9), before)
        bundle.files['CAB-A'].objects[17].get_raw_data = lambda: b'changed'
        self.assertNotEqual(bundle_bodies(bundle, 9), before)

    def test_unsupported_layout_platform_and_child_ownership(self):
        for change in ('version', 'platform', 'child', 'object', 'empty'):
            bundle = fixture()
            if change == 'version': bundle.version = 6
            elif change == 'platform': bundle.files['CAB-A']._m_target_platform = 9
            elif change == 'child': bundle.files['../outside'] = bundle.files.pop('CAB-A')
            elif change == 'object': bundle.files['CAB-A'].objects[2**63] = bundle.files['CAB-A'].objects.pop(17)
            else: bundle.files.pop('CAB-A')
            with self.assertRaises(FormatError): bundle_bodies(bundle, 2)
