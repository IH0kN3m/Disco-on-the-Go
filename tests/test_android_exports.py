import unittest
from disco_port.android_exports import export_sources

class AndroidExportsTests(unittest.TestCase):
    def test_symbol_ownership_and_overrides(self):
        asm, header = export_sources({'_il2cpp_init': 4, '_il2cpp_alloc': 8, '_il2cpp_set_data_dir': 12})
        self.assertIn('il2cpp_alloc:', asm)
        self.assertNotIn('il2cpp_init:', asm)
        self.assertNotIn('il2cpp_set_data_dir:', asm)
        self.assertIn('br x16', asm)
        self.assertIn('"_il2cpp_init"', header)
    def test_invalid_and_duplicate_symbols(self):
        for names in ([], ['_valid', '_valid'], ['_bad\n.global injected'], ['unprefixed'], ['_foo.bar']):
            with self.assertRaises(ValueError): export_sources(names)
