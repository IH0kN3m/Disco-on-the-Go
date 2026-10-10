import unittest
from disco_port.binary import FormatError
from disco_port.adb_devices import authorized_devices

class AndroidDeviceTests(unittest.TestCase):
    def test_adb_states_and_ambiguous_or_malformed_input(self):
        self.assertEqual(authorized_devices('List of devices attached\nfixture-a device model:Tablet\nfixture-b unauthorized\nfixture-c offline\n'),['fixture-a'])
        self.assertEqual(authorized_devices('List of devices attached\n'),[])
        for value in ('bad header','List of devices attached\n-only device\n','List of devices attached\none\n',
                      'List of devices attached\na device\na device\n'):
            with self.assertRaises(FormatError): authorized_devices(value)
