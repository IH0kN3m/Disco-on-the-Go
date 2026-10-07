"""Static compatibility checks for the one inspected original game revision."""
import hashlib
from pathlib import Path

from .binary import FormatError

# Fingerprints, not distributed game content. Offsets in the adapters require these exact inputs.
SOURCE_HASHES = {
    'Contents/Frameworks/GameAssembly.dylib': '0550f5a1e9fb9addba0b365908f21bc5a04a2f3979f1b2a640774a05a6c7ab52',
    'Contents/Resources/Data/il2cpp_data/Metadata/global-metadata.dat': '182882d0ef82ca09bbbe556c04cf4759a700bc80a9ab2e306eb998cd29a43f5c',
    'Contents/PlugIns/steam_api.bundle/Contents/MacOS/libsteam_api.dylib': '1e7e029ac92c3221cc205acbe9e3bbc56ff4eed966125595a2e09748a50eb909',
    'Contents/PlugIns/AmplifyTextureNative.bundle/Contents/MacOS/AmplifyTextureNative': '474612e980951feb0f855bf5e57ae86e89d9492f4b61a43b50f58967bddd297e',
}


def sha256(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def validate_sources(bundle, expected=None):
    bundle = Path(bundle).resolve(strict=True)
    result = {}
    for name, digest in (SOURCE_HASHES if expected is None else expected).items():
        path = (bundle / name).resolve(strict=True)
        if not path.is_relative_to(bundle) or not path.is_file():
            raise FormatError('Source input escapes the supplied bundle or is not a file')
        actual = sha256(path)
        if actual != digest:
            raise FormatError(f'Unsupported game revision: {name}; expected SHA-256 {digest}, got {actual}')
        result[name] = actual
    return result
