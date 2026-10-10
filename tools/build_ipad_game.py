#!/usr/bin/env python3
"""Build the staged game unsigned, with separate asset-mode products."""

from pathlib import Path
import plistlib
import subprocess

ROOT = Path(__file__).resolve().parent.parent


def main():
    project = ROOT / 'artifacts/build/native-engine-ios'
    info = plistlib.loads((project / 'Info.plist').read_bytes())
    persistent = info.get('DiscoPersistentAssets') is True
    derived = ROOT / ('artifacts/build/native-engine-device-persistent' if persistent else 'artifacts/build/native-engine-device')
    subprocess.run(['xcodebuild', '-project', str(project / 'Unity-iPhone.xcodeproj'), '-scheme', 'Unity-iPhone',
                    '-configuration', 'Debug', '-destination', 'generic/platform=iOS', '-derivedDataPath', str(derived),
                    'CODE_SIGNING_ALLOWED=NO', 'SDK_STAT_CACHE_ENABLE=NO', 'build'], check=True)
    app=derived/'Build/Products/Debug-iphoneos/Disco on the Go.app'
    if not app.is_dir():raise ValueError('Branded app product missing')
    if persistent and (derived / 'Build/Products/Debug-iphoneos/Disco on the Go.app/Data').exists():
        raise ValueError('Persistent build unexpectedly includes bundled data')


if __name__ == '__main__':
    try:
        main()
    except (OSError, ValueError, subprocess.CalledProcessError) as error:
        raise SystemExit(f'Engine build failed: {error}')
