#!/usr/bin/env python3
"""Trace bounded direct initializer dependencies without executing source binaries."""
import json
from pathlib import Path
from disco_port.binary import MachO
from disco_port.build_inputs import validate_sources
from disco_port.dyld_plan import load_plan
from disco_port.function_starts import function_starts
from disco_port.arm64_calls import initializer_calls

ROOT = Path(__file__).resolve().parent.parent

if __name__ == '__main__':
    hashes = validate_sources(ROOT/'reference/Disco.app')
    image = MachO((ROOT/'reference/Disco.app/Contents/Frameworks/GameAssembly.dylib').read_bytes())
    plan = load_plan(image); starts = function_starts(image)
    records = [initializer_calls(image, starts, plan['bindings'], root) for root in plan['initializers']]
    output = ROOT/'artifacts/android/runtime/initializer-dependencies.json'; output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps({'source_hashes': hashes, 'initializers': records}, indent=2)+'\n')
    boot=initializer_calls(image, starts, plan['bindings'], plan['exports']['_il2cpp_init'])
    (output.parent/'boot-dependencies.json').write_text(json.dumps(boot,indent=2)+'\n')
    print(f"Runtime boot: {boot['function_count']} direct-reachable functions, {len(boot['imports'])} imports, "
          f"{len(boot['indirect_calls_or_jumps'])} unresolved indirect sites")
    for n, r in enumerate(records):
        print(f"Initializer {n}: {r['function_count']} direct-reachable functions, {len(r['imports'])} imports, "
              f"{len(r['indirect_calls_or_jumps'])} unresolved indirect sites, {len(r['unresolved_direct_edges'])} unresolved direct edges")
