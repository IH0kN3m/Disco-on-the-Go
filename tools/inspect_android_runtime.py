#!/usr/bin/env python3
"""Static Android ABI-gap inventory; matching symbol names do not prove ABI safety."""
import argparse
from collections import Counter
import json
from pathlib import Path
import struct
import subprocess
from disco_port.build_inputs import validate_sources
from disco_port.retarget import loader_info

ROOT=Path(__file__).resolve().parent.parent


def main(sdk):
    bundle=ROOT/'reference/Disco.app';hashes=validate_sources(bundle)
    source=bundle/'Contents/Frameworks/GameAssembly.dylib'
    image,loader=loader_info(source.read_bytes())
    imports=subprocess.check_output(['xcrun','nm','-arch','arm64','-u',str(source)],text=True).splitlines()
    imports=[s.strip() for s in imports if s.strip()]
    if len(imports)>10000:raise ValueError('Unexpected native import count')
    ndk=sdk/'ndk/27.2.12479018/toolchains/llvm/prebuilt/darwin-x86_64'
    exports=set()
    for name in ('libc.so','libm.so','libdl.so','liblog.so'):
        library=ndk/'sysroot/usr/lib/aarch64-linux-android/28'/name
        raw=subprocess.check_output([str(ndk/'bin/llvm-nm'),'-D','--defined-only',str(library)],text=True)
        exports.update(line.split()[-1].split('@')[0] for line in raw.splitlines() if len(line.split())>=3)
    records=[]
    for original in imports:
        name=original[1:] if original.startswith('_') else original
        if name.startswith(('_Z','__cxa','_Unwind','__gxx')):category='C++ ABI/exceptions; explicit compatibility required'
        elif name.startswith(('CF','NS','kCF','OBJC','objc_','mach_','thread_','dyld_','_NS','_DefaultRune','sysctl','getsectby')):category='Darwin or Objective-C service; bridge/replacement required'
        elif name.startswith('pthread_'):category='Thread ABI/structures; wrapper audit required'
        elif name in exports:category='Android C symbol name exists; signature/structure/flags audit required'
        else:category='No name match in selected Android API-28 C libraries'
        records.append({'source_symbol':original,'elf_candidate':name,'classification':category,'android_c_name_present':name in exports})
    svc=0;executable_bytes=0
    for section in image.sections:
        if section.name not in ('__text','il2cpp'):continue
        offset=image.offset_for_address(section.address,section.size)
        if section.size%4:raise ValueError('ARM64 code section is not instruction-aligned')
        executable_bytes+=section.size
        svc+=sum(word & 0xffe0001f==0xd4000001 for (word,) in struct.iter_unpack('<I',image.data[offset:offset+section.size]))
    commands=[];cursor=32
    for _ in range(struct.unpack_from('<I',image.data,16)[0]):
        command,length=struct.unpack_from('<II',image.data,cursor)
        if command==0x80000022:
            values=struct.unpack_from('<10I',image.data,cursor+8)
            commands.append(dict(zip(('rebase_offset','rebase_size','bind_offset','bind_size','weak_bind_offset','weak_bind_size','lazy_bind_offset','lazy_bind_size','export_offset','export_size'),values)))
        cursor+=length
    report={'scope':'Static ABI-gap evidence, not a Mach-O loader or verified Android runtime',
            'source_hashes':hashes,'loader':loader,'imports':records,'import_counts':dict(Counter(r['classification'] for r in records)),
            'executable_bytes':executable_bytes,'svc_instruction_matches':svc,'dyld_streams':commands}
    output=ROOT/'artifacts/android/runtime-audit.json';output.parent.mkdir(parents=True,exist_ok=True)
    output.write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps({'imports':len(imports),'groups':report['import_counts'],'svc_instruction_matches':svc},indent=2))

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--sdk',type=Path,default=Path.home()/'Library/Android/sdk');a=p.parse_args()
    main(a.sdk)
