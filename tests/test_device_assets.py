import copy
from pathlib import Path
import tempfile
import unittest

from disco_port.binary import FormatError
from disco_port.device_assets import data_manifest, manifest_bytes, validate_manifest


def fixture():
    return {'format': 1, 'files': [
        {'path': name, 'size': 3, 'sha256': 'a' * 64}
        for name in ('globalgamemanagers', 'Managed/Metadata/global-metadata.dat')]}


class DeviceAssetsTests(unittest.TestCase):
    def test_canonical_fingerprint_and_owned_changes(self):
        value = fixture()
        self.assertEqual(manifest_bytes(value), manifest_bytes(copy.deepcopy(value)))
        changed = copy.deepcopy(value)
        changed['files'][0]['sha256'] = 'b' * 64
        self.assertNotEqual(manifest_bytes(value), manifest_bytes(changed))

    def test_malformed_paths_hashes_counts_and_required_inputs(self):
        for path in ('.', '../outside', '/outside', 'a//b', 'a/./b', 'a\\b', '\0'):
            value = fixture(); value['files'][0]['path'] = path
            with self.assertRaises(FormatError): validate_manifest(value)
        for change in ('duplicate', 'hash', 'size', 'empty', 'required', 'version'):
            value = fixture()
            if change == 'duplicate': value['files'].append(value['files'][0])
            elif change == 'hash': value['files'][0]['sha256'] = 'xyz'
            elif change == 'size': value['files'][0]['size'] = True
            elif change == 'empty': value['files'] = []
            elif change == 'required': value['files'].pop()
            else: value['format'] = 2
            with self.assertRaises(FormatError): validate_manifest(value)
        value = fixture(); value['format'] = True
        with self.assertRaises(FormatError): validate_manifest(value)

    def test_symlinks_fail_and_file_bytes_are_hashed(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / 'Managed/Metadata').mkdir(parents=True)
            (root / 'globalgamemanagers').write_bytes(b'one')
            (root / 'Managed/Metadata/global-metadata.dat').write_bytes(b'two')
            first = data_manifest(root)
            (root / 'globalgamemanagers').write_bytes(b'new')
            self.assertNotEqual(first, data_manifest(root))
            (root / 'link').symlink_to(root / 'globalgamemanagers')
            with self.assertRaises(FormatError): data_manifest(root)
