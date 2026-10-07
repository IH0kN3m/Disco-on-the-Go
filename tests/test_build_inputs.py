import hashlib
from pathlib import Path
import tempfile
import unittest
from disco_port.build_inputs import validate_sources
from disco_port.binary import FormatError


class BuildInputTests(unittest.TestCase):
    def test_exact_revision_missing_modified_and_escaping_input(self):
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory); bundle = base / 'App'; bundle.mkdir()
            file = bundle / 'input'; file.write_bytes(b'synthetic')
            expected = {'input': hashlib.sha256(b'synthetic').hexdigest()}
            self.assertEqual(validate_sources(bundle, expected), expected)
            file.write_bytes(b'changed')
            with self.assertRaises(FormatError): validate_sources(bundle, expected)
            file.unlink()
            with self.assertRaises(FileNotFoundError): validate_sources(bundle, expected)
            outside = base / 'outside'; outside.write_bytes(b'synthetic'); file.symlink_to(outside)
            with self.assertRaises(FormatError): validate_sources(bundle, expected)
