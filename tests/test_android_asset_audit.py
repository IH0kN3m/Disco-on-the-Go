import copy
import unittest
from disco_port.android_asset_audit import validate_texture_shape
from disco_port.binary import FormatError


class AndroidAssetAuditTests(unittest.TestCase):
    def test_empty_font_atlas_and_owned_stream(self):
        empty={'m_Width':0,'m_Height':0,'m_MipCount':1,'m_CompleteImageSize':0,'image data':b'', 'm_StreamData':{'offset':0,'size':0,'path':''}}
        self.assertEqual(validate_texture_shape(empty),'dynamic_empty')
        stored=copy.deepcopy(empty);stored.update(m_Width=256,m_Height=128,m_MipCount=9,m_CompleteImageSize=128)
        stored['m_StreamData'].update(offset=32,size=128,path='owned.resS')
        self.assertEqual(validate_texture_shape(stored),'stored')
        for key,value in (('m_Width',-1),('m_Height',32769),('m_MipCount',10),('image data',b'conflicting')):
            bad=copy.deepcopy(stored);bad[key]=value
            with self.assertRaises(FormatError):validate_texture_shape(bad)
        for key,value in (('offset',-1),('size',2**64),('path','')):
            bad=copy.deepcopy(stored);bad['m_StreamData'][key]=value
            with self.assertRaises(FormatError):validate_texture_shape(bad)
        bad=copy.deepcopy(empty);bad['m_CompleteImageSize']=1
        with self.assertRaises(FormatError):validate_texture_shape(bad)
