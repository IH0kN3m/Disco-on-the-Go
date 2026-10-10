#!/usr/bin/env python3
"""Stage a pinned, private ARM64 image plus validated classic-dyld load plan."""
import hashlib
import json
from pathlib import Path
import struct
from disco_port.binary import MachO
from disco_port.build_inputs import validate_sources
from disco_port.dyld_plan import load_plan
from disco_port.arm64_calls import branch_target, stub_slot
from disco_port.android_exports import export_sources
from disco_port.mapped_package import image_package, unwind_package
from disco_port.arm64_baseline import baseline_image

ROOT = Path(__file__).resolve().parent.parent


def stage():
    hashes = validate_sources(ROOT / 'reference/Disco.app')
    image = MachO((ROOT / 'reference/Disco.app/Contents/Frameworks/GameAssembly.dylib').read_bytes())
    plan = load_plan(image)
    output = ROOT / 'artifacts/android/runtime'; output.mkdir(parents=True, exist_ok=True)
    translated, instructions=baseline_image(image)
    if instructions != [(0x1331df0,0xce000c40),(0x1bb9e4c,0xce140400),(0x1cbf490,0xce000c40)]:
        raise ValueError('Pinned ARM64 baseline instruction inventory changed')
    pack=image_package(translated,plan)
    (output / 'runtime.map').write_bytes(pack)
    if any(not image.executable(address) for address in plan['exports'].values()):
        raise ValueError('Runtime API exports must be executable functions')

    uw=unwind_package(image)
    (output/'unwind.map').write_bytes(uw)
    export_asm, export_header = export_sources(plan['exports'])
    (output/'RuntimeExports.S').write_text(export_asm)
    (output/'RuntimeExports.h').write_text(export_header)
    # Fail-fast native stubs identify unsupported imports during device execution.
    imports = sorted(set(b['symbol'] for b in plan['bindings']))
    slots = {b['address']: b['symbol'] for b in plan['bindings']}
    callable_names = set(); setjmp_stubs = set()
    for section in image.sections:
        if section.name == '__stubs':
            for address in range(section.address, section.address + section.size, 12):
                symbol = slots[stub_slot(image, address)]
                callable_names.add(symbol)
                if symbol == '__setjmp': setjmp_stubs.add(address)
    # This adapter spills registers only; forbid a general nonlocal-jump input.
    if any('longjmp' in name for name in imports):
        raise ValueError('Nonlocal jumps require a complete ABI adapter')
    jump_calls = []
    for section in image.sections:
        if section.name == '__text':
            begin = image.offset_for_address(section.address, section.size)
            for i, (word,) in enumerate(struct.iter_unpack('<I', image.data[begin:begin+section.size])):
                at = section.address + 4*i
                if branch_target(word, at) in setjmp_stubs: jump_calls.append(at)
    if jump_calls != [0x3afaf0]:
        raise ValueError('GC-only register spill callsite assumption changed')
    plugin_path=ROOT/'reference/Disco.app/Contents/PlugIns/AmplifyTextureNative.bundle/Contents/MacOS/AmplifyTextureNative'
    plugin_bytes=plugin_path.read_bytes()
    if hashlib.sha256(plugin_bytes).hexdigest()!='474612e980951feb0f855bf5e57ae86e89d9492f4b61a43b50f58967bddd297e':raise ValueError('Unsupported Amplify input')
    plugin=MachO(plugin_bytes);plugin_plan=load_plan(plugin)
    plugin_baseline, plugin_instructions=baseline_image(plugin)
    if plugin_instructions:raise ValueError('Amplify baseline needs additional validated translations')
    (output/'amplify.map').write_bytes(image_package(plugin_baseline,plugin_plan))
    (output/'amplify-unwind.map').write_bytes(unwind_package(plugin))
    plugin_slots={b['address']:b['symbol'] for b in plugin_plan['bindings']}
    for section in plugin.sections:
        if section.name=='__stubs':
            for address in range(section.address,section.address+section.size,12):callable_names.add(plugin_slots[stub_slot(plugin,address)])
    imports=sorted(set(imports)|{b['symbol'] for b in plugin_plan['bindings']})
    asm = ['.text', '.p2align 2']
    declarations = []
    for n, name in enumerate(imports):
        asm += [f'.global DiscoMissing_{n}', f'.hidden DiscoMissing_{n}', f'DiscoMissing_{n}:',
                f'mov w0, #{n}', 'mov x1, x30', 'b DiscoUnsupportedTrap']
        declarations.append(f'extern \"C\" void DiscoMissing_{n}();')
    asm += ['.section .note.GNU-stack,\"\",%progbits']
    (output / 'MissingImports.S').write_text('\n'.join(asm)+'\n')
    (output / 'MissingImports.h').write_text('#pragma once\n'+'\n'.join(declarations)+
        '\nstatic const char* missingNames[]={' + ','.join(json.dumps(n) for n in imports) + '};\n'+
        'static const bool missingCallable[]={' + ','.join('true' if n in callable_names else 'false' for n in imports) + '};\n'+
        'static void(*missingThunks[])()={' + ','.join(f'DiscoMissing_{n}' for n in range(len(imports))) + '};\n')
    summary = {'scope': 'Mac-derived runtime package for the Android compatibility provider',
               'source_hashes': hashes, 'map_sha256': hashlib.sha256(pack).hexdigest(),
               'baseline_eor3_translations': len(instructions),
               'image_bytes': len(image.data), 'virtual_bytes': max(s.address + s.virtual_size for s in image.segments),
               'segments': len(image.segments), 'rebases': len(plan['rebases']),
               'binding_records': len(plan['bindings']), 'binding_slots': len(set(b['address'] for b in plan['bindings'])),
               'import_symbols': len(set(b['symbol'] for b in plan['bindings'])),
               'exports': len(plan['exports']), 'initializers': len(plan['initializers'])}
    (output / 'plan.json').write_text(json.dumps(plan, indent=2) + '\n')
    (output / 'report.json').write_text(json.dumps(summary, indent=2) + '\n')
    print(json.dumps({k: v for k, v in summary.items() if k not in ('source_hashes', 'map_sha256')}, indent=2))
    return output, summary


if __name__ == '__main__':
    stage()
