#!/usr/bin/env python3
"""Inventory static Texture2D residency flags and BC expansion without decoding images."""

import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path, PurePosixPath

import UnityPy
from UnityPy.enums import TextureFormat
from disco_port.binary import FormatError
from disco_port.texture_memory import estimate_bc

ROOT = Path(__file__).resolve().parent.parent


def main(bundle, include_bundles):
    if UnityPy.__version__ != '1.25.4':
        raise FormatError('Expected UnityPy 1.25.4; run make setup-scenes')
    root = (bundle / 'Contents/Resources/Data').resolve()
    paths = sorted(p for p in root.iterdir() if p.is_file() and
                   (p.suffix == '.assets' or p.name == 'globalgamemanagers' or p.name.startswith('level') and p.name[5:].isdigit()))
    if include_bundles:
        paths += sorted(p for p in (root / 'StreamingAssets').rglob('*') if p.is_file())
    records, inspected, placeholders = [], 0, 0
    trees, tree_instances, tree_nodes = {}, 0, 0
    metadata_bytes = 0
    for path in paths:
        if path.is_symlink() or not path.resolve().is_relative_to(root):
            raise FormatError('Texture input escapes reference data ownership')
        with path.open('rb') as stream:
            signature = stream.read(8)
        is_bundle = signature == b'UnityFS\0'
        if path.parent != root and not is_bundle:
            continue
        if path.stat().st_size > 256 * 1024**2:
            raise FormatError('Texture container exceeds bounded inspection size')
        environment = UnityPy.load(path.read_bytes())
        for file in environment.files.values():
            if is_bundle:
                if file.version != 7 or not 0 < len(file.files) <= 65536:
                    raise FormatError('Unsupported UnityFS container layout/count')
                for name in file.files:
                    owned = PurePosixPath(name)
                    if not name or owned.is_absolute() or '..' in owned.parts or '\\' in name:
                        raise FormatError('Bundle child escapes container ownership')
            children = file.files.values() if is_bundle else [file]
            for child in children:
                if not hasattr(child, 'objects'):
                    continue
                if child.header.version != 22 or child.unity_version != '2020.3.12f1':
                    raise FormatError('Unsupported texture serialized layout/version')
                if len(child.objects) > 1000000:
                    raise FormatError('Serialized object count exceeds supported scope')
                inspected += 1
                metadata_bytes += child.header.metadata_size
                for serialized_type in child.types:
                    if serialized_type.node is not None:
                        nodes = [(n.m_Type, n.m_Name, n.m_Level, n.m_ByteSize, n.m_MetaFlag,
                                  n.m_Version, n.m_TypeFlags, n.m_RefTypeHash)
                                 for n in serialized_type.node.traverse()]
                        if len(nodes) > 1000000:
                            raise FormatError('Type tree node count exceeds supported scope')
                        key = hashlib.sha256(json.dumps(nodes, sort_keys=True, separators=(',', ':')).encode()).hexdigest()
                        trees[key] = len(nodes)
                        tree_instances += 1
                        tree_nodes += len(nodes)
                for obj in child.objects.values():
                    if obj.type.name != 'Texture2D':
                        continue
                    texture = obj.read()
                    if texture.m_Width == texture.m_Height == texture.m_ImageCount == texture.m_CompleteImageSize == 0 and not texture.image_data and not texture.m_StreamData.size:
                        placeholders += 1
                        continue
                    if texture.m_TextureDimension != 2 or texture.m_ImageCount != 1 or texture.m_MipsStripped != 0:
                        raise FormatError(f'Unsupported Texture2D layout in {path.name}:{obj.path_id}: dimension={texture.m_TextureDimension}, count={texture.m_ImageCount}, stripped={texture.m_MipsStripped}')
                    name = TextureFormat(texture.m_TextureFormat).name
                    estimate = estimate_bc(name, texture.m_Width, texture.m_Height, texture.m_MipCount)
                    record = {'source': path.relative_to(root).as_posix(), 'child': child.name,
                              'path_id': obj.path_id, 'name': texture.m_Name, 'format': name,
                              'width': texture.m_Width, 'height': texture.m_Height, 'mips': texture.m_MipCount,
                              'readable': texture.m_IsReadable, 'mip_streaming': texture.m_StreamingMipmaps,
                              'external_resource': bool(texture.m_StreamData.path),
                              'stored_bytes': texture.m_StreamData.size or len(texture.image_data)}
                    if estimate:
                        record.update({k: estimate[k] for k in ('bc_bytes', 'fallback_bytes')})
                    records.append(record)
        del environment
    bc = [r for r in records if 'bc_bytes' in r]
    summary = {'serialized_files': inspected, 'texture2d_objects': len(records), 'empty_placeholders': placeholders,
               'formats': dict(Counter(r['format'] for r in records)),
               'mip_streaming_objects': sum(bool(r['mip_streaming']) for r in records),
               'external_resource_objects': sum(r['external_resource'] for r in records),
               'readable_objects': sum(bool(r['readable']) for r in records),
               'bc_objects': len(bc), 'bc_full_chain_bytes': sum(r['bc_bytes'] for r in bc),
               'fallback_full_chain_bytes': sum(r['fallback_bytes'] for r in bc)}
    summary.update(serialized_metadata_bytes=metadata_bytes, type_tree_instances=tree_instances,
                   type_tree_nodes=tree_nodes, distinct_tree_structures=len(trees), distinct_tree_nodes=sum(trees.values()))
    output = ROOT / 'artifacts/inspection' / ('texture-memory-all.json' if include_bundles else 'texture-memory-root.json')
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps({'scope': 'All serialized Texture2D objects in selected containers; not runtime residency. No payload decoding, deduplication, virtual-texture or cubemap accounting.',
                                  'summary': summary, 'textures': records}, indent=2) + '\n')
    print(json.dumps(summary, indent=2))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--bundle', type=Path, default=ROOT / 'reference/Disco.app')
    parser.add_argument('--bundles', action='store_true')
    arguments = parser.parse_args()
    try:
        main(arguments.bundle, arguments.bundles)
    except (OSError, ValueError, KeyError) as error:
        raise SystemExit(f'Texture inventory failed: {error}')
