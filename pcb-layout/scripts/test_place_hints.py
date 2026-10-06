#!/usr/bin/env python3
import unittest
import place_hints as ph

REFS = {'U1': 0, 'U2': 1, 'J1': 2, 'C1': 3, 'C2': 4, 'L1': 5}
PADS = {'U1': {'7': [1.0, -2.0]}}


class Parse(unittest.TestCase):
    def test_statements(self):
        h = ph.parse('''
            group psu: U2 L1 C2      # kept together
            U1 center
            J1 on edge left  top-left
            psu right of U1  level with U1  gap: wide
            C1 near U1.7 within: 2  weight: 3
            J1 rotate 90
            C1, C2 below U1 and J1
        ''', REFS, PADS)
        kinds = [(x['kind'], x.get('arg')) for x in h]
        self.assertEqual(kinds, [('group', None), ('region', 'center'), ('edge', 'left'), ('region', 'top-left'), ('dir', 'right'), ('level', 'y'),
                                 ('near', None), ('rotate', 90), ('dir', 'below')])
        self.assertEqual(h[4]['parts'], [1, 4, 5])          # a group as the subject
        self.assertEqual(h[4]['target'], {'parts': [0]})
        self.assertEqual(h[5]['gap'], 4.0)                   # gap: belongs to the clause before it
        self.assertEqual(h[6]['target'], {'pad': [0, [1.0, -2.0]]})
        self.assertEqual((h[6]['gap'], h[6]['weight']), (2.0, 3.0))
        self.assertEqual((h[8]['parts'], h[8]['target']), ([3, 4], {'parts': [0, 2]}))

    def test_refusals(self):
        for bad in ('U9 center', 'U1 somewhere', 'U1', 'U1 right of U1', 'C1 near U1.99', 'U1 left of U2 gap: huge'):
            with self.assertRaises(ph.HintError, msg=bad):
                ph.parse(bad, REFS, PADS)


if __name__ == '__main__':
    unittest.main()
