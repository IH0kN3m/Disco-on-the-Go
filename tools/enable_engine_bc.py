#!/usr/bin/env python3
"""Replace the pinned engine's Metal format object with a checked BC wrapper experiment."""
import hashlib
from pathlib import Path
import shutil
import subprocess

from disco_port.binary import FormatError
from disco_port.metal_bc import embedded_bitcode, rename_metal_definitions

ROOT = Path(__file__).resolve().parent.parent
SHA = '73e2c74f22ea83464e227a4c127b11740bf4c2bb4322dee50655cebd2bb58f19'
FUNCTIONS = {
    'PixelFormat': '_ZN5metal11PixelFormatE14GraphicsFormatPS0_',
    'UnityGraphicsFormat': '_ZN5metal19UnityGraphicsFormatE14MTLPixelFormat',
    'PixelFormatElementSize': '_ZN5metal22PixelFormatElementSizeE14MTLPixelFormat',
    'TextureFormatBlockSize': '_ZN5metal22TextureFormatBlockSizeE14MTLPixelFormat',
    'IsCompressedPixelFormat': '_ZN5metal23IsCompressedPixelFormatE14MTLPixelFormat',
    'IsFilterCompatible': '_ZN5metal18IsFilterCompatibleE14MTLPixelFormat',
    'IsColorRenderable': '_ZN5metal17IsColorRenderableE14MTLPixelFormat',
    'SupportsBlending': '_ZN5metal16SupportsBlendingE14MTLPixelFormat',
    'IsTextureViewCompatible': '_ZN5metal23IsTextureViewCompatibleE14MTLPixelFormatS0_',
    'InitFormatUsageFlags': '_ZN5metal20InitFormatUsageFlagsEP12GraphicsCaps',
}


def main():
    source = ROOT / 'artifacts/build/unity-ios/Libraries/libiPhone-lib.a'
    destination = ROOT / 'artifacts/build/native-engine-ios/Libraries/libiPhone-lib.a'
    output = ROOT / 'artifacts/linkage/bc-bridge'
    output.mkdir(parents=True, exist_ok=True)
    run = lambda args: subprocess.run(args, check=True, capture_output=True)
    original = run(['/usr/bin/ar', '-p', str(source), 'TextureFormatMetal.o']).stdout
    if hashlib.sha256(original).hexdigest() != SHA:
        raise FormatError('Unsupported Unity Metal object; exact 2020.3.12f1 object required')
    bitcode = output / 'original.bc'; bitcode.write_bytes(embedded_bitcode(original))
    ir = output / 'original.ll'
    run(['xcrun', 'clang', '-target', 'arm64-apple-ios17.0', '-S', '-emit-llvm', '-x', 'ir', str(bitcode), '-o', str(ir)])
    text = rename_metal_definitions(ir.read_text(), FUNCTIONS)
    changed = output / 'wrapped.ll'; changed.write_text(text)
    sdk = run(['xcrun', '--sdk', 'iphoneos', '--show-sdk-path']).stdout.decode().strip()
    replacement = output / 'TextureFormatMetal.o'
    run(['xcrun', 'clang', '-target', 'arm64-apple-ios17.0', '-c', '-x', 'ir', str(changed), '-o', str(replacement)])
    bridge = output / 'DiscoMetalBCBridge.o'
    run(['xcrun', 'clang++', '-target', 'arm64-apple-ios17.0', '-isysroot', sdk, '-fobjc-arc', '-O2', '-c',
         str(ROOT / 'runtime/UnityHost/iOS/MetalBCBridge.mm'), '-o', str(bridge)])
    archive = output / 'libiPhone-lib.a'
    shutil.copyfile(source, archive)
    run(['/usr/bin/ar', '-r', str(archive), str(replacement), str(bridge)])
    run(['/usr/bin/ranlib', str(archive)])
    shutil.copyfile(archive, destination)
    print('Checked BC bridge selected in derived engine archive; game data and GameAssembly unchanged. Device validation required.')


if __name__ == '__main__':
    try:
        main()
    except (OSError, ValueError, subprocess.CalledProcessError) as error:
        if isinstance(error, subprocess.CalledProcessError):
            print(error.stderr.decode(errors='replace')[-3000:])
        raise SystemExit(f'BC experiment failed: {error}')
