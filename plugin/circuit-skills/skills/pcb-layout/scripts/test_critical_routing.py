import copy
import unittest
from check_critical_routing import assess, measure


class CriticalGateTests(unittest.TestCase):
    def setUp(self):
        self.metrics = {n: dict(copper_mm=10., segments=1, vias=0, layers=['F.Cu'],
            unsupported_items=0, reference_samples=42, reference_missing_samples=0) for n in ['P','N']}
        self.policy = dict(version=1, groups=[dict(name='pair', differential_pair=True,
            legs=[['P'],['N']], allowed_layers=['F.Cu'], max_vias=0,
            max_copper_mm=20, max_copper_mismatch_mm=1, required_reviews=['impedance'])],
            reviews={'impedance': dict(board_sha256='sha',reviewer='engineer',evidence='stackup and solver report')})

    def test_current_review_and_screen_pass(self):
        self.assertTrue(assess(self.metrics,self.policy,'sha')['ok'])

    def test_stale_review_fails_closed(self):
        report=assess(self.metrics,self.policy,'rerouted')
        self.assertFalse(report['ok'])
        self.assertEqual(report['findings'][0]['kind'],'unresolved')

    def test_missing_net_is_not_zero_length_pass(self):
        del self.metrics['N']
        self.assertIn('net N absent',str(assess(self.metrics,self.policy,'sha')))

    def test_layer_via_mismatch_and_reference_holes(self):
        self.metrics['P'].update(copper_mm=14, vias=2, layers=['In1.Cu'],reference_missing_samples=2)
        messages=str(assess(self.metrics,self.policy,'sha')['findings'])
        for message in ['disallowed layers','2 vias','mismatch','filled reference']:
            self.assertIn(message,messages)

    def test_missing_budgets_and_review_requirements_not_pass(self):
        group=self.policy['groups'][0]
        del group['max_vias']
        group['required_reviews']=[]
        self.assertFalse(assess(self.metrics,self.policy,'sha')['ok'])

    def test_series_net_copper_is_aggregated(self):
        self.metrics['P2']=copy.deepcopy(self.metrics['P'])
        self.policy['groups'][0]['legs'][0].append('P2')
        self.assertIn('mismatch 10.000',str(assess(self.metrics,self.policy,'sha')))

    def test_unsupported_arc_does_not_silently_pass(self):
        self.metrics['P']['unsupported_items']=1
        self.assertIn('unsupported',str(assess(self.metrics,self.policy,'sha')))

    def test_empty_policy_rejected(self):
        with self.assertRaises(ValueError):
            assess({},dict(version=1,groups=[]),'sha')

    def test_invalid_numeric_budget(self):
        self.policy['groups'][0]['max_copper_mismatch_mm']=float('nan')
        with self.assertRaises(ValueError):
            assess(self.metrics,self.policy,'sha')

    def test_native_track_via_and_missing_reference(self):
        try:
            import pcbnew
        except ImportError:
            self.skipTest('native geometry test requires KiCad pcbnew')
        board=pcbnew.BOARD()
        net=pcbnew.NETINFO_ITEM(board,'P')
        board.Add(net)
        track=pcbnew.PCB_TRACK(board)
        track.SetStart(pcbnew.VECTOR2I(pcbnew.FromMM(1),pcbnew.FromMM(1)))
        track.SetEnd(pcbnew.VECTOR2I(pcbnew.FromMM(4),pcbnew.FromMM(5)))
        track.SetLayer(pcbnew.F_Cu)
        track.SetNet(net)
        board.Add(track)
        via=pcbnew.PCB_VIA(board)
        via.SetPosition(track.GetEnd())
        via.SetNet(net)
        board.Add(via)
        self.policy['reference_layers']={'F.Cu':{'layer':'In1.Cu','net':'GND'}}
        metrics=measure(board,self.policy)['P']
        self.assertAlmostEqual(metrics['copper_mm'],5)
        self.assertEqual(metrics['vias'],1)
        self.assertEqual(metrics['layers'],['F.Cu'])
        self.assertEqual(metrics['reference_samples'],21)
        self.assertEqual(metrics['reference_missing_samples'],21)


if __name__ == '__main__':
    unittest.main()
