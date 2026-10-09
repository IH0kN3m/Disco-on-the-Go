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
    # Reviewed diagnostic entry points only. Full initialization is explicitly disabled.
    if plan['initializers'][0] != 0x253c:
        raise ValueError('Pinned clock initializer changed')
    (output / 'RuntimePins.h').write_text(
        '#pragma once\nnamespace RuntimePins {\n'
        f'constexpr unsigned long long Dot={DOT_ADDRESS};\n'
        'constexpr unsigned long long ClockInit=0x253c, ClockData=0x2bf0e98, ClockRatio=0x2c06fc0;\n'
        '}\n')
    summary = {'scope': 'Mapped image diagnostic; unresolved ABI imports prohibit full runtime initialization',
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
