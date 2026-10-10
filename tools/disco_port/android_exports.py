"""Generate register-preserving ELF tail branches for validated Mach-O exports."""
import re

OVERRIDES = {'il2cpp_init', 'il2cpp_set_data_dir', 'il2cpp_add_internal_call', 'il2cpp_runtime_invoke'}


def export_sources(exports):
    names = sorted(exports)
    if not names or len(names) > 512 or len(set(names)) != len(names):
        raise ValueError('Invalid runtime export count')
    for name in names:
        if not re.fullmatch(r'_[A-Za-z][A-Za-z0-9_]*', name):
            raise ValueError('Unsafe export symbol')
    lines = ['.text', '.p2align 2', '.hidden DiscoExportTargets']
    for index, name in enumerate(names):
        public = name[1:]
        if public in OVERRIDES:
            continue
        lines += [f'.global {public}', f'.type {public}, %function', f'{public}:',
                  'adrp x16, DiscoExportTargets', 'add x16, x16, :lo12:DiscoExportTargets',
                  f'ldr x16, [x16, #{index*8}]', 'br x16', f'.size {public}, .-{public}']
    lines += ['.section .note.GNU-stack,"",%progbits']
    header = '#pragma once\nstatic const char* discoExportNames[]={' + ','.join('"'+n+'"' for n in names) + '};\n'
    return '\n'.join(lines)+'\n', header
