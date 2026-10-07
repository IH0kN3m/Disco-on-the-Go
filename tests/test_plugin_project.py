import copy
import unittest
from disco_port.binary import FormatError
from disco_port.plugin_project import embed_framework, link_game_controller

def fixture():
    return {'objects': {'D15C00000000000000000002': {'isa':'PBXCopyFilesBuildPhase','dstSubfolderSpec':'10','files':[]},
        'app':{'isa':'PBXNativeTarget','productType':'com.apple.product-type.application','buildPhases':['D15C00000000000000000002']}}}

class PluginProjectTests(unittest.TestCase):
    def test_sdk_linkage_is_owned_and_idempotent(self):
        p = {'objects': {'engine': {'isa':'PBXNativeTarget','name':'UnityFramework','productType':'com.apple.product-type.framework','buildPhases':['link']},
                         'link': {'isa':'PBXFrameworksBuildPhase','files':[]}}}
        link_game_controller(p); before=copy.deepcopy(p)
        link_game_controller(p); self.assertEqual(p,before)
        file = p['objects']['D15C00000000000000000060']
        self.assertEqual(file['sourceTree'],'SDKROOT')
        self.assertEqual(len(p['objects']['link']['files']),1)

    def test_sdk_linkage_rejects_collisions_and_shared_phase(self):
        for change in ('collision','shared','owner','phase'):
            p = {'objects': {'engine': {'isa':'PBXNativeTarget','name':'UnityFramework','productType':'com.apple.product-type.framework','buildPhases':['link']},
                             'link': {'isa':'PBXFrameworksBuildPhase','files':[]}}}
            objects = p['objects']
            if change=='collision': objects['D15C00000000000000000060']={'path':'Other.framework'}
            elif change=='shared': objects['other']={'isa':'PBXNativeTarget','buildPhases':['link']}
            elif change=='owner': objects['engine']['productType']='com.apple.product-type.application'
            else: objects['engine']['buildPhases']=[]
            before=copy.deepcopy(p)
            with self.subTest(change=change),self.assertRaises(FormatError): link_game_controller(p)
            self.assertEqual(p,before)

    def test_signing_and_idempotent_app_ownership(self):
        p=fixture(); embed_framework(p,'Codec','file','build'); before=copy.deepcopy(p)
        embed_framework(p,'Codec','file','build'); self.assertEqual(p,before)
        self.assertIn('CodeSignOnCopy',p['objects']['build']['settings']['ATTRIBUTES'])
    def test_rejects_unowned_conflicting_and_duplicate_phase(self):
        for change in ('owner','destination','collision','duplicate','path'):
            p=fixture(); o=p['objects']
            if change=='owner': o['app']['buildPhases']=[]
            elif change=='destination': o['D15C00000000000000000002']['dstSubfolderSpec']='7'
            elif change=='collision': o['file']={'isa':'PBXFileReference','path':'Other.framework'}
            elif change=='duplicate': o['another']=copy.deepcopy(o['app'])
            else: o['another']={'path':'Frameworks/Codec.framework'}
            before=copy.deepcopy(p)
            with self.subTest(change=change),self.assertRaises(FormatError): embed_framework(p,'Codec','file','build')
            self.assertEqual(p,before)
