"""Bounded Unity 2020 GLCore program reconstruction for GLES 3.2."""
import re
import struct
from .binary import FormatError

PRECISION='\n'.join('precision highp '+t+';' for t in ('float','int','sampler2D','sampler3D','samplerCube','sampler2DArray','sampler2DShadow','samplerCubeShadow','sampler2DArrayShadow','usampler2D','isampler2D','sampler2DMS','isampler2DMS','usampler2DMS'))


def source_to_gles(source):
    if not isinstance(source,str) or len(source)>2**20 or '\0' in source:raise FormatError('Invalid GLSL source')
    versions=re.findall(r'^\s*#version\s+(\d+)\s*$',source,re.M)
    if not versions or any(v not in ('150','330','410','420','430') for v in versions):raise FormatError('Unsupported GLCore language version')
    if '#ifdef VERTEX' not in source or '#ifdef FRAGMENT' not in source:raise FormatError('Expected paired vertex/fragment source')
    source=re.sub(r'^\s*#extension GL_ARB_(explicit_attrib_location|shader_bit_encoding|shading_language_420pack|gpu_shader5)\s*:[^\n]*','',source,flags=re.M)
    source=re.sub(r'^\s*#version\s+\d+\s*$', '#version 320 es\n'+PRECISION+'\n',source,flags=re.M)
    # GLES 3.1+ supports explicit uniform locations. Unity's serialized
    # sampler bindings rely on these locations; removing them changes which
    # uniforms the player updates even when the program links successfully.
    return source


def convert_program(raw):
    def integer(at):
        if at<0 or at+4>len(raw):raise FormatError('Truncated shader program')
        return struct.unpack_from('<i',raw,at)[0]
    if integer(0)!=201806140 or integer(4) not in (6,7,8):raise FormatError('Unsupported shader program version/type')
    at=24
    for _ in range(2):
        count=integer(at);at+=4
        if not 0<=count<=4096:raise FormatError('Invalid keyword count')
        for _ in range(count):
            n=integer(at);at+=4
            if not 0<=n<=4096 or at+n>len(raw):raise FormatError('Invalid keyword ownership')
            at=(at+n+3)&~3
    n=integer(at);start=at+4;end=start+n;aligned=(end+3)&~3
    if not 0<n<=2**20 or aligned>len(raw):raise FormatError('Invalid shader source ownership')
    try:code=source_to_gles(raw[start:end].decode('utf-8')).encode('utf-8')
    except UnicodeError as e:raise FormatError('Non-text GLCore source') from e
    result=bytearray(raw[:at]);struct.pack_into('<i',result,4,3)
    result+=struct.pack('<i',len(code))+code
    result+=bytes((-len(result))%4);result+=raw[aligned:]
    return bytes(result)


def convert_blob(raw):
    return convert_segments([raw])


def convert_segments(segments):
    if not segments or len(segments)>64 or any(len(s)>128*1024**2 for s in segments):raise FormatError('Invalid shader segments')
    raw=segments[0]
    if len(raw)<4:raise FormatError('Truncated shader table')
    count=struct.unpack_from('<i',raw)[0];table=4+count*12
    if not 0<count<=65536 or table>len(raw):raise FormatError('Invalid shader table count')
    result=bytearray(table);struct.pack_into('<i',result,0,count);owned=[]
    for i in range(count):
        offset,size,segment=struct.unpack_from('<iii',raw,4+12*i)
        if not 0<=segment<len(segments) or offset<(table if segment==0 else 0) or size<=0 or offset+size>len(segments[segment]):raise FormatError('Invalid shader program ownership')
        if any(segment==part and offset<end and begin<offset+size for part,begin,end in owned):raise FormatError('Overlapping shader program entries')
        owned.append((segment,offset,offset+size));program=convert_program(segments[segment][offset:offset+size])
        struct.pack_into('<iii',result,4+12*i,len(result),len(program),0);result+=program
    return bytes(result)
