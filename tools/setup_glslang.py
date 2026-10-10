#!/usr/bin/env python3
"""Stage the checksum-pinned official macOS GLSL validator under artifacts."""
import hashlib
from pathlib import Path, PurePosixPath
import subprocess
import tarfile
import urllib.request

ROOT=Path(__file__).resolve().parent.parent
VERSION='16.6.0'
SHA256='4f8c05f2888a73ed0b7b274bc524af9130e09ae94b43c0f3f9ed83cfae852834'
URL=f'https://github.com/KhronosGroup/glslang/releases/download/{VERSION}/glslang-{VERSION}-macos-universal-release.tar.gz'


def main():
    output=ROOT/f'artifacts/toolchains/glslang-{VERSION}';output.mkdir(parents=True,exist_ok=True)
    package=output/'release.tar.gz'
    if not package.exists():
        temporary=package.with_suffix('.download')
        with urllib.request.urlopen(URL,timeout=60) as source,temporary.open('wb') as target:
            total=0
            while block:=source.read(1024**2):
                total+=len(block)
                if total>32*1024**2:raise ValueError('Validator archive exceeds supported size')
                target.write(block)
        temporary.replace(package)
    if hashlib.sha256(package.read_bytes()).hexdigest()!=SHA256:raise ValueError('Validator archive checksum mismatch')
    with tarfile.open(package) as archive:
        entries=[e for e in archive.getmembers() if e.isfile() and PurePosixPath(e.name).name=='glslang']
        if len(entries)!=1 or not 0<entries[0].size<=64*1024**2:raise ValueError('Unsupported validator package layout')
        binary=output/'bin/glslang';binary.parent.mkdir(exist_ok=True)
        binary.write_bytes(archive.extractfile(entries[0]).read());binary.chmod(0o755)
    result=subprocess.run([str(binary),'--version'],capture_output=True,text=True,check=True)
    if 'Glslang Version: 11:'+VERSION not in result.stdout:raise ValueError('Unexpected validator version')
    print('Official GLSL validator ready under artifacts; release checksum verified.')


if __name__=='__main__':main()
