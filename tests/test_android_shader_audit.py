import struct
import unittest
from disco_port.android_shader_audit import program_sources,stage_source,referenced_programs
from disco_port.binary import FormatError

SOURCE='#ifdef VERTEX\n#version 320 es\nvoid main(){}\n#endif\n#ifdef FRAGMENT\n#version 320 es\nvoid main(){}\n#endif\n'

def fixture(source=SOURCE):
    code=source.encode();raw=struct.pack('<9i',201806140,3,0,0,0,0,0,0,len(code))+code
    raw+=bytes((-len(raw))%4)
    return struct.pack('<4i',1,16,len(raw),0)+raw


class AndroidShaderAuditTests(unittest.TestCase):
    def test_program_and_stage_ownership(self):
        programs=program_sources([fixture()]);self.assertEqual(programs,[{'type':3,'source':SOURCE}])
        vertex=stage_source(SOURCE,'vertex');self.assertTrue(vertex.startswith('#version 320 es\n#define VERTEX 1\n'))
        self.assertEqual(vertex.count('#version'),1)
        donor=SOURCE.replace('320 es','300 es').replace('void main(){}','#define UNITY_SUPPORTS_UNIFORM_LOCATION 1\nvoid main(){}')
        self.assertIn('UNITY_SUPPORTS_UNIFORM_LOCATION 0',stage_source(donor,'fragment',4))
        self.assertIn('UNITY_SUPPORTS_UNIFORM_LOCATION 1',stage_source(donor,'fragment',3))
        parsed={'m_SubShaders':[{'m_Passes':[{'m_Platforms':[9],'progVertex':{'m_SubPrograms':[{'m_BlobIndex':0,'m_GpuProgramType':3}]}}]}]}
        self.assertEqual(referenced_programs(parsed,1),[(0,3,'progVertex')])
        with self.assertRaises(FormatError):referenced_programs(parsed,0)
        parsed['m_SubShaders'][0]['m_Passes'][0]['m_Platforms']=[15]
        with self.assertRaises(FormatError):referenced_programs(parsed,1)

    def test_malformed_programs_and_versions(self):
        blob=fixture()
        for data in (b'',blob[:-1],struct.pack('<i',65537),struct.pack('<4i',1,0,10,0)+blob[16:]):
            with self.assertRaises(FormatError):program_sources([data])
        overlapping=struct.pack('<7i',2,28,len(blob)-16,0,28,len(blob)-16,0)+blob[16:]
        with self.assertRaises(FormatError):program_sources([overlapping])
        for source in (SOURCE.replace('320 es','430'),SOURCE.replace('FRAGMENT','GEOMETRY'),SOURCE+'\0',SOURCE.replace('320 es','300 es',1)):
            with self.assertRaises(FormatError):stage_source(source,'vertex')
        with self.assertRaises(FormatError):program_sources([fixture(SOURCE+'\0')])
