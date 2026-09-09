"""Render the actual Cairo callbacks; no screenshots or mock drawing code."""
import unittest

try:
    import cairo
except ImportError:
    cairo = None

from nexum.core.experiment_session import CONFIGS, ExperimentSession
from nexum.ui.experiment_drawing import LaboratoryDrawing


@unittest.skipUnless(cairo, "PyCairo não está disponível neste Python")
class ExperimentRenderingTests(unittest.TestCase):
    def render(self, session, *, dark=False, chart=False, size=(800, 430), running=False):
        surface = cairo.ImageSurface(cairo.FORMAT_ARGB32, *size)
        cr = cairo.Context(surface)
        cr.set_source_rgb(*((.12, .13, .15) if dark else (.98, .98, .98)))
        cr.paint()
        drawing = LaboratoryDrawing(cr, dark)
        if chart:
            drawing.chart(*size, session)
        else:
            drawing.bench(*size, session, running=running)
        surface.flush()
        return bytes(surface.get_data())

    def test_every_bench_and_chart_draws_start_middle_end_in_both_themes(self):
        for eid in CONFIGS:
            session = ExperimentSession(eid)
            for fraction in (0, .5, 1):
                session.seek(session.duration*fraction)
                for dark in (False, True):
                    with self.subTest(eid=eid, fraction=fraction, dark=dark):
                        self.assertTrue(self.render(session, dark=dark, running=fraction < 1))
                        self.assertTrue(self.render(session, dark=dark, chart=True, size=(560, 190)))

    def test_each_dynamic_bench_has_a_visible_physical_change(self):
        for eid in ("gas", "titration", "electro", "calorimetry", "kinetics", "nuclear"):
            with self.subTest(eid=eid):
                session = ExperimentSession(eid)
                initial = self.render(session)
                session.seek(session.duration*.6)
                final = self.render(session)
                changed_bytes = sum(a != b for a, b in zip(initial, final))
                self.assertGreater(changed_bytes, 200)

    def test_zero_current_and_zero_rate_have_no_fictitious_motion(self):
        for eid, cfg in (("electro", {"current_a": 0}), ("kinetics", {"k_s": 0})):
            session = ExperimentSession(eid, cfg)
            initial = self.render(session, running=True)
            session.seek(session.duration)
            self.assertEqual(initial, self.render(session, running=True))

    def test_source_off_removes_the_optical_beams(self):
        lit = ExperimentSession("spectro")
        off = ExperimentSession("spectro", {"incident": 0})
        self.assertNotEqual(self.render(lit), self.render(off))

    def test_invalid_and_boundary_states_draw_without_errors(self):
        cases = [("spectro", {"epsilon_l_mol_cm": 0}), ("spectro", {"concentration_m": 0}),
                 ("nuclear", {"nuclei0": 0}), ("kinetics", {"concentration0_m": 0}),
                 ("haber", {"n_n2": 0, "n_h2": 0, "n_nh3": 2}),
                 ("electro", {"cu_conc0": .001, "cu_volume_l": .01, "current_a": 5}),
                 ("calorimetry", {"heater_power_w": 0, "initial_temp_k": 330})]
        self.render(None)
        self.render(None, chart=True)
        for eid, cfg in cases:
            with self.subTest(eid=eid, cfg=cfg):
                session = ExperimentSession(eid, cfg)
                session.seek(session.duration)
                self.render(session)
                self.render(session, chart=True, size=(560, 190))

    def test_static_parameter_changes_have_visible_effects(self):
        for eid, cfg in (("haber", {"pressure_bar": 1}), ("spectro", {"concentration_m": .015})):
            initial, changed = ExperimentSession(eid), ExperimentSession(eid, cfg)
            self.assertNotEqual(self.render(initial), self.render(changed))
            self.assertNotEqual(self.render(initial, chart=True), self.render(changed, chart=True))


if __name__ == "__main__":
    unittest.main()
