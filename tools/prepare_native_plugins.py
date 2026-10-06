#!/usr/bin/env python3
"""Derive the supplied ARM64 Steam library for an iOS compatibility experiment."""

import hashlib
import json
from pathlib import Path
import plistlib
import subprocess

from disco_port.retarget import ios_dependency, loader_info

ROOT = Path(__file__).resolve().parent.parent


def main():
    source = ROOT / 'reference/Disco.app/Contents/PlugIns/steam_api.bundle/Contents/MacOS/libsteam_api.dylib'
    original = source.read_bytes()
    image, before = loader_info(original)
    if before['platform'] != 1:
        raise ValueError('Expected the supplied macOS ARM64 Steam library')
    framework = ROOT / 'artifacts/native-plugins/SteamAPI.framework'
    framework.mkdir(parents=True, exist_ok=True)
    binary = framework / 'SteamAPI'
    binary.write_bytes(image.data)
    subprocess.run(['codesign', '--remove-signature', str(binary)], check=True)
    temporary = framework.parent / 'SteamAPI-ios'
    subprocess.run(['xcrun', 'vtool', '-set-build-version', 'ios', '17.0', '27.0', '-replace', '-output', str(temporary), str(binary)], check=True)
    temporary.replace(binary)
    arguments = ['install_name_tool', '-id', '@rpath/SteamAPI.framework/SteamAPI']
    for dependency in before['dependencies']:
        mapped = ios_dependency(dependency)
        if mapped != dependency:
            arguments.extend(['-change', dependency, mapped])
    subprocess.run([*arguments, str(binary)], check=True)
    _, after = loader_info(binary.read_bytes())
    if after['platform'] != 2 or before['executable_sha256'] != after['executable_sha256']:
        raise ValueError('Steam derivation changed code or failed to select iOS')
    if after['dependencies'] != [ios_dependency(name) for name in before['dependencies']]:
        raise ValueError('Steam derivation changed dependencies unexpectedly')
    binary.chmod(0o755)
    (framework / 'Info.plist').write_bytes(plistlib.dumps({
        'CFBundleExecutable': 'SteamAPI', 'CFBundleIdentifier': 'org.discoport.steamapi', 'CFBundleName': 'SteamAPI',
        'CFBundlePackageType': 'FMWK', 'CFBundleVersion': '1', 'CFBundleShortVersionString': '0.1.0',
        'CFBundleSupportedPlatforms': ['iPhoneOS'], 'MinimumOSVersion': '17.0'
    }))
    report = {'scope': 'Original Steam CPU library; no Steam client/service compatibility established',
              'source_sha256': hashlib.sha256(original).hexdigest(), 'derived_sha256': hashlib.sha256(binary.read_bytes()).hexdigest(),
              'source_loader': before, 'derived_loader': after}
    (framework.parent / 'preparation.json').write_text(json.dumps(report, indent=2) + '\n')
    if source.read_bytes() != original:
        raise ValueError('Reference Steam library changed')
    print('Prepared the derived Steam framework; executable bytes unchanged, runtime compatibility untested.')


if __name__ == '__main__':
    try:
        main()
    except (OSError, ValueError, subprocess.CalledProcessError) as error:
        raise SystemExit(f'Plugin preparation failed: {error}')
