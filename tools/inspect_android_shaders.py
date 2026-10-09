#!/usr/bin/env python3
"""Extract bounded GLCore samples and stage GLES compile pairs under artifacts."""
import argparse
import hashlib
import json
from pathlib import Path
import struct
import UnityPy
from UnityPy.helpers import CompressionHelper
from UnityPy.export.ShaderConverter import ShaderProgram
from UnityPy.streams import EndianBinaryReader
from disco_port.android_shaders import gles_stage
from disco_port.binary import FormatError

ROOT=Path(__file__).resolve().parent.parent


def main(limit):
    if UnityPy.__version__!='1.25.4':raise FormatError('Expected UnityPy 1.25.4')
    root=ROOT/'reference/Disco.app/Contents/Resources/Data'
    output=ROOT/'artifacts/android/shaders';output.mkdir(parents=True,exist_ok=True)
    records=[];seen=set();inventory=[];errors=[]
    for name in ('globalgamemanagers.assets','resources.assets','sharedassets0.assets','Resources/unity_builtin_extra'):
        env=UnityPy.load((root/name).read_bytes())
        for obj in env.objects:
            if obj.type.name!='Shader':continue
            data=obj.read();inventory.append({'source':name,'id':obj.path_id,'platforms':data.platforms})
            if len(records)>=limit or 15 not in data.platforms:continue
            try:
                index=data.platforms.index(15)
                tables=[getattr(data,n)[index] for n in ('offsets','compressedLengths','decompressedLengths')]
                if any(not isinstance(t,list) or len(t)!=1 for t in tables):raise FormatError('Segmented shader requires separate support')
                offset,compressed,expanded=[t[0] for t in tables];blob=bytes(data.compressedBlob)
                if offset<0 or not 0<compressed<=len(blob)-offset or not 4<expanded<=64*1024**2:raise FormatError('Shader blob bounds invalid')
                raw=CompressionHelper.decompress_lz4(blob[offset:offset+compressed],expanded)
                if len(raw)!=expanded:raise FormatError('Shader expanded length mismatch')
                count=struct.unpack_from('<i',raw)[0]
                if not 0<count<=65536 or 4+12*count>len(raw):raise FormatError('Shader program count invalid')
                for at in range(count):
                    start,size,segment=struct.unpack_from('<iii',raw,4+12*at)
                    if segment!=0 or start<4+12*count or size<=0 or start+size>len(raw):raise FormatError('Unowned shader program range')
                program=ShaderProgram(EndianBinaryReader(raw,endian='<'),obj.version)
                for sub in program.m_SubPrograms:
                    code=bytes(sub.m_ProgramCode);digest=hashlib.sha256(code).hexdigest()
                    if digest in seen:continue
                    seen.add(digest)
                    text=code.decode('utf-8')
                    try:vertex,fragment=gles_stage(text,'vertex'),gles_stage(text,'fragment')
                    except FormatError:continue
                    entry=len(records)
                    (output/f'shader-{entry:03}.vert').write_text(vertex)
                    (output/f'shader-{entry:03}.frag').write_text(fragment)
                    records.append({'source':name,'shader_id':obj.path_id,'shader_name':data.m_ParsedForm.m_Name,'subprogram_type':int(sub.m_ProgramType),'source_sha256':digest})
                    break # One unique pair per shader, so large variant tables do not dominate the sample.
            except (ValueError,IndexError,struct.error) as error:
                errors.append({'source':name,'shader_id':obj.path_id,'error':str(error)})
    if not records:raise FormatError('No supported shader pairs recovered')
    (output/'shader-count.txt').write_text(str(len(records)))
    (output/'report.json').write_text(json.dumps({'scope':'Compile/link experiment only; no Unity material reconstruction or rendering validation','sample_pairs':records,'inventory':inventory,'errors':errors},indent=2)+'\n')
    print('Staged',len(records),'unique shader pairs from',len(inventory),'shader objects; rejected objects:',len(errors))

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--limit',type=int,default=24);a=p.parse_args()
    if not 1<=a.limit<=64:p.error('limit must be 1..64')
    main(a.limit)
