#!/usr/bin/env python3
"""Install hash-pinned Unity 2020 Android export tools under artifacts/."""
import hashlib
import os
from pathlib import Path
import shutil
import stat
import tarfile
import urllib.request
import zipfile

ROOT=Path(__file__).resolve().parent.parent
GOOGLE='https://dl.google.com/android/repository/'
PACKAGES=[
 ('sdk-tools-darwin-4333796.zip',GOOGLE,103022432,'ecb29358bc0f13d7c2fa0f9290135a5b608e38434aad9bf7067d0252c160853e','sdk/tools'),
 ('android-ndk-r19-darwin-x86_64.zip',GOOGLE,807592927,'04159ade2fc5c7d055248cf65664039b8596f4b9ee3fbc44a9bf2ce2ee28d95d','android-ndk-r19'),
 ('platform-30_r03.zip',GOOGLE,52328361,'f3f5b75744dbf6ee6ed3e8174a71e513bfee502d0bc3463ea97e517bff68d84e','sdk/platforms/android-30'),
 ('5a6ceea22103d8dec989aefcef309949c0c42f1d.build-tools_r30.0.2-macosx.zip',GOOGLE,51227855,'be65592c9219757468065fe5945ac5500fbd84fcc069d7b13b077c0d663642ef','sdk/build-tools/30.0.2'),
 ('zulu8.96.0.205-ca-jdk8.0.504-macosx_aarch64.tar.gz','https://cdn.azul.com/zulu/bin/',103714410,'58bb3c08f2aa63d9743cf31899fa4b8c6c9effefce9479e7288c26621c3bb21b','jdk8'),
]


def verify(path,size,digest):
    if path.stat().st_size!=size or hashlib.file_digest(path.open('rb'),'sha256').hexdigest()!=digest:raise ValueError('Package fingerprint mismatch: '+path.name)


def setup():
    base=ROOT/'artifacts/toolchains';downloads=base/'downloads';downloads.mkdir(parents=True,exist_ok=True)
    legacy=base/'android-legacy';legacy.mkdir(exist_ok=True)
    modern=Path(os.environ.get('ANDROID_HOME',Path.home()/'Library/Android/sdk'))
    if not (modern/'platform-tools/adb').is_file():raise ValueError('Install Android SDK platform-tools first')
    for name,url,size,digest,destination in PACKAGES:
        archive=downloads/name
        if not archive.is_file():
            partial=archive.with_suffix(archive.suffix+'.partial')
            with urllib.request.urlopen(url+name,timeout=60) as response,partial.open('wb') as output:
                total=0
                while block:=response.read(1024**2):
                    total+=len(block)
                    if total>size:raise ValueError('Package exceeds pinned size')
                    output.write(block)
            verify(partial,size,digest);partial.replace(archive)
        verify(archive,size,digest)
        target=legacy/destination
        if target.exists():continue
        temporary=legacy/(name+'.extract')
        if temporary.exists():raise ValueError('Incomplete extraction exists: '+temporary.name)
        temporary.mkdir()
        if name.endswith('.zip'):
            with zipfile.ZipFile(archive) as z:
                for entry in z.infolist():
                    path=temporary/entry.filename
                    if not path.resolve().is_relative_to(temporary.resolve()) or stat.S_ISLNK(entry.external_attr>>16):raise ValueError('Unsafe ZIP path or link')
                    z.extract(entry,temporary)
                    if path.is_file() and entry.external_attr>>16:path.chmod((entry.external_attr>>16)&0o777)
        else:
            with tarfile.open(archive) as tar:tar.extractall(temporary,filter='data')
        tops=list(temporary.iterdir())
        if len(tops)!=1 or not tops[0].is_dir():raise ValueError('Unexpected tool archive layout')
        target.parent.mkdir(parents=True,exist_ok=True);tops[0].rename(target);temporary.rmdir()
    sdk=legacy/'sdk'
    for name in ('platform-tools','licenses'):
        source=modern/name;target=sdk/name
        if target.exists():continue
        if not source.is_dir():raise ValueError('Legacy export needs platform-tools and accepted SDK licenses in ANDROID_HOME')
        shutil.copytree(source,target,symlinks=True)
    if 'Pkg.Revision=26.1.1' not in (sdk/'tools/source.properties').read_text():raise ValueError('Unity 2020 export requires SDK tools 26.1.1')
    java=legacy/'jdk8/Contents/Home'
    if not (java/'bin/javac').is_file():raise ValueError('Extracted JDK layout differs')
    (base/'jdk8-path.txt').write_text(str(java)+'\n')
    print('Pinned Unity Android export tools are ready under artifacts/toolchains/android-legacy.')

if __name__=='__main__':setup()
