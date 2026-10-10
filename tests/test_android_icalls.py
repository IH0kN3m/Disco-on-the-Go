import unittest
from disco_port.android_icalls import stack_layout,scalar,split_arguments
from disco_port.binary import FormatError

class IcallABITests(unittest.TestCase):
    def test_packed_integers_and_pointer_alignment(self):
        self.assertEqual(stack_layout([('int',4)]*8+[('int',1),('int',4),('int',1),('int',8)]),
                         [(1,0,0),(4,4,8),(1,8,16),(8,16,24)])
        self.assertEqual(stack_layout([('int',8)]*11),[(8,0,0),(8,8,8),(8,16,16)])
    def test_independent_float_bank_and_shared_stack(self):
        values=[('int',4)]*8+[('float',4)]*8+[('float',4),('int',1),('float',8),('int',4)]
        self.assertEqual(stack_layout(values),[(4,0,0),(1,4,8),(8,8,16),(4,16,24)])
    def test_unknown_and_malformed_signatures_rejected(self):
        for values in [[('int',3)],[('vector',16)],[('float',1)],[('int',8)]*65]:
            with self.assertRaises(FormatError):stack_layout(values)
        with self.assertRaises(FormatError):scalar('UnknownAggregate')
        with self.assertRaises(FormatError):split_arguments('A<B, int')
        self.assertEqual(split_arguments('A<B,C> const&, int'),['A<B,C> const&','int'])
