import unittest
from disco_port.release_audit import check_source


class ReleaseAuditTests(unittest.TestCase):
    def test_only_original_text_locations_are_eligible(self):
        self.assertEqual(check_source('tools/example.py', b'print("hello")'), [])
        for path, data, mode in [('artifacts/code.py', b'x', '100644'), ('reference/Disco.app/file', b'x', '100644'),
                                 ('runtime/texture.png', b'png', '100644'), ('tools/dump.py', b'x\0', '100644'),
                                 ('tools/out.py', b'x', '120000'), ('../README.md', b'x', '100644'),
                                 ('tools/out.py', b'x' * 262145, '100644'), ('tools/out.py', b'\xff', '100644')]:
            with self.subTest(path=path, mode=mode): self.assertTrue(check_source(path, data, mode))

    def test_private_values_and_credentials_are_reported_without_echoing_them(self):
        identifier = 'synthetic-sensitive-value'
        self.assertEqual(check_source('README.md', identifier.encode(), private_values=(identifier,)), ['local device/signing identifier'])
        key = '-----BEGIN ' + 'PRIVATE KEY-----'
        self.assertIn('private key', check_source('README.md', key.encode()))
        personal = '/' + 'Users/' + 'fixture/private'
        self.assertIn('personal absolute path', check_source('README.md', personal.encode()))
