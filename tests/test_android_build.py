import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from disco_port.android_build import validate_payload, signing_key, export_paths, revision
from disco_port.binary import FormatError
from disco_port.build_inputs import sha256


class AndroidBuildTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.payload = self.root / 'apk/data'
        self.payload.parent.mkdir()
        (self.root / 'external').mkdir()
        self.payload.write_bytes(b'original synthetic payload')
        self.record = {'path': 'apk/data', 'bytes': self.payload.stat().st_size, 'sha256': sha256(self.payload)}
        self.manifest([self.record])

    def manifest(self, records):
        (self.root / 'derived-manifest.json').write_text(json.dumps({'files': records}))

    def test_payload_detects_modified_missing_and_extra_files(self):
        self.assertEqual(validate_payload(self.root), sha256(self.root / 'derived-manifest.json'))
        self.payload.write_bytes(b'changed')
        with self.assertRaises(FormatError): validate_payload(self.root)
        self.payload.unlink()
        with self.assertRaises(FormatError): validate_payload(self.root)
        self.payload.write_bytes(b'original synthetic payload')
        (self.root / 'external/extra').write_bytes(b'uninventoried')
        with self.assertRaises(FormatError): validate_payload(self.root)

    def test_payload_rejects_duplicate_escape_and_symlink_ownership(self):
        for records in ([self.record, self.record], [], [dict(self.record, path='../outside')],
                        [dict(self.record, path=str(self.payload))], [dict(self.record, path='unowned/data')]):
            self.manifest(records)
            with self.assertRaises(FormatError): validate_payload(self.root)
        self.manifest([self.record])
        self.payload.unlink(); self.payload.symlink_to(self.root / 'derived-manifest.json')
        with self.assertRaises(FormatError): validate_payload(self.root)

    def test_payload_rejects_malformed_records_and_root_links(self):
        for records in ([None], [{}], [dict(self.record, bytes=True)], [dict(self.record, path=7)],
                        [dict(self.record, sha256='invalid')]):
            self.manifest(records)
            with self.assertRaises(FormatError): validate_payload(self.root)
        self.manifest([self.record])
        (self.root / 'external').rmdir()
        (self.root / 'external').symlink_to(self.payload.parent, target_is_directory=True)
        with self.assertRaises(FormatError): validate_payload(self.root)

    def test_key_creation_is_independent_of_probe_and_reuses_key(self):
        commands = []
        def run(command):
            commands.append(command)
            Path(command[command.index('-keystore') + 1]).write_bytes(b'synthetic key')
        first = signing_key(self.root, Path('/java'), run)
        self.assertEqual(first, signing_key(self.root, Path('/java'), run))
        self.assertEqual(len(commands), 1)
        self.assertTrue(first.is_relative_to(self.root / 'artifacts'))

    def test_export_override_does_not_read_missing_default_jdk(self):
        with patch.dict('os.environ', {'DISCO_ANDROID_JDK': '/custom/jdk'}, clear=True):
            self.assertEqual(export_paths(self.root)['jdk'], Path('/custom/jdk'))

    def test_revision_rejects_unsupported_tools(self):
        properties = self.root / 'source.properties'
        properties.write_text('Pkg.Revision = 27.2.12479018\n')
        revision(properties, '27.2.12479018')
        with self.assertRaises(FormatError): revision(properties, '19.0.5232133')
