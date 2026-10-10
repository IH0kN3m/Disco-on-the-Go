"""Bounded validation of staged Unity 2020 GLES program ownership and sources."""
import re
import struct
from .binary import FormatError


def program_sources(segments):
    if not segments or len(segments)>64 or any(len(s)>256*1024**2 for s in segments):
        raise FormatError('Invalid shader segment count/size')
    raw=segments[0]
    if len(raw)<4:raise FormatError('Truncated shader table')
    count=struct.unpack_from('<i',raw)[0];table=4+count*12
    if not 0<=count<=65536 or table>len(raw):raise FormatError('Invalid shader program count')
    owned=[];result=[];entries=[]
    for i in range(count):
        offset,size,segment=struct.unpack_from('<iii',raw,4+12*i)
        if not 0<=segment<len(segments) or offset<(table if segment==0 else 0) or not 0<size<=len(segments[segment])-offset:
            raise FormatError('Shader program escapes owned segment')
        owned.append((segment,offset,offset+size));entries.append((segment,offset,size))
    owned.sort()
    if any(a[0]==b[0] and a[2]>b[1] for a,b in zip(owned,owned[1:])):raise FormatError('Overlapping shader program entries')
    for segment,offset,size in entries:
        data=segments[segment][offset:offset+size]
        def integer(at):
            if at<0 or at+4>len(data):raise FormatError('Truncated shader program')
            return struct.unpack_from('<i',data,at)[0]
        version,kind=integer(0),integer(4)
        if version!=201806140 or kind not in (2,3,4,5):raise FormatError('Unsupported GLES program version/type')
        at=24
        for _ in range(2):
            n=integer(at);at+=4
            if not 0<=n<=4096:raise FormatError('Invalid shader keyword count')
            for _ in range(n):
                n=integer(at);at+=4
                if not 0<=n<=4096 or n>len(data)-at:raise FormatError('Shader keyword escapes program')
                at=(at+n+3)&~3
        n=integer(at);at+=4
        if not 0<n<=1024**2 or ((at+n+3)&~3)>len(data):raise FormatError('Shader source escapes program')
        try:source=data[at:at+n].decode('utf-8')
        except UnicodeError as e:raise FormatError('Non-text GLES source') from e
        if '\0' in source:raise FormatError('NUL in GLES source')
        result.append({'type':kind,'source':source})
    return result


def stage_source(source,stage,program_type=3):
    if stage not in ('vertex','fragment') or not isinstance(source,str) or len(source)>1024**2 or '\0' in source:
        raise FormatError('Invalid GLES stage/source')
    versions=re.findall(r'^\s*#version\s+(\d+)(?:\s+(es))?\s*$',source,re.M)
    if not versions:versions=[('100','')] # Unity's exact GLES2 donor may omit #version.
    if len(set(versions))!=1 or versions[0] not in (('100',''),('300','es'),('310','es'),('320','es')):
        raise FormatError('Unsupported/mixed GLES language versions')
    if '#ifdef VERTEX' not in source or '#ifdef FRAGMENT' not in source:
        raise FormatError('Expected paired Unity GLES source')
    text=re.sub(r'^\s*#version[^\n]*','',source,flags=re.M)
    if program_type==4 and versions[0]==('300','es'):
        # Exact Android donor GLES3 shaders use HLSLcc's runtime feature switch.
        # ES 3.00 has no explicit uniform locations/bindings. Unity disables this
        # define for that language; converted GLES31 programs retain locations.
        text=text.replace('#define UNITY_SUPPORTS_UNIFORM_LOCATION 1','#define UNITY_SUPPORTS_UNIFORM_LOCATION 0')
    version=' '.join(v for v in versions[0] if v)
    return '#version '+version+'\n#define '+stage.upper()+' 1\n'+text


def referenced_programs(parsed,count):
    references=[]
    for sub in parsed['m_SubShaders']:
        for shader_pass in sub['m_Passes']:
            if shader_pass['m_Platforms'] not in ([],[9]):raise FormatError('Non-Android shader pass platform')
            for name,program in shader_pass.items():
                if not name.startswith('prog') or not isinstance(program,dict):continue
                for variant in program['m_SubPrograms']:
                    index=variant['m_BlobIndex'];kind=variant['m_GpuProgramType']
                    if type(index) is not int or not 0<=index<count or kind not in (2,3,4,5):
                        raise FormatError('Shader variant references an unowned GLES program')
                    references.append((index,kind,name))
    return references
