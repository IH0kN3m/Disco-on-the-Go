#!/usr/bin/env python3
"""Optional Xcode build phase: embed only the prepared local CPU probe inputs."""

import os
import hashlib
import json
from pathlib import Path
import shutil
import subprocess

ROOT = Path(__file__).resolve().parent.parent


def main():
    if os.environ.get('DISCO_RUNTIME_PROBE') != 'YES':
        return
    if not os.environ.get('SDK_NAME', '').startswith('iphoneos'):
        raise ValueError('The native module probe supports physical iOS builds only')
    source = Path(os.environ['DISCO_RUNTIME_PROBE_ROOT']).resolve()
    if not source.is_relative_to(ROOT / 'artifacts') or not (source / 'preparation.json').exists():
        raise ValueError('Use prepared inputs under ignored artifacts/')
    report = json.loads((source / 'preparation.json').read_text())
    for path, expected in ((source / 'GameAssembly.framework/GameAssembly', report['derived_sha256']),
                           (source / 'NativeMetadata/Metadata/global-metadata.dat', report['metadata_sha256'])):
        with path.open('rb') as stream:
            digest = hashlib.sha256()
            for chunk in iter(lambda: stream.read(1024 * 1024), b''):
                digest.update(chunk)
            if digest.hexdigest() != expected:
                raise ValueError('Prepared native module or metadata changed; prepare the probe again')
    app = Path(os.environ['TARGET_BUILD_DIR']) / os.environ['WRAPPER_NAME']
    frameworks = app / 'Frameworks'
    frameworks.mkdir(parents=True, exist_ok=True)
    destination = frameworks / 'GameAssembly.framework'
    if destination.exists():
        shutil.rmtree(destination)
    shutil.copytree(source / 'GameAssembly.framework', destination)
    metadata = app / 'NativeMetadata'
    if metadata.exists():
        shutil.rmtree(metadata)
    shutil.copytree(source / 'NativeMetadata', metadata)
    if os.environ.get('CODE_SIGNING_ALLOWED') == 'YES':
        identity = os.environ.get('EXPANDED_CODE_SIGN_IDENTITY')
        if not identity:
            raise ValueError('Xcode did not provide a development signing identity')
        subprocess.run(['codesign', '--force', '--sign', identity, '--timestamp=none', str(destination)], check=True)


if __name__ == '__main__':
    main()
