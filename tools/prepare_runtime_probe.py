#!/usr/bin/env python3
"""Prepare a derived ARM64 iOS library and metadata for device-only CPU testing."""

import argparse
import hashlib
import json
from pathlib import Path
import plistlib
import subprocess

from disco_port.metadata import Metadata
from disco_port.retarget import ios_dependency, loader_info

ROOT = Path(__file__).resolve().parent.parent


def prepare(bundle):
    bundle = bundle.resolve()
    source = bundle / 'Contents/Frameworks/GameAssembly.dylib'
    metadata = bundle / 'Contents/Resources/Data/il2cpp_data/Metadata/global-metadata.dat'
    data, meta = source.read_bytes(), metadata.read_bytes()
    Metadata(meta)
    image, original = loader_info(data)
    if original['platform'] != 1:
        raise ValueError('Expected the supplied macOS ARM64 module')
    base = ROOT / 'artifacts/runtime-probe'
    framework = base / 'GameAssembly.framework'
    framework.mkdir(parents=True, exist_ok=True)
    binary = framework / 'GameAssembly'
    binary.write_bytes(image.data)
    subprocess.run(['codesign', '--remove-signature', str(binary)], check=True)
    adjusted = base / 'GameAssembly-ios'
    subprocess.run(['xcrun', 'vtool', '-set-build-version', 'ios', '17.0', '27.0', '-replace', '-output', str(adjusted), str(binary)], check=True)
    adjusted.replace(binary)
    arguments = ['install_name_tool', '-id', '@rpath/GameAssembly.framework/GameAssembly']
    for dependency in original['dependencies']:
        replacement = ios_dependency(dependency)
        if replacement != dependency:
            arguments.extend(['-change', dependency, replacement])
    subprocess.run([*arguments, str(binary)], check=True)
    _, derived = loader_info(binary.read_bytes())
    if derived['platform'] != 2 or derived['executable_sha256'] != original['executable_sha256']:
        raise ValueError('Retargeting changed executable bytes or failed to set iOS platform')
    if derived['dependencies'] != [ios_dependency(d) for d in original['dependencies']]:
        raise ValueError('Derived library dependencies differ from the intended iOS paths')
    binary.chmod(0o755)
    (framework / 'Info.plist').write_bytes(plistlib.dumps({
        'CFBundleExecutable': 'GameAssembly', 'CFBundleIdentifier': 'org.discoport.gameassembly',
        'CFBundleName': 'GameAssembly', 'CFBundlePackageType': 'FMWK', 'CFBundleVersion': '1',
        'CFBundleShortVersionString': '0.1.0', 'CFBundleSupportedPlatforms': ['iPhoneOS'], 'MinimumOSVersion': '17.0'
    }))
    destination = base / 'NativeMetadata/Metadata'
    destination.mkdir(parents=True, exist_ok=True)
    (destination / 'global-metadata.dat').write_bytes(meta)
    # Never execute the source or derived module on the Mac.
    if hashlib.sha256(source.read_bytes()).digest() != hashlib.sha256(data).digest():
        raise ValueError('Reference module changed during preparation')
    report = {'scope': 'Device-only IL2CPP CPU probe; Unity/gameplay integration absent',
              'source_sha256': hashlib.sha256(data).hexdigest(), 'metadata_sha256': hashlib.sha256(meta).hexdigest(),
              'source_loader': original, 'derived_loader': derived, 'derived_sha256': hashlib.sha256(binary.read_bytes()).hexdigest()}
    (base / 'preparation.json').write_text(json.dumps(report, indent=2) + '\n')
    print('Prepared an unsigned iOS ARM64 module; executable section bytes are unchanged. Runtime compatibility remains untested.')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--bundle', type=Path, default=ROOT / 'reference/Disco.app')
    args = parser.parse_args()
    try:
        prepare(args.bundle)
    except (OSError, ValueError, subprocess.CalledProcessError) as error:
        parser.exit(1, f'Runtime preparation failed: {error}\n')


if __name__ == '__main__':
    main()
