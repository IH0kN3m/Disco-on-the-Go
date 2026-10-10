import struct
import unittest
from disco_port.android_shader_blob import convert_blob,convert_program,convert_segments,source_to_gles
from disco_port.binary import FormatError

SOURCE='#ifdef VERTEX\n#version 150\nvoid main(){}\n#endif\n#ifdef FRAGMENT\n#version 150\nvoid main(){}\n#endif\n'
def program():
    code=SOURCE.encode();head=struct.pack('<8i',201806140,6,0,0,0,0,0,0)+struct.pack('<i',len(code))+code
    return head+bytes((-len(head))%4)+b'tail'

class AndroidShaderBlobTests(unittest.TestCase):
    def test_explicit_sampler_locations_survive_conversion(self):
        source=SOURCE.replace('void main(){}', '#define UNITY_LOCATION(x) layout(location = x)\nUNITY_LOCATION(7) uniform sampler2D atlas;\nvoid main(){}')
        converted=source_to_gles(source)
        self.assertIn('#define UNITY_LOCATION(x) layout(location = x)', converted)
        self.assertIn('UNITY_LOCATION(7) uniform sampler2D atlas;', converted)

    def test_segment_ownership_and_index_preservation(self):
        raw=program();table=struct.pack('<7i',2,0,len(raw),1,28,len(raw),0)
        result=convert_segments([table+raw,raw]);converted=convert_program(raw)
        self.assertEqual(struct.unpack_from('<7i',result),(2,28,len(converted),0,28+len(converted),len(converted),0))
        self.assertEqual(result[28:],converted*2)
        with self.assertRaises(FormatError):convert_segments([table+raw,raw[:-1]])

    def test_rebuild_preserves_trailing_bindings(self):
        raw=program();result=convert_program(raw)
        self.assertEqual(struct.unpack_from('<i',result,4)[0],3)
        self.assertTrue(result.endswith(b'tail'))
        self.assertEqual(result.count(b'#version 320 es'),2)
        blob=struct.pack('<4i',1,16,len(raw),0)+raw;rebuilt=convert_blob(blob)
        start,size,segment=struct.unpack_from('<3i',rebuilt,4)
        self.assertEqual((start,size,segment),(16,len(result),0));self.assertEqual(rebuilt[16:],result)
    def test_bounds_overlap_and_unsupported(self):
        raw=program()
        for blob in [b'',struct.pack('<i',99999),struct.pack('<4i',1,16,len(raw)+1,0)+raw,struct.pack('<4i',1,16,len(raw),1)+raw,struct.pack('<7i',2,28,len(raw),0,28,len(raw),0)+raw]:
            with self.assertRaises(FormatError):convert_blob(blob)
        for source in [SOURCE.replace('150','999'),SOURCE.replace('FRAGMENT','GEOMETRY'),SOURCE+'\0']:
            with self.assertRaises(FormatError):source_to_gles(source)
        with self.assertRaises(FormatError):convert_program(raw[:36])
