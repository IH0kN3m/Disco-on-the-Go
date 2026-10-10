import copy
import struct
import unittest
from disco_port.branding import validate_icns, name_ipad_project, APP_NAME, IPAD_APP
from disco_port.binary import FormatError


class BrandingTests(unittest.TestCase):
    def test_icon_entry_bounds(self):
        valid=b'icns'+struct.pack('>I',19)+b'test'+struct.pack('>I',11)+b'png'
        validate_icns(valid)
        for invalid in (b'',b'icns'+struct.pack('>I',8),valid[:-1],
                        valid[:12]+struct.pack('>I',7)+valid[16:],
                        valid[:12]+struct.pack('>I',20)+valid[16:]):
            with self.assertRaises(FormatError):validate_icns(invalid)

    def test_name_preserves_identity_and_framework_settings(self):
        project={'objects':{
            'app':{'isa':'PBXNativeTarget','name':'Unity-iPhone','buildConfigurationList':'configs','productReference':'product'},
            'framework':{'isa':'PBXNativeTarget','name':'UnityFramework','buildConfigurationList':'other'},
            'configs':{'buildConfigurations':['debug']},'other':{'buildConfigurations':['fwdebug']},
            'debug':{'buildSettings':{'PRODUCT_BUNDLE_IDENTIFIER':'org.fixture.existing'}},
            'fwdebug':{'buildSettings':{'PRODUCT_NAME':'UnityFramework'}},'product':{'path':'old.app'}}}
        original=copy.deepcopy(project)
        name_ipad_project(project)
        self.assertEqual(project['objects']['debug']['buildSettings']['PRODUCT_NAME'],APP_NAME)
        self.assertEqual(project['objects']['debug']['buildSettings']['PRODUCT_BUNDLE_IDENTIFIER'],'org.fixture.existing')
        self.assertEqual(project['objects']['product']['path'],IPAD_APP)
        self.assertEqual(project['objects']['fwdebug'],original['objects']['fwdebug'])
        original['objects']['other']['buildConfigurations']=['debug']
        with self.assertRaises(FormatError):name_ipad_project(original)
