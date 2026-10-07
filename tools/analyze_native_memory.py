#!/usr/bin/env python3
"""Static, bounded native decompilation of startup and scene ownership paths."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import sqlite3
import subprocess

from disco_port.binary import MachO
from disco_port.function_starts import function_starts, function_end
from disco_port.native_literals import NativeLiterals

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_TYPES = ['FastLoadManager', 'FortressOccident.SceneTransitionManager',
                 'FortressOccident.ApplicationManager', 'DialogueBundleLoader',
                 'ActorsPortraitsBundleManager', 'InventoryItemsBundleManager',
                 'SceneLoadingManager', 'NavMeshDataCollection']


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--type', action='append', help='Additional exact owning class name')
    parser.add_argument('--address', action='append', default=[], help='Additional exact unslid function start')
    parser.add_argument('--prepare-only', action='store_true')
    parser.add_argument('--output', type=Path, default=ROOT / 'artifacts/native-memory',
                        help='Private analysis directory under artifacts/')
    args = parser.parse_args()
    output = args.output.resolve()
    if not output.is_relative_to((ROOT / 'artifacts').resolve()):
        raise ValueError('Decompiled game material must remain under artifacts/')
    output.mkdir(parents=True, exist_ok=True)
    data = (ROOT / 'reference/Disco.app/Contents/Frameworks/GameAssembly.dylib').read_bytes()
    digest = hashlib.sha256(data).hexdigest()
    if digest != '0550f5a1e9fb9addba0b365908f21bc5a04a2f3979f1b2a640774a05a6c7ab52':
        raise ValueError('Exception helper assumptions require the inspected reference revision')
    image = MachO(data)
    starts = function_starts(image)
    database = ROOT / 'artifacts/inspection/methods.sqlite'
    with sqlite3.connect(database.as_uri() + '?mode=ro', uri=True) as db:
        expected = json.loads(db.execute('SELECT value FROM provenance WHERE key=?', ('gameassembly_sha256',)).fetchone()[0])
        if expected != digest:
            raise ValueError('Method index belongs to a different reference binary')
        rows = db.execute('''SELECT m.id,m.qualified_name,m.image,t.qualified_name,p.qualified_name,l.address
            FROM methods m JOIN locations l ON m.id=l.method_id JOIN types t ON m.type_id=t.id
            LEFT JOIN types p ON p.byval_type_index=t.declaring_type_index
            WHERE l.architecture='arm64' AND l.status='mapped' ORDER BY m.id''').fetchall()
    labels = {}
    selected = {}
    owners = set(DEFAULT_TYPES + (args.type or []))
    for method_id, name, assembly, owner, parent, address in rows:
        image.offset_for_address(address, 4)
        if not image.executable(address):
            raise ValueError('Method label points outside owned executable sections')
        safe = 'M' + str(method_id) + '_' + re.sub('[^a-zA-Z0-9_]', '_', name)[:120]
        labels.setdefault(address, safe)
        if owner in owners or parent in owners:
            selected.setdefault(address, {'name': name, 'owner': owner, 'parent': parent, 'method_id': method_id})
    for raw in args.address:
        address = int(raw, 0)
        selected.setdefault(address, {'name': 'native_helper_' + hex(address), 'method_id': None})
    if not 0 < len(selected) <= 1000:
        raise ValueError('Unsupported target function count')
    lines = []
    for address, record in sorted(selected.items()):
        end = function_end(image, starts, address)
        record.update(address=address, end=end)
        name = labels.get(address, 'Native_' + format(address, 'x'))
        lines.append(f'{address:x}\t{end:x}\t{name}')
    (output / 'targets.tsv').write_text('\n'.join(lines) + '\n')
    (output / 'labels.tsv').write_text(''.join(f'{address:x}\t{name}\n' for address, name in sorted(labels.items())))
    (output / 'functions.tsv').write_text(''.join(
        f'{address:x}\t{function_end(image, starts, address):x}\t{labels.get(address, "Native_" + format(address, "x"))}\n'
        for address in starts))
    (output / 'targets.json').write_text(json.dumps({'source_sha256': digest,
        'scope': 'Static native pseudocode and call references, not recovered source or executable replacements',
        'function_starts': len(starts), 'targets': list(selected.values())}, indent=2) + '\n')
    # This snapshot is read as data by Ghidra, never loaded/executed on the Mac.
    (output / 'GameAssembly-arm64.macho').write_bytes(image.data)
    if args.prepare_only:
        print(f'Prepared {len(selected)} bounded native targets and {len(labels)} method labels.'); return
    ghidra = ROOT / 'artifacts/toolchains/ghidra/ghidra_12.1.3_PUBLIC/support/analyzeHeadless'
    if not ghidra.is_file():
        raise ValueError('Run tools/setup_ghidra.py first')
    home = ROOT / 'artifacts/cache/ghidra-home'
    home.mkdir(parents=True, exist_ok=True)
    projects = output / 'projects'
    projects.mkdir(exist_ok=True)
    environment = dict(os.environ)
    environment['JAVA_TOOL_OPTIONS'] = '-Duser.home=' + str(home)
    command = [str(ghidra), str(projects), 'NativeMemory', '-import', str(output / 'GameAssembly-arm64.macho'),
               '-overwrite', '-noanalysis', '-scriptPath', str(ROOT / 'tools/ghidra'),
               '-postScript', 'ExportNativeMemory.java', str(output), 'gameassembly', '-max-cpu', '4',
               '-log', str(output / 'analysis.log'), '-scriptlog', str(output / 'script.log')]
    subprocess.run(command, cwd=ROOT, env=environment, check=True)
    summary = json.loads((output / 'decompilation.json').read_text())
    if summary['failed']:
        raise ValueError('Some selected functions did not decompile; inspect private diagnostics')
    literals = NativeLiterals((ROOT / 'reference/Disco.app/Contents/Resources/Data/il2cpp_data/Metadata/global-metadata.dat').read_bytes())
    references = {}
    for path in sorted((output / 'decompiled').glob('*.c')):
        # Resolve only references exported by this selected decompilation pass.
        if int(path.stem, 16) not in selected:
            continue
        for raw in re.findall(r'Ram([0-9a-f]{16})', path.read_text()):
            address = int(raw, 16)
            if any(s.address + s.file_size <= address and address + 8 <= s.address + s.virtual_size
                   for s in image.segments):
                continue  # Zero-filled runtime state contains no encoded file usage.
            encoded, = image.pointers(address, 1)
            if encoded < 2**32 and encoded >> 29 == 5 and encoded & 1:
                references[hex(address)] = literals.resolve(encoded)
    (output / 'literal-references.json').write_text(json.dumps(references, ensure_ascii=False, indent=2) + '\n')
    print(f"Static decompilation complete: {summary['completed']} native functions. Results remain ignored.")


if __name__ == '__main__':
    try:
        main()
    except (OSError, ValueError, sqlite3.Error, subprocess.CalledProcessError) as error:
        raise SystemExit(f'Native analysis failed: {error}')
