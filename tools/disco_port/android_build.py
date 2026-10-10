"""Toolchain and private payload checks for the Mac-to-Android build."""
import json
import os
from pathlib import Path
import subprocess

from .binary import FormatError
from .build_inputs import sha256
from .android_engine import UNITY_SHA256


def sdk_path():
    return Path(os.environ.get('ANDROID_HOME', Path.home() / 'Library/Android/sdk'))


def export_paths(root):
    base = root / 'artifacts/toolchains'
    return {
        'sdk': Path(os.environ.get('DISCO_ANDROID_SDK', base / 'android-legacy/sdk')),
        'ndk': Path(os.environ.get('DISCO_ANDROID_NDK', base / 'android-legacy/android-ndk-r19')),
        'jdk': Path(os.environ['DISCO_ANDROID_JDK']) if 'DISCO_ANDROID_JDK' in os.environ
               else Path((base / 'jdk8-path.txt').read_text().strip()),
    }


def require_file(path):
    if not path.is_file(): raise FormatError('Missing Android toolchain file: ' + str(path))


def revision(path, expected):
    require_file(path)
    fields = {key.strip(): value.strip() for key, value in
              (line.split('=', 1) for line in path.read_text().splitlines() if '=' in line)}
    if fields.get('Pkg.Revision', '').strip() != expected:
        raise FormatError('Unexpected toolchain revision: ' + str(path))


def validate_toolchains(root, editor):
    sdk = sdk_path()
    player = editor.parents[3] / 'PlaybackEngines/AndroidPlayer'
    engine = player / 'Variations/il2cpp/Development/Libs/arm64-v8a/libunity.so'
    require_file(engine)
    if sha256(engine) != UNITY_SHA256: raise FormatError('Unsupported Unity Android engine fingerprint')
    legacy = export_paths(root)
    for path in (legacy['sdk'] / 'platforms/android-30/android.jar',
                 legacy['sdk'] / 'build-tools/30.0.2/aapt', legacy['jdk'] / 'bin/javac'):
        require_file(path)
    revision(legacy['sdk'] / 'tools/source.properties', '26.1.1')
    revision(legacy['sdk'] / 'build-tools/30.0.2/source.properties', '30.0.2')
    revision(legacy['ndk'] / 'source.properties', '19.0.5232133')
    jdk8 = subprocess.check_output([str(legacy['jdk'] / 'bin/javac'), '-version'], stderr=subprocess.STDOUT, text=True).strip()
    if not jdk8.startswith('javac 1.8.'): raise FormatError('Unity export requires JDK 8')
    java = Path(subprocess.check_output(['/usr/libexec/java_home', '-v', '17'], text=True).strip())
    jdk17 = subprocess.check_output([str(java / 'bin/javac'), '-version'], text=True).strip()
    if not jdk17.startswith('javac 17.'): raise FormatError('APK assembly requires JDK 17')
    for name in ('aapt2', 'd8', 'zipalign', 'apksigner'):
        require_file(sdk / 'build-tools/36.0.0' / name)
    require_file(sdk / 'platforms/android-36/android.jar')
    revision(sdk / 'build-tools/36.0.0/source.properties', '36.0.0')
    revision(sdk / 'ndk/27.2.12479018/source.properties', '27.2.12479018')
    compiler = sdk / 'ndk/27.2.12479018/toolchains/llvm/prebuilt/darwin-x86_64/bin'
    for name in ('aarch64-linux-android28-clang++', 'llvm-nm', 'llvm-strip'): require_file(compiler / name)
    return {'unity_android_sha256': UNITY_SHA256, 'export_jdk': jdk8, 'assembly_jdk': jdk17,
            'ndk': '27.2.12479018', 'build_tools': '36.0.0', 'compile_sdk': 36}


def signing_key(root, java, run):
    """Reuse one workspace key so rebuilding retains update/save compatibility."""
    key = root / 'artifacts/android/signing/debug.keystore'
    key.parent.mkdir(parents=True, exist_ok=True)
    if not key.exists():
        run([java / 'bin/keytool', '-genkeypair', '-keystore', key, '-storepass', 'android',
             '-keypass', 'android', '-alias', 'androiddebugkey', '-keyalg', 'RSA',
             '-keysize', '2048', '-validity', '10000',
             '-dname', 'CN=Local Android Debug,O=Disco Port,C=US', '-noprompt'])
    return key


def validate_payload(base):
    """Reject stale, missing, extra or modified derived payloads before packaging."""
    manifest = json.loads((base / 'derived-manifest.json').read_text())
    if not isinstance(manifest, dict): raise FormatError('Invalid derived asset manifest')
    records = manifest.get('files')
    if not isinstance(records, list) or not records: raise FormatError('Empty derived asset manifest')
    expected = set()
    for entry in records:
        if (not isinstance(entry, dict) or not isinstance(entry.get('path'), str)
                or type(entry.get('bytes')) is not int or entry['bytes'] < 0
                or not isinstance(entry.get('sha256'), str) or len(entry['sha256']) != 64
                or any(c not in '0123456789abcdef' for c in entry['sha256'])):
            raise FormatError('Malformed derived asset record')
        name = entry['path']; path = base / name
        if name in expected: raise FormatError('Duplicate derived asset')
        expected.add(name)
        if (Path(name).is_absolute() or not Path(name).parts or Path(name).parts[0] not in ('apk', 'external')
                or '..' in Path(name).parts or not path.resolve().is_relative_to(base.resolve())
                or path.is_symlink() or not path.is_file()):
            raise FormatError('Invalid derived asset ownership')
        if path.stat().st_size != entry['bytes'] or sha256(path) != entry['sha256']:
            raise FormatError('Derived asset changed; rerun asset preparation: ' + name)
    actual = set()
    for folder in ('apk', 'external'):
        if (base / folder).is_symlink() or not (base / folder).is_dir():
            raise FormatError('Invalid derived asset root')
        for path in (base / folder).rglob('*'):
            if path.is_symlink(): raise FormatError('Derived asset symlink')
            if path.is_file(): actual.add(path.relative_to(base).as_posix())
    if actual != expected: raise FormatError('Derived asset inventory changed; rerun asset preparation')
    return sha256(base / 'derived-manifest.json')
