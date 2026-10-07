#!/usr/bin/env python3
"""Derive the original ARM64 Amplify CPU codecs with an explicit desktop-GPU guard."""
import hashlib
import json
from pathlib import Path
import plistlib
import shutil
import subprocess
from disco_port.retarget import loader_info
from disco_port.plugin_project import embed_framework

ROOT = Path(__file__).resolve().parent.parent
OUTPUT = ROOT / 'artifacts/native-plugins'
OPENGL = '/System/Library/Frameworks/OpenGL.framework/Versions/A/OpenGL'
GUARD = '@rpath/DiscoOpenGLGuard.framework/DiscoOpenGLGuard'


def stage(project, destination):
    report = json.loads((OUTPUT/'amplify-preparation.json').read_text())
    frameworks = [('AmplifyTextureNative','derived_sha256','05','06'),
                  ('DiscoOpenGLGuard','guard_sha256','07','08')]
    for name,key,file_suffix,build_suffix in frameworks:
        source = OUTPUT/(name+'.framework')
        if hashlib.sha256((source/name).read_bytes()).hexdigest() != report[key]:
            raise ValueError('Prepared Amplify framework changed')
    for name,key,file_suffix,build_suffix in frameworks:
        embed_framework(project,name,'D15C000000000000000000'+file_suffix,'D15C000000000000000000'+build_suffix)
        shutil.copytree(OUTPUT/(name+'.framework'),destination/'Frameworks'/(name+'.framework'),dirs_exist_ok=True)


def framework_info(name):
    return {'CFBundleExecutable': name, 'CFBundleIdentifier': 'org.discoport.'+name.lower(),
        'CFBundleName': name, 'CFBundlePackageType': 'FMWK', 'CFBundleVersion': '1',
        'CFBundleShortVersionString': '0.1.0', 'CFBundleSupportedPlatforms': ['iPhoneOS'],
        'MinimumOSVersion': '17.0'}


def main():
    source = ROOT / 'reference/Disco.app/Contents/PlugIns/AmplifyTextureNative.bundle/Contents/MacOS/AmplifyTextureNative'
    data = source.read_bytes()
    if hashlib.sha256(data).hexdigest() != '474612e980951feb0f855bf5e57ae86e89d9492f4b61a43b50f58967bddd297e':
        raise ValueError('Amplify derivation requires the inspected reference revision')
    image, before = loader_info(data)
    if before['platform'] != 1 or before['dependencies'] != [OPENGL, '/usr/lib/libc++.1.dylib', '/usr/lib/libSystem.B.dylib']:
        raise ValueError('Unsupported Amplify loader dependencies')
    guard = OUTPUT / 'DiscoOpenGLGuard.framework'; guard.mkdir(parents=True, exist_ok=True)
    sdk = subprocess.run(['xcrun','--sdk','iphoneos','--show-sdk-path'], check=True, capture_output=True, text=True).stdout.strip()
    subprocess.run(['xcrun','clang++','-target','arm64-apple-ios17.0','-isysroot',sdk,'-std=c++17',
        '-dynamiclib','-install_name',GUARD,str(ROOT/'runtime/UnityHost/iOS/DiscoOpenGLGuard.cpp'),
        '-o',str(guard/'DiscoOpenGLGuard')],check=True)
    (guard/'Info.plist').write_bytes(plistlib.dumps(framework_info('DiscoOpenGLGuard')))
    destination = OUTPUT / 'AmplifyTextureNative.framework'; destination.mkdir(parents=True, exist_ok=True)
    binary = destination / 'AmplifyTextureNative'; binary.write_bytes(image.data)
    subprocess.run(['codesign','--remove-signature',str(binary)],check=True)
    temporary = OUTPUT / 'Amplify-ios'
    subprocess.run(['xcrun','vtool','-set-build-version','ios','17.0','27.0','-replace','-output',str(temporary),str(binary)],check=True)
    temporary.replace(binary)
    subprocess.run(['install_name_tool','-id','@rpath/AmplifyTextureNative.framework/AmplifyTextureNative',
        '-change',OPENGL,GUARD,str(binary)],check=True)
    _,after = loader_info(binary.read_bytes())
    if after['platform'] != 2 or before['executable_sha256'] != after['executable_sha256'] or after['dependencies'] != [GUARD,*before['dependencies'][1:]]:
        raise ValueError('Amplify derivation changed code or unexpected loader fields')
    binary.chmod(0o755)
    (destination/'Info.plist').write_bytes(plistlib.dumps(framework_info('AmplifyTextureNative')))
    report = {'scope':'Original CPU codecs/histogram; desktop GPU imports explicitly abort; device compatibility unverified',
        'source_sha256':hashlib.sha256(data).hexdigest(),'derived_sha256':hashlib.sha256(binary.read_bytes()).hexdigest(),
        'guard_sha256':hashlib.sha256((guard/'DiscoOpenGLGuard').read_bytes()).hexdigest(),
        'source_loader':before,'derived_loader':after}
    (OUTPUT/'amplify-preparation.json').write_text(json.dumps(report,indent=2)+'\n')
    if source.read_bytes()!=data: raise ValueError('Reference plugin changed')
    print('Prepared derived Amplify CPU plugin and explicit GPU guard; device compatibility unverified.')

if __name__=='__main__':
    try: main()
    except (OSError,ValueError,subprocess.CalledProcessError) as error:
        raise SystemExit(f'Amplify preparation failed: {error}')
