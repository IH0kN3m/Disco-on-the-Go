#!/usr/bin/env python3
"""Build an ARM64 Android diagnostic APK; this does not build the playable game."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import zipfile

from disco_port.binary import MachO
from disco_port.build_inputs import validate_sources
from disco_port.function_starts import function_starts
from disco_port.android_probe import checked_leaf, DOT_ADDRESS, DOT_SHA256

ROOT = Path(__file__).resolve().parent.parent


def build(sdk, java, original=False, shaders=False, mapped=False):
    sdk, java = sdk.resolve(), java.resolve()
    tools = sdk / 'build-tools/36.0.0'
    platform = sdk / 'platforms/android-36/android.jar'
    ndk = sdk / 'ndk/27.2.12479018/toolchains/llvm/prebuilt/darwin-x86_64'
    compiler = ndk / 'bin/aarch64-linux-android28-clang++'
    for path in (tools/'aapt2',tools/'d8',tools/'apksigner',tools/'zipalign',platform,compiler,java/'bin/javac',java/'bin/keytool'):
        if not path.is_file(): raise ValueError('Required Android tool missing: ' + str(path))
    base = ROOT / 'artifacts/android'
    output = base / ('build-mapped-runtime' if mapped else 'build-original-leaf' if original else 'build-capabilities')
    output.mkdir(parents=True, exist_ok=True)
    for directory in ('classes', 'dex'):
        p = output / directory
        if p.exists(): shutil.rmtree(p)
        p.mkdir()
    environment = os.environ.copy(); environment['JAVA_HOME'] = str(java)
    log = output / 'build.log'
    def run(command):
        with log.open('a') as stream:
            result = subprocess.run([str(c) for c in command],cwd=output,env=environment,stdout=stream,stderr=subprocess.STDOUT)
        if result.returncode: raise ValueError(f'Android tool failed: {Path(command[0]).name}; inspect {log.relative_to(ROOT)}')
    log.write_text('Local Android diagnostic build\n')
    extra = []
    source_hashes = {}
    if original:
        source_hashes = validate_sources(ROOT/'reference/Disco.app')
        image = MachO((ROOT/'reference/Disco.app/Contents/Frameworks/GameAssembly.dylib').read_bytes())
        code = checked_leaf(image,function_starts(image),DOT_ADDRESS,24,DOT_SHA256)
        (output/'dot.bin').write_bytes(code)
        assembly = output/'OriginalDot.S'
        assembly.write_text('.text\n.p2align 2\n.global DiscoOriginalDot\n.hidden DiscoOriginalDot\n.type DiscoOriginalDot, %function\nDiscoOriginalDot:\n.incbin "dot.bin"\n.size DiscoOriginalDot, .-DiscoOriginalDot\n.section .note.GNU-stack,"",%progbits\n')
        extra = ['-DDISCO_ORIGINAL_KERNEL=1', assembly]
    runtime = None
    if mapped:
        from stage_android_runtime import stage
        runtime, staged = stage()
        source_hashes = staged['source_hashes']
        extra += ['-DDISCO_MAPPED_RUNTIME=1', '-I', runtime, runtime/'MissingImports.S']
    native = output/'libdiscoprobe.so'
    run([compiler,'-std=c++17','-O2','-fPIC','-shared','-static-libstdc++','-Wl,-z,max-page-size=16384',
         '-Wl,-z,common-page-size=16384','-Wl,--no-undefined','-Wl,-z,noexecstack',
         ROOT/'runtime/AndroidHost/Probe.cpp',ROOT/'runtime/AndroidHost/ShaderProbe.cpp',ROOT/'runtime/AndroidHost/BCDecodeProbe.cpp',
         ROOT/'runtime/AndroidHost/RuntimeProbe.cpp',ROOT/'runtime/AndroidHost/RuntimeLoader.cpp',ROOT/'runtime/AndroidHost/DarwinUnwind.cpp',ROOT/'runtime/AndroidHost/DarwinBridge.cpp',ROOT/'runtime/AndroidHost/DarwinVarargs.cpp',ROOT/'runtime/AndroidHost/DarwinThreads.cpp',ROOT/'runtime/AndroidHost/DarwinABI.S',ROOT/'runtime/AndroidHost/DarwinIcalls.S',ROOT/'runtime/AndroidHost/IcallProbe.cpp',*extra,'-lvulkan','-lEGL','-lGLESv3','-landroid','-llog','-o',native])
    java_sources = sorted((ROOT/'apps/android/src').rglob('*.java'))
    run([java/'bin/javac','--release','8','-classpath',platform,'-d',output/'classes',*java_sources])
    run([tools/'d8','--min-api','28','--lib',platform,'--output',output/'dex',*sorted((output/'classes').rglob('*.class'))])
    unsigned = output/'unaligned.apk'
    run([tools/'aapt2','link','--manifest',ROOT/'apps/android/AndroidManifest.xml','-I',platform,'-o',unsigned])
    with zipfile.ZipFile(unsigned,'a') as apk:
        apk.write(output/'dex/classes.dex','classes.dex',compress_type=zipfile.ZIP_DEFLATED)
        apk.write(native,'lib/arm64-v8a/libdiscoprobe.so',compress_type=zipfile.ZIP_STORED)
        if runtime:
            apk.write(runtime/'runtime.map','assets/runtime.map',compress_type=zipfile.ZIP_STORED)
            apk.write(runtime/'unwind.map','assets/unwind.map',compress_type=zipfile.ZIP_STORED)
            for name in ('amplify.map','amplify-unwind.map'):apk.write(runtime/name,'assets/'+name,compress_type=zipfile.ZIP_STORED)
            apk.write(ROOT/'reference/Disco.app/Contents/Resources/Data/il2cpp_data/Metadata/global-metadata.dat','assets/global-metadata.dat',compress_type=zipfile.ZIP_STORED)
    if shaders:
        samples=ROOT/'artifacts/android/shaders'
        count=int((samples/'shader-count.txt').read_text())
        if not 0<count<=64:raise ValueError('Invalid shader sample count')
        with zipfile.ZipFile(unsigned,'a') as apk:
            for name in ['shader-count.txt',*[f'shader-{i:03}.{stage}' for i in range(count) for stage in ('vert','frag')]]:
                apk.write(samples/name,'assets/'+name,compress_type=zipfile.ZIP_DEFLATED)
    aligned = output/'aligned.apk'
    run([tools/'zipalign','-f','-P','16','4',unsigned,aligned])
    from disco_port.android_build import signing_key
    key = signing_key(ROOT, java, run)
    apk = output/'disco-android-probe.apk'
    run([tools/'apksigner','sign','--ks',key,'--ks-key-alias','androiddebugkey','--ks-pass','pass:android','--key-pass','pass:android','--out',apk,aligned])
    run([tools/'apksigner','verify','--verbose',apk])
    run([tools/'zipalign','-c','-P','16','4',apk])
    report = {'scope':'Android capability and selected native runtime diagnostics; not a game port',
              'original_leaf':original,'mapped_runtime':mapped,'shader_samples':shaders,'source_hashes':source_hashes,'ndk':'27.2.12479018','build_tools':'36.0.0',
              'compile_sdk':36,'min_sdk':28,'abi':'arm64-v8a','elf_alignment':16384,
              'apk_sha256':hashlib.sha256(apk.read_bytes()).hexdigest()}
    (output/'build.json').write_text(json.dumps(report,indent=2)+'\n')
    print('Built',apk.relative_to(ROOT),flush=True)
    print('Diagnostic only. This APK contains private derived code/shaders and must not be redistributed.' if original or shaders or mapped else 'Original tooling only; no game content embedded.')


if __name__ == '__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--sdk',type=Path,default=Path(os.environ.get('ANDROID_HOME',Path.home()/'Library/Android/sdk')))
    parser.add_argument('--java-home',type=Path)
    parser.add_argument('--with-original-kernel',action='store_true',help='Locally link the inspected original ARM64 arithmetic leaf; no runtime initialization')
    parser.add_argument('--with-shader-samples',action='store_true',help='Include locally extracted GLES compile/link experiments; private game data')
    parser.add_argument('--with-mapped-runtime',action='store_true',help='Run the pinned native runtime startup, metadata invocation and collection experiment; no gameplay')
    args=parser.parse_args()
    try:
        java=args.java_home or Path(subprocess.check_output(['/usr/libexec/java_home','-v','17'],text=True).strip())
        build(args.sdk,java,args.with_original_kernel,args.with_shader_samples,args.with_mapped_runtime)
    except (ValueError,OSError,subprocess.CalledProcessError) as error:
        parser.exit(1,f'Android build failed: {error}\n')
