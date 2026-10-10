#!/usr/bin/env python3
"""Package Unity Android with the local ARM64 provider; all derived files stay private."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import zipfile
from stage_android_runtime import stage
from disco_port.android_engine import adapt_desktop_audio
from disco_port.android_icalls import stage_icall_bridges
from disco_port.android_build import signing_key, validate_payload

ROOT = Path(__file__).resolve().parent.parent


def build(provider_only=False, game_data=False, obb=False):
    if obb and not game_data:raise ValueError("OBB mode requires game data")
    payload_hash=validate_payload(ROOT/'artifacts/android/game-data') if game_data else None
    sdk=Path(os.environ.get('ANDROID_HOME',Path.home()/'Library/Android/sdk'))
    java=Path(subprocess.check_output(['/usr/libexec/java_home','-v','17'],text=True).strip())
    tools=sdk/'build-tools/36.0.0'; platform=sdk/'platforms/android-36/android.jar'
    compiler=sdk/'ndk/27.2.12479018/toolchains/llvm/prebuilt/darwin-x86_64/bin/aarch64-linux-android28-clang++'
    editor=Path((ROOT/'artifacts/toolchains/unity-editor-path.txt').read_text().strip())
    player=editor.parents[3]/'PlaybackEngines/AndroidPlayer'
    output=ROOT/'artifacts/android/build-game';output.mkdir(parents=True,exist_ok=True)
    log=output/'build.log';log.write_text('Local Unity Android provider build\n')
    env=os.environ.copy();env['JAVA_HOME']=str(java)
    def run(command):
        with log.open('a') as stream:
            result=subprocess.run([str(c) for c in command],cwd=output,env=env,stdout=stream,stderr=subprocess.STDOUT)
        if result.returncode:raise ValueError('Build failed; inspect artifacts/android/build-game/build.log')
    runtime,staged=stage()
    stage_icall_bridges(player/'Variations/il2cpp/Development/Libs/arm64-v8a/libunity.so',compiler.parent/'llvm-nm',runtime)
    sources=['RuntimeLoader.cpp','DarwinUnwind.cpp','DarwinBridge.cpp','DarwinVarargs.cpp','DarwinThreads.cpp','DarwinABI.S','DarwinIcalls.S','UnityProvider.cpp']
    run([compiler,'-std=c++17','-O2','-g','-fPIC','-shared','-static-libstdc++','-Wl,--exclude-libs,ALL',
         '-Wl,-z,max-page-size=16384','-Wl,-z,common-page-size=16384','-Wl,--no-undefined','-Wl,-z,noexecstack',
         '-Wl,-soname,libil2cpp.so','-DDISCO_MAPPED_RUNTIME=1','-I',runtime,'-I',ROOT/'runtime/UnityHost','-I',editor.parents[1]/'il2cpp/libil2cpp',
         *[ROOT/'runtime/AndroidHost'/s for s in sources],runtime/'MissingImports.S',runtime/'RuntimeExports.S',runtime/'GeneratedIcalls.S',
         '-landroid','-llog','-lGLESv3','-o',output/'libil2cpp.so'])
    if provider_only:
        print('Android Unity runtime provider compiled.');return
    exported=ROOT/'artifacts/android/unity-export/unityLibrary/src/main'
    if not (exported/'assets/bin/Data/globalgamemanagers').is_file():raise ValueError('Export the Unity Android host first')
    for name in ('classes','dex','generated'):
        folder=output/name
        if folder.exists():shutil.rmtree(folder)
        folder.mkdir()
    run([tools/'aapt2','compile','--dir',player/'Apk/res','-o',output/'resources.zip'])
    branding=ROOT/'artifacts/branding/android-res'
    if not (branding/'drawable/disco_icon.png').is_file():raise ValueError('Prepare local app icons with make port first')
    run([tools/'aapt2','compile','--dir',branding,'-o',output/'branding.zip'])
    unsigned=output/'unaligned.apk'
    run([tools/'aapt2','link','--manifest',ROOT/'apps/android/GameManifest.xml','-I',platform,
         '--java',output/'generated','--extra-packages','com.unity3d.player','-o',unsigned,output/'resources.zip',output/'branding.zip'])
    unity=player/'Variations/il2cpp/Development';jar=unity/'Classes/classes.jar'
    sources=[*sorted((exported/'java').rglob('*.java')),*sorted((ROOT/'apps/android/game').rglob('*.java')),*sorted((output/'generated').rglob('*.java'))]
    run([java/'bin/javac','--release','8','-classpath',str(platform)+os.pathsep+str(jar),'-d',output/'classes',*sources])
    run([tools/'d8','--min-api','28','--lib',platform,'--output',output/'dex',jar,*sorted((output/'classes').rglob('*.class'))])
    (output/'libunity.so').write_bytes(adapt_desktop_audio((unity/'Libs/arm64-v8a/libunity.so').read_bytes()))
    run([compiler.parent/'llvm-strip','--strip-unneeded',output/'libunity.so'])
    run([compiler,'-std=c++17','-O2','-fPIC','-shared','-nostdlib++',
         '-Wl,-z,max-page-size=16384','-Wl,-z,common-page-size=16384','-Wl,--no-undefined',
         ROOT/'runtime/AndroidHost/OfflineStore.cpp','-o',output/'libsteam_api.so'])
    assets=ROOT/'artifacts/android/game-data/apk' if game_data else exported/'assets'
    if obb:
        archive_path=output/'main.1.org.discoport.androidgame.obb';cache=output/'obb-inputs.json'
        inputs=[{'path':str(p.relative_to(assets)),'sha256':hashlib.file_digest(p.open('rb'),'sha256').hexdigest()} for p in sorted(assets.rglob('*')) if p.is_file()]
        previous=json.loads(cache.read_text()) if cache.is_file() else {}
        if not archive_path.is_file() or previous.get('inputs')!=inputs:
            with zipfile.ZipFile(archive_path,'w') as archive:
                archive.writestr(zipfile.ZipInfo('assets/disco-port-local-v1',(1980,1,1,0,0,0)),b'')
                for path in sorted(assets.rglob('*')):
                    if path.is_file():archive.write(path,'assets/'+str(path.relative_to(assets)),compress_type=zipfile.ZIP_STORED)
            cache.write_text(json.dumps({'inputs':inputs})+'\n')
    with zipfile.ZipFile(unsigned,'a') as apk:
        apk.write(output/'dex/classes.dex','classes.dex',compress_type=zipfile.ZIP_DEFLATED)
        for name,path in [('libil2cpp.so',output/'libil2cpp.so'),('libunity.so',output/'libunity.so'),('libsteam_api.so',output/'libsteam_api.so'),('libmain.so',unity/'Libs/arm64-v8a/libmain.so')]:
            apk.write(path,'lib/arm64-v8a/'+name,compress_type=zipfile.ZIP_STORED)
        apk.write(runtime/'runtime.map','assets/runtime.map',compress_type=zipfile.ZIP_STORED)
        apk.write(runtime/'unwind.map','assets/unwind.map',compress_type=zipfile.ZIP_STORED)
        for name in ('amplify.map','amplify-unwind.map'):apk.write(runtime/name,'assets/'+name,compress_type=zipfile.ZIP_STORED)
        apk.write(ROOT/'reference/Disco.app/Contents/Resources/Data/il2cpp_data/Metadata/global-metadata.dat','assets/global-metadata.dat',compress_type=zipfile.ZIP_STORED)
        # Unity's Android first-install extractor reads APK assets directly,
        # before our provider selects NativeMetadata. These cannot live only
        # in the OBB; a previously initialized tablet masked the missing tree.
        apk.write(ROOT/'reference/Disco.app/Contents/Resources/Data/il2cpp_data/Metadata/global-metadata.dat','assets/bin/Data/Managed/Metadata/global-metadata.dat',compress_type=zipfile.ZIP_STORED)
        for path in sorted((ROOT/'reference/Disco.app/Contents/Resources/Data/il2cpp_data/Resources').glob('*.dat')):
            if path.is_symlink():raise ValueError('Unexpected runtime resource symlink')
            apk.write(path,'assets/runtime-resources/'+path.name,compress_type=zipfile.ZIP_STORED)
            apk.write(path,'assets/bin/Data/Managed/Resources/'+path.name,compress_type=zipfile.ZIP_STORED)
        for path in sorted((exported/'assets/bin/Data/Managed/etc').rglob('*')):
            if path.is_symlink():raise ValueError('Unexpected managed configuration symlink')
            if path.is_file():apk.write(path,'assets/bin/Data/Managed/'+str(path.relative_to(exported/'assets/bin/Data/Managed')),compress_type=zipfile.ZIP_STORED)
        assets=ROOT/'artifacts/android/game-data/apk' if game_data else exported/'assets'
        if game_data and not (ROOT/'artifacts/android/game-data/manifest.json').is_file():raise ValueError('Stage the complete game data first')
        for path in sorted(assets.rglob('*')):
            if path.is_file() and (not obb or path.name=='boot.config'):apk.write(path,'assets/'+str(path.relative_to(assets)),compress_type=zipfile.ZIP_STORED)
    aligned=output/'aligned.apk';apk=output/'disco-on-the-go.apk'
    run([tools/'zipalign','-f','-P','16','4',unsigned,aligned])
    key=signing_key(ROOT,java,run)
    run([tools/'apksigner','sign','--ks',key,'--ks-key-alias','androiddebugkey','--ks-pass','pass:android','--key-pass','pass:android','--out',apk,aligned])
    run([tools/'apksigner','verify','--verbose',apk])
    run([tools/'zipalign','-c','-P','16','4',apk])
    (output/'build.json').write_text(json.dumps({'scope':'Mac-derived game with Android engine; this build still requires device validation' if game_data else 'Original runtime with empty Unity Android host; gameplay not integrated','derived_manifest_sha256':payload_hash,'obb':obb,'obb_sha256':hashlib.file_digest((output/'main.1.org.discoport.androidgame.obb').open('rb'),'sha256').hexdigest() if obb else None,'apk_sha256':hashlib.file_digest(apk.open('rb'),'sha256').hexdigest(),'source_hashes':staged['source_hashes']},indent=2)+'\n')
    print('Built private Unity Android host APK:',apk.relative_to(ROOT))


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--provider-only',action='store_true');parser.add_argument('--game-data',action='store_true');parser.add_argument('--obb',action='store_true');args=parser.parse_args()
    build(args.provider_only,args.game_data,args.obb)
