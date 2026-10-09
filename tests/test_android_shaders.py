import unittest
from disco_port.binary import FormatError
from disco_port.android_shaders import gles_stage

class AndroidShaderTests(unittest.TestCase):
    def test_stage_selection_and_only_desktop_uniform_locations_removed(self):
        source='''#ifdef VERTEX
#version 330
#extension GL_ARB_explicit_attrib_location : require
#define UNITY_LOCATION(x) layout(location = x)
layout(location=0) in vec4 position;
void main(){gl_Position=position;}
#endif
#ifdef FRAGMENT
#version 330
layout(location=0) out vec4 color;
void main(){color=vec4(1);}
#endif
'''
        for stage in ('vertex','fragment'):
            result=gles_stage(source,stage)
            self.assertTrue(result.startswith('#version 320 es\n#define '+stage.upper()))
            self.assertEqual(result.count('#version'),1)
            self.assertNotIn('GL_ARB_explicit_attrib_location',result)
            self.assertIn('#define UNITY_LOCATION(x)\n',result)
            self.assertIn('layout(location=0) out vec4 color;',result)
    def test_rejects_unrecognized_or_unbounded_source(self):
        for source,stage in [('', 'vertex'),('#version 999\n#ifdef VERTEX\n#ifdef FRAGMENT','vertex'),
                             ('#version 330\n#ifdef VERTEX','fragment'),('x\0','vertex'),('x'*1048577,'vertex'),
                             ('#version 330\n#ifdef VERTEX\n#ifdef FRAGMENT','geometry')]:
            with self.assertRaises(FormatError):gles_stage(source,stage)
