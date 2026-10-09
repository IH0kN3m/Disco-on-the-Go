#!/usr/bin/env python3
"""Add the pinned Android module to the local Unity editor without installer scripts."""
import hashlib
from pathlib import Path
import shutil
import subprocess
import urllib.request

ROOT=Path(__file__).resolve().parent.parent
NAME='UnitySetup-Android-Support-for-Editor-2020.3.12f1.pkg'
SIZE=346425350
SHA='b708c3fb91c44ee94d7e5659bd25d3cf27751ef5363af6a0a147272cbd7f9b96'


def main():
    base=ROOT/'artifacts/toolchains'
    editor=Path((base/'unity-editor-path.txt').read_text().strip()).resolve(strict=True)
    # Do not install this downloaded module into an unrelated/global editor.
    if not editor.is_relative_to((ROOT/'artifacts').resolve()):raise ValueError('Android module setup only updates the local artifacts editor')
    downloads=base/'downloads';downloads.mkdir(parents=True,exist_ok=True)
    archive=downloads/NAME
    if not archive.exists():
        partial=archive.with_suffix('.pkg.partial')
        url='https://download.unity3d.com/download_unity/b3b2c6512326/MacEditorTargetInstaller/'+NAME
        with urllib.request.urlopen(url,timeout=60) as response,partial.open('wb') as output:
            total=0
            while block:=response.read(1024*1024):
                total+=len(block)
                if total>SIZE:raise ValueError('Oversized Android package')
                output.write(block)
        verify(partial);partial.replace(archive)
    verify(archive)
    expanded=base/'unity-android-package'
    if not expanded.exists():subprocess.run(['pkgutil','--expand-full',str(archive),str(expanded)],check=True)
    payload=next((expanded/n/'Payload' for n in ('TargetSupport.pkg','TargetSupport.pkg.tmp') if (expanded/n/'Payload/UnityEditor.Android.Extensions.dll').is_file()),None)
    if payload is None:raise ValueError('Unsupported Android module package layout')
    destination=editor.parents[3]/'PlaybackEngines/AndroidPlayer'
    if destination.exists():
        if not (destination/'disco-package.sha256').exists() or (destination/'disco-package.sha256').read_text()!=SHA:
            raise ValueError('An untracked Android module already exists; refusing to overwrite it')
    else:
        shutil.copytree(payload,destination,symlinks=True)
        (destination/'disco-package.sha256').write_text(SHA)
    print('Pinned Unity Android module ready. Full Android Unity export/runtime integration is still separate work.')


def verify(path):
    with path.open('rb') as stream:digest=hashlib.file_digest(stream,'sha256').hexdigest()
    if path.stat().st_size!=SIZE or digest!=SHA:raise ValueError('Android package size/hash differs from pinned input')

if __name__=='__main__':
    try:main()
    except (ValueError,OSError,subprocess.CalledProcessError) as error:raise SystemExit('Unity Android setup failed: '+str(error))
