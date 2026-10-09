#!/usr/bin/env python3
"""Stage a pinned, private ARM64 image plus validated classic-dyld load plan."""
import hashlib
import json
from pathlib import Path
import struct
from disco_port.binary import MachO
from disco_port.build_inputs import validate_sources
from disco_port.dyld_plan import load_plan
from disco_port.android_probe import DOT_ADDRESS, DOT_SHA256, checked_leaf
from disco_port.function_starts import function_starts
from disco_port.arm64_calls import branch_target, stub_slot

ROOT = Path(__file__).resolve().parent.parent


def stage():
    hashes = validate_sources(ROOT / 'reference/Disco.app')
    image = MachO((ROOT / 'reference/Disco.app/Contents/Frameworks/GameAssembly.dylib').read_bytes())
    checked_leaf(image, function_starts(image), DOT_ADDRESS, 24, DOT_SHA256)
    plan = load_plan(image)
    names = sorted(set(b['symbol'] for b in plan['bindings']) | set(plan['exports']))
    strings = bytearray(); offsets = {}
    for name in names:
        offsets[name] = len(strings); strings += name.encode('ascii') + b'\0'
    output = ROOT / 'artifacts/android/runtime'; output.mkdir(parents=True, exist_ok=True)
    pack = bytearray(struct.pack('<8s6IQ', b'DSCMAP01', len(image.segments), len(plan['rebases']),
                                len(plan['bindings']), len(plan['exports']), len(plan['initializers']), len(strings), len(image.data)))
    for s in image.segments:
        pack += struct.pack('<5Q', s.address, s.virtual_size, s.offset, s.file_size, s.protection)
    for r in plan['rebases']:
        pack += struct.pack('<2Q', r['address'], r['target'])
    for b in plan['bindings']:
        pack += struct.pack('<QIi qII', b['address'], offsets[b['symbol']], b['ordinal'], b['addend'],
                            b['flags'], {'bind': 0, 'lazy': 1, 'weak': 2}[b['kind']])
    for name, address in sorted(plan['exports'].items()):
        pack += struct.pack('<QII', address, offsets[name], 0)
    for address in plan['initializers']:
        pack += struct.pack('<Q', address)
    pack += strings; pack += image.data
    (output / 'runtime.map').write_bytes(pack)
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
    # Hash-pinned diagnostic entry points; native boot is an explicit experiment.
    if plan['initializers'][0] != 0x253c:
        raise ValueError('Pinned clock initializer changed')
    (output / 'RuntimePins.h').write_text(
        '#pragma once\nnamespace RuntimePins {\n'
        f'constexpr unsigned long long Dot={DOT_ADDRESS};\n'
        'constexpr unsigned long long ClockInit=0x253c, ClockData=0x2bf0e98, ClockRatio=0x2c06fc0;\n'
        '}\n')
    summary = {'scope': 'Mapped runtime startup experiment; unsupported imports trap; no engine or gameplay',
               'source_hashes': hashes, 'map_sha256': hashlib.sha256(pack).hexdigest(),
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
