#!/usr/bin/env python3
"""Statically decompile the supplied Amplify ARM64 exports; never load the plugin."""
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
from disco_port.retarget import loader_info
from disco_port.function_starts import function_starts, function_end

ROOT = Path(__file__).resolve().parent.parent

def main():
    source = ROOT / 'reference/Disco.app/Contents/PlugIns/AmplifyTextureNative.bundle/Contents/MacOS/AmplifyTextureNative'
    data = source.read_bytes()
    digest = hashlib.sha256(data).hexdigest()
    if digest != '474612e980951feb0f855bf5e57ae86e89d9492f4b61a43b50f58967bddd297e':
        raise ValueError('Plugin analysis requires the inspected reference revision')
    image, loader = loader_info(data)
    if loader['platform'] != 1:
        raise ValueError('Expected supplied macOS ARM64 plugin')
    starts = function_starts(image)
    listing = subprocess.run(['xcrun', 'nm', '-arch', 'arm64', '-g', str(source)],
                             check=True, capture_output=True, text=True).stdout
    labels = {}
    for line in listing.splitlines():
        match = re.fullmatch(r'([0-9a-fA-F]{16}) T _([a-zA-Z0-9_]{1,159})', line)
        if match:
            address = int(match[1], 16)
            function_end(image, starts, address)
            if address in labels:
                raise ValueError('Ambiguous plugin export')
            labels[address] = 'P_' + match[2]
    if not 1 <= len(labels) <= 256:
        raise ValueError('Unsupported plugin export count')
    output = ROOT / 'artifacts/native-plugin-analysis'
    output.mkdir(exist_ok=True)
    (output / 'Amplify-arm64.macho').write_bytes(image.data)
    (output / 'labels.tsv').write_text(''.join(f'{a:x}\t{n}\n' for a,n in sorted(labels.items())))
    boundaries = ''.join(f'{a:x}\t{function_end(image, starts, a):x}\t{labels.get(a, "Native_" + format(a,"x"))}\n' for a in starts)
    (output / 'functions.tsv').write_text(boundaries)
    (output / 'targets.tsv').write_text(''.join(f'{a:x}\t{function_end(image, starts, a):x}\t{n}\n' for a,n in sorted(labels.items())))
    (output / 'provenance.json').write_text(json.dumps({'source_sha256': digest, 'loader': loader,
        'scope': 'Static plugin pseudocode; no execution or compatibility established'}, indent=2)+'\n')
    home = ROOT / 'artifacts/cache/ghidra-home'
    home.mkdir(parents=True, exist_ok=True)
    environment = dict(os.environ, JAVA_TOOL_OPTIONS='-Duser.home='+str(home))
    projects = output / 'projects'; projects.mkdir(exist_ok=True)
    ghidra = ROOT / 'artifacts/toolchains/ghidra/ghidra_12.1.3_PUBLIC/support/analyzeHeadless'
    subprocess.run([str(ghidra), str(projects), 'Amplify', '-import', str(output / 'Amplify-arm64.macho'),
        '-overwrite', '-noanalysis', '-scriptPath', str(ROOT/'tools/ghidra'), '-postScript',
        'ExportNativeMemory.java', str(output), 'amplify', '-max-cpu', '4'], env=environment, check=True)
    summary = json.loads((output / 'decompilation.json').read_text())
    if summary['failed']: raise ValueError('Selected plugin exports did not decompile')
    if source.read_bytes() != data: raise ValueError('Reference plugin changed')
    print(f'Statically inspected {summary["completed"]} exports; results remain under artifacts/.')

if __name__ == '__main__':
    try: main()
    except (OSError, ValueError, subprocess.CalledProcessError) as error:
        raise SystemExit(f'Plugin analysis failed: {error}')
