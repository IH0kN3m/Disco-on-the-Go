#!/usr/bin/env python3
"""Compare supplied Windows/Mac metadata labels and bounded root shader payloads."""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import UnityPy
from disco_port.metadata import Metadata
from disco_port.shader_inventory import platform_fingerprints

ROOT = Path(__file__).resolve().parent.parent
CONTAINERS = ('globalgamemanagers.assets', 'resources.assets', 'sharedassets0.assets', 'Resources/unity_builtin_extra')


def inspect(root):
    raw = (root / 'il2cpp_data/Metadata/global-metadata.dat').read_bytes()
    metadata = Metadata(raw)
    report = {k: len(getattr(metadata, k)) for k in ('images', 'types', 'methods', 'fields')}
    report['metadata_sha256'] = hashlib.sha256(raw).hexdigest()
    report['image_type_counts'] = {i['name']: i['type_count'] for i in metadata.images}
    report['shaders'] = []
    for name in CONTAINERS:
        path = root / name
        if path.stat().st_size > 512 * 1024**2:
            raise ValueError('Serialized container exceeds inspection bound')
        env = UnityPy.load(path.read_bytes())
        for file in env.files.values():
            if getattr(file, 'unity_version', None) != '2020.3.12f1':
                raise ValueError('Expected serialized Unity 2020.3.12f1 inputs')
        for obj in env.objects:
            if obj.type.name != 'Shader':
                continue
            data = obj.read()
            report['shaders'].append({'container': name, 'name': data.m_ParsedForm.m_Name,
                                     'platform_blobs': platform_fingerprints(data.platforms, data.offsets,
                                                                            data.compressedLengths, bytes(data.compressedBlob))})
    return metadata, report


def main(windows):
    if UnityPy.__version__ != '1.25.4':
        raise ValueError('Expected UnityPy 1.25.4')
    mac, mr = inspect(ROOT / 'reference/Disco.app/Contents/Resources/Data')
    win, wr = inspect(windows)
    labels = lambda m: Counter((v['image'], v['qualified_name'], v['parameter_count']) for v in m.methods)
    ml, wl = labels(mac), labels(win)
    shaders = lambda r: {(v['container'], v['name']): v['platform_blobs'] for v in r['shaders']}
    ms, ws = shaders(mr), shaders(wr)
    if len(ms) != len(mr['shaders']) or len(ws) != len(wr['shaders']):
        raise ValueError('Ambiguous duplicate shader names within a container')
    shared = ms.keys() & ws.keys()
    summary = {'shared_method_labels': sum((ml & wl).values()), 'mac_only_labels': sum((ml - wl).values()),
               'windows_only_labels': sum((wl - ml).values()), 'shared_shader_names': len(shared),
               'identical_glcore_payloads': sum(15 in ms[k] and ms[k][15] == ws[k].get(15) for k in shared)}
    report = {'scope': 'Metadata names/parameter counts and four root shader containers only; no executable equivalence',
              'mac': mr, 'windows': wr, 'summary': summary,
              'mac_only_labels': list((ml - wl).elements()), 'windows_only_labels': list((wl - ml).elements())}
    output = ROOT / 'artifacts/android/windows-comparison.json'
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps(summary, indent=2))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--data', type=Path, default=ROOT / 'artifacts/android/windows-extracted/Disco Elysium_Data')
    args = parser.parse_args()
    try:
        main(args.data)
    except (ValueError, OSError) as error:
        parser.exit(1, f'Windows comparison failed: {error}\n')
