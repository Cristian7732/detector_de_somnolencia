"""Pruebas sintéticas: reglas y geometría; no miden detección de somnolencia."""
import math
from types import SimpleNamespace
import unittest
from detector import DetectorState, Settings, ratios


class RulesTest(unittest.TestCase):
    def test_one_blink_after_reopening_and_no_blinks_during_long_closure(self):
        state = DetectorState()
        for t, ear in [(0, .3), (.1, .1), (.2, .1), (.3, .3)]:
            state.update(t, ear, .1)
        self.assertEqual(state.blinks, 1)
        for i in range(4, 30):
            last = state.update(i / 10, .1, .1)
        self.assertTrue(last['alert'])
        state.update(3, .3, .1)
        self.assertEqual(state.blinks, 1)

    def test_mouth_event_counted_once_and_new_opening_does_not_alert_immediately(self):
        state = DetectorState()
        for i in range(41):
            status = state.update(i / 10, .3, .8)
        self.assertTrue(status['alert'])
        self.assertEqual(state.mouth_events, 0)
        state.update(4.1, .3, .1)
        self.assertEqual(state.mouth_events, 1)
        self.assertFalse(state.update(4.2, .3, .8)['alert'])

    def test_loss_and_long_processing_gap_reset_timers(self):
        state = DetectorState()
        for i in range(12):
            state.update(i / 10, .1, .8)
        self.assertFalse(state.update(1.2, None, None)['alert'])
        self.assertFalse(state.update(1.3, .1, .8)['alert'])
        self.assertFalse(state.update(10, .1, .8)['alert'])
        self.assertEqual(len(state.history), 1)

    def test_time_weighting_at_different_sampling_rates(self):
        # Cuatro segundos de ventana; un segundo cerrado = 25 %, independientemente de FPS.
        for hz in [10, 20, 30]:
            state = DetectorState(Settings(window_seconds=4))
            for i in range(4 * hz + 1):
                status = state.update(i / hz, .1 if i < hz else .3, .1)
                if i < 4 * hz:
                    self.assertIsNone(status['closure'])
            self.assertAlmostEqual(status['closure'], 25)
            for i in range(4 * hz + 1, 8 * hz + 1):
                status = state.update(i / hz, .3, .1)
            self.assertAlmostEqual(status['closure'], 0)
            self.assertLessEqual(len(state.history), 4 * hz + 2)

    def test_invalid_values_and_partial_window_never_trigger_ratio_alert(self):
        state = DetectorState()
        self.assertFalse(state.update(0, math.nan, .1)['valid'])
        self.assertIsNone(state.update(.1, .1, .1)['closure'])
        self.assertFalse(state.update(.2, .1, math.inf)['valid'])

    def test_geometry_degenerate_and_scale_invariant(self):
        points = [SimpleNamespace(x=0, y=0) for _ in range(478)]
        self.assertIsNone(ratios(points, 640, 480))
        from detector import LEFT_EYE, RIGHT_EYE, MOUTH_UPPER, MOUTH_LOWER
        for indices in [LEFT_EYE, RIGHT_EYE]:
            for idx, (x, y) in zip(indices, [(0, 0), (.25, .1), (.75, .1), (1, 0), (.75, -.1), (.25, -.1)]):
                points[idx] = SimpleNamespace(x=x, y=y)
        for idx in MOUTH_UPPER:
            points[idx] = SimpleNamespace(x=.5, y=.1)
        for idx in MOUTH_LOWER:
            points[idx] = SimpleNamespace(x=.5, y=-.1)
        points[291] = SimpleNamespace(x=1, y=0)
        ear, mar = ratios(points, 100, 100)
        self.assertAlmostEqual(ear, .2)
        self.assertAlmostEqual(mar, .2)
        self.assertEqual(ratios(points, 100, 100), ratios(points, 200, 200))


if __name__ == '__main__':
    unittest.main()
