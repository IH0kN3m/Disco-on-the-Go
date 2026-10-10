#!/usr/bin/env python3
"""Retag derived startup UnityFS containers while verifying unchanged object bodies."""

import argparse
import hashlib
import json
from pathlib import Path

import UnityPy
from UnityPy.enums import BuildTarget
from disco_port.bundle_validation import bundle_bodies

ROOT = Path(__file__).resolve().parent.parent


def main(addressables=False):
    if UnityPy.__version__ != '1.25.4':
        raise ValueError('Expected UnityPy 1.25.4; run make setup')
    root = ROOT / ('artifacts/build/native-engine-ios/Data/Raw/aa/StandaloneOSX' if addressables else 'artifacts/build/native-engine-ios/Data/Raw/AssetBundles/iOS')
    report = []
    for path in sorted(root.rglob('*')):
        if not path.is_file():
            continue
        with path.open('rb') as stream:
            signature = stream.read(8)
        if signature != b'UnityFS\0':
            continue
        if not path.resolve().is_relative_to(root.resolve()) or path.stat().st_size > 256 * 1024 * 1024:
            raise ValueError('Bundle path or size exceeds supported scope')
        original = path.read_bytes()
        environment = UnityPy.load(original)
        if len(environment.files) != 1:
            raise ValueError('Expected one UnityFS container')
        bundle = next(iter(environment.files.values()))
        before = bundle_bodies(bundle, 2)
        count = 0
        for child in bundle.files.values():
            if not hasattr(child, 'objects'):
                continue
            if child.header.version != 22 or child.unity_version != '2020.3.12f1' or child._m_target_platform != 2:
                raise ValueError('Unsupported startup serialized child')
            child._m_target_platform = 9
            child.target_platform = BuildTarget.iOS
            child.mark_changed()
            count += 1
        if not count:
            raise ValueError('Startup bundle has no serialized child')
        derived = bundle.save(packer='lz4')
        check = next(iter(UnityPy.load(derived).files.values()))
        if bundle_bodies(check, 9) != before:
            raise ValueError('Retagging changed object/resource bytes or failed to select iOS')
        path.write_bytes(derived)
        report.append({'path': str(path.relative_to(root)), 'serialized_children': count,
                       'source_sha256': hashlib.sha256(original).hexdigest(), 'derived_sha256': hashlib.sha256(derived).hexdigest()})
    if not report:
        raise ValueError('No supported startup bundles')
    report_path = ROOT / 'artifacts/build/native-engine-ios' / ('addressable-bundle-retag.json' if addressables else 'startup-bundle-retag.json')
    report_path.write_text(json.dumps(report, indent=2) + '\n')
    kind = 'addressable' if addressables else 'startup'
    print(f'Retagged {len(report)} derived {kind} containers; all object and resource bytes are unchanged.')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--addressables', action='store_true', help='Retag the supplied addressable containers instead of startup bundles')
    args = parser.parse_args()
    try:
        main(args.addressables)
    except (OSError, ValueError, KeyError) as error:
        raise SystemExit(f'Startup bundle retagging failed: {error}')
