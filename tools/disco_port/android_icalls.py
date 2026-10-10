"""Checked scalar ARM64 stack layouts and original bridge generation."""
import hashlib
import re
import subprocess
from .android_engine import UNITY_SHA256
from .binary import FormatError

ENUM32={'GfxPrimitiveType','IndexFormat','ShaderChannel','VertexFormat','MeshUpdateFlags',
        'TextureFilterMode','GraphicsFormat','RenderTextureMemoryless','ShadowCastingMode',
        'LightProbeUsage','GfxRTLoadAction','GfxRTStoreAction','CubemapFace','ComputeQueueType',
        'TextCore::GlyphPackingMode','TextCore::RenderMode','QueryTriggerInteraction','CapsuleCollider2D::CapsuleDirection'}

def stack_layout(arguments):
    """Return (size, Apple offset, AAPCS64 offset) for stack scalars."""
    if len(arguments)>64:raise FormatError('Too many ABI arguments')
    registers={'int':0,'float':0};apple=android=0;result=[]
    for kind,size in arguments:
        if kind not in registers or size not in (1,2,4,8) or (kind=='float' and size not in (4,8)):
            raise FormatError('Unsupported ABI scalar')
        if registers[kind]<8:registers[kind]+=1;continue
        apple=(apple+size-1)&-size
        result.append((size,apple,android));apple+=size;android+=8
    return result

def scalar(name):
    if name.endswith(('*','&')):return 'int',8
    if name in ('float','double'):return 'float',4 if name=='float' else 8
    if name in ('char','unsigned char','bool'):return 'int',1
    if name in ('short','unsigned short'):return 'int',2
    if name in ('int','unsigned int') or name in ENUM32:return 'int',4
    if name in ('long','unsigned long','long long','unsigned long long'):return 'int',8
    raise FormatError('Unsupported engine ABI type: '+name)

def split_arguments(text):
    level=0;start=0;result=[]
    for i,c in enumerate(text):
        if c in '(<':level+=1
        elif c in ')>':level-=1
        elif c==',' and level==0:result.append(text[start:i].strip());start=i+1
        if level<0:raise FormatError('Unbalanced native signature')
    if level:raise FormatError('Unbalanced native signature')
    return result+[text[start:].strip()] if text else []

def stage_icall_bridges(engine,nm,output):
    if hashlib.file_digest(engine.open('rb'),'sha256').hexdigest()!=UNITY_SHA256:
        raise FormatError('Unsupported internal-call engine fingerprint')
    symbols=subprocess.check_output([str(nm),'-C',str(engine)],text=True)
    selected=[];unsupported=[]
    for line in symbols.splitlines():
        match=re.fullmatch(r'([0-9a-f]+) t (\w+)_CUSTOM_(\w+)\((.*)\)',line)
        if not match:continue
        address,owner,name,args=match.groups();args=split_arguments(args)
        if len(args)<=8:continue
        try:layout=stack_layout([scalar(a) for a in args])
        except FormatError as error:unsupported.append(str(error));continue
        if not any(a!=b for _,a,b in layout):continue
        if owner=='TextGenerator' and name=='Populate_Internal_Injected':continue # Independently tested assembly adapter.
        selected.append((int(address,16),'.'+owner+'::'+name,layout))
    selected.sort()
    asm=['.text','.p2align 2'];header=['#pragma once','#include <cstring>',
        'extern "C" {',f'__attribute__((visibility("hidden"))) void* DiscoIcallTargets[{len(selected)}]={{}};']
    for i,(address,name,layout) in enumerate(selected):
        symbol=f'DiscoIcallBridge{i}';frame=((len(layout)*8+16)+15)&-16
        header.append(f'void {symbol}();')
        asm += [f'.global {symbol}',f'.hidden {symbol}',f'.type {symbol}, %function',symbol+':','.cfi_startproc',
                f'sub sp, sp, #{frame}',f'.cfi_def_cfa_offset {frame}',f'stp x29,x30,[sp,#{frame-16}]',
                '.cfi_offset x29,-16','.cfi_offset x30,-8']
        for size,apple,android in layout:
            register='x9' if size==8 else 'w9';suffix={1:'b',2:'h',4:'',8:''}[size]
            asm += [f'ldr{suffix} {register},[sp,#{frame+apple}]',f'str{suffix} {register},[sp,#{android}]']
        asm += ['adrp x16, DiscoIcallTargets','add x16,x16,:lo12:DiscoIcallTargets',f'ldr x16,[x16,#{i*8}]','blr x16',
                f'ldp x29,x30,[sp,#{frame-16}]',f'add sp,sp,#{frame}','.cfi_def_cfa_offset 0','ret','.cfi_endproc',f'.size {symbol},.-{symbol}']
    header += ['}', 'struct DiscoIcallEntry { const char* suffix; uintptr_t offset; Il2CppMethodPointer bridge; };',
               'static const DiscoIcallEntry discoIcalls[] = {']
    for i,(address,name,_) in enumerate(selected):header.append(f'{{"{name}",0x{address:x},&DiscoIcallBridge{i}}},')
    header += ['};']
    asm+=['.section .note.GNU-stack,"",%progbits']
    (output/'GeneratedIcalls.S').write_text('\n'.join(asm)+'\n')
    (output/'GeneratedIcalls.h').write_text('\n'.join(header)+'\n')
    import json
    (output/'icall-abi.json').write_text(json.dumps({'bridges':selected,'unsupported_signatures':sorted(set(unsupported))},indent=2)+'\n')
