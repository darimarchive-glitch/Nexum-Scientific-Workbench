"""Behavior and scientific regressions for the didactic laboratory."""
import math
import unittest
from unittest.mock import patch

from nexum.core.experiment_session import CONFIGS, ExperimentSession, indicator_state
from nexum.core.experiments import F
from nexum.ui.experiment_drawing import flask_fill_height


class ExperimentSessionTests(unittest.TestCase):
    def test_all_benches_prepare_and_reach_their_final_state(self):
        for eid in CONFIGS:
            with self.subTest(experiment=eid):
                session = ExperimentSession(eid)
                session.seek(session.duration)
                self.assertTrue(session.metrics)
                self.assertTrue(session.guide)
                self.assertEqual(session.complete, session.dynamic)

    def test_titration_volume_is_transferred_and_color_follows_ph(self):
        session = ExperimentSession("titration")
        initial_color = session.state["indicator"]["color"]
        session.seek(50)
        self.assertAlmostEqual(session.state["liquid_volume_ml"], 50)
        self.assertAlmostEqual(session.state["ph"], 7, places=10)
        self.assertEqual(session.state["indicator"]["label"], "Incolor")
        session.step()
        self.assertAlmostEqual(session.state["base_added_ml"], 25.05)
        self.assertNotEqual(session.state["indicator"]["color"], initial_color)
        self.assertAlmostEqual(session.state["remaining_base_ml"]+session.state["base_added_ml"], 50)
        self.assertEqual(session.point, (session.state["base_added_ml"], session.state["ph"]))

    def test_weak_acid_equivalence_is_basic_with_same_glass_volume(self):
        session = ExperimentSession("titration", {"mode": "weak-strong"})
        session.seek(50)
        self.assertAlmostEqual(session.state["liquid_volume_ml"], 50)
        self.assertAlmostEqual(session.state["ph"], 8.7219, delta=.001)
        self.assertEqual(session.state["indicator"]["label"], "Em viragem")

    def test_indicator_never_changes_the_underlying_ph(self):
        for name in ("Fenolftaleína", "Azul de bromotimol", "Sem indicador"):
            session = ExperimentSession("titration", {"indicator": name})
            session.seek(50)
            self.assertAlmostEqual(session.state["ph"], 7, places=10)
        self.assertEqual(indicator_state(14, "Sem indicador")["label"], "Incolor")

    def test_indicator_endpoints_and_transition_ranges(self):
        for name, lo, hi in (("Fenolftaleína", 8.2, 10), ("Azul de bromotimol", 6, 7.6)):
            self.assertEqual(indicator_state(lo, name)["range"], (lo, hi))
            self.assertNotEqual(indicator_state(lo, name)["color"], indicator_state(hi, name)["color"])
            for ph in (0, 7, 9, 14):
                self.assertTrue(all(0 <= v <= 1 for v in indicator_state(ph, name)["color"]))

    def test_large_excess_base_does_not_cancel_hydrogen_root(self):
        session = ExperimentSession("titration", {"base_c": 10})
        session.seek(session.duration)
        s = session.state
        self.assertTrue(math.isfinite(s["ph"]))
        self.assertAlmostEqual(s["h_m"]-s["oh_m"], s["strong_acid_excess_m"], places=11)

    def test_no_equivalence_marker_outside_deliverable_volume(self):
        session = ExperimentSession("titration", {"max_volume_ml": 10})
        self.assertEqual(session.markers, [])
        self.assertIn("não alcança", session.guide)

    def test_curve_contains_exact_equivalence_even_off_grid(self):
        session = ExperimentSession("titration", {"acid_v_ml": 23.714})
        veq = session.state["equivalence_ml"]
        match = [p for p in session.reference_curve if abs(p[0]-veq) < 1e-10]
        self.assertTrue(match)
        self.assertAlmostEqual(match[0][1], 7, places=9)

    def test_erlenmeyer_rises_with_volume_and_is_nonlinear(self):
        self.assertAlmostEqual(flask_fill_height(0), 0)
        self.assertAlmostEqual(flask_fill_height(1), 1)
        levels = [flask_fill_height(f) for f in (.25, .5, .75)]
        self.assertTrue(levels[0] < levels[1] < levels[2])
        self.assertGreater(levels[2]-levels[1], levels[1]-levels[0])

    def test_daniell_zero_current_transfers_neither_charge_nor_mass(self):
        session = ExperimentSession("electro", {"current_a": 0})
        session.seek(120)
        s = session.state
        self.assertEqual(s["charge_c"], 0)
        self.assertEqual(s["copper_mass_deposited_g"], 0)
        self.assertEqual(s["zinc_mass_lost_g"], 0)
        self.assertAlmostEqual(s["e_rev_v"], 1.1)

    def test_daniell_stops_at_available_copper_and_has_no_fake_zero_voltage(self):
        session = ExperimentSession("electro", {"cu_conc0": .001, "cu_volume_l": .01, "current_a": 5})
        self.assertAlmostEqual(session.duration, 2*F*.001*.01/5)
        session.advance(999)
        self.assertTrue(session.complete)
        self.assertTrue(session.state["exhausted"])
        self.assertEqual(session.state["cu_conc_m"], 0)
        self.assertEqual(session.state["current_a"], 0)
        self.assertIsNone(session.state["e_rev_v"])
        self.assertIsNone(session.point)
        self.assertTrue(all(p[1] != 0 for p in session.reference_curve))
        self.assertAlmostEqual(session.state["copper_mass_deposited_g"], .001*.01*63.546)

    def test_calorimetry_energy_and_celsius_thermometer(self):
        session = ExperimentSession("calorimetry")
        session.seek(120)
        s = session.state
        self.assertAlmostEqual(s["temperature_c"], s["temperature_k"]-273.15)
        self.assertAlmostEqual(s["input_energy_j"], s["stored_energy_j"]+s["heat_lost_j"])
        self.assertGreater(s["temperature_c"], 25)
        self.assertEqual(session.point[1], s["temperature_c"])

    def test_unpowered_calorimeter_cools_and_can_gain_heat_from_ambient(self):
        cooling = ExperimentSession("calorimetry", {"heater_power_w": 0, "initial_temp_k": 330})
        cooling.seek(120)
        self.assertLess(cooling.state["temperature_k"], 330)
        self.assertGreater(cooling.state["heat_flow_w"], 0)
        warming = ExperimentSession("calorimetry", {"heater_power_w": 0, "ambient_temp_k": 330})
        warming.seek(120)
        self.assertGreater(warming.state["temperature_k"], 298.15)
        self.assertLess(warming.state["heat_lost_j"], 0)

    def test_static_sessions_do_not_create_a_fictitious_timeline(self):
        for eid in ("haber", "spectro"):
            session = ExperimentSession(eid)
            initial = dict(session.state)
            session.advance(100)
            self.assertEqual(session.elapsed, 0)
            self.assertEqual(session.history, [])
            self.assertEqual(session.state, initial)

    def test_haber_handles_initial_ammonia_without_nitrogen_conversion(self):
        session = ExperimentSession("haber", {"n_n2": 0, "n_h2": 0, "n_nh3": 2})
        self.assertIsNone(session.state["conversion_n2"])
        self.assertIn(("Conversão N₂", "—"), session.metrics)
        eq = session.state["equilibrium_moles"]
        self.assertAlmostEqual(2*eq["n_n2"]+eq["n_nh3"], 2)
        self.assertAlmostEqual(2*eq["n_h2"]+3*eq["n_nh3"], 6)

    def test_haber_comparison_changes_with_pressure(self):
        low = ExperimentSession("haber", {"pressure_bar": 1})
        high = ExperimentSession("haber", {"pressure_bar": 200})
        self.assertGreater(high.state["equilibrium_moles"]["n_nh3"], low.state["equilibrium_moles"]["n_nh3"])

    def test_beer_transmission_source_off_and_blank(self):
        for cfg in ({"incident": 0}, {"concentration_m": 0}, {"epsilon_l_mol_cm": 0}):
            session = ExperimentSession("spectro", cfg)
            if cfg.get("incident") == 0:
                self.assertEqual(session.state["transmitted"], 0)
                self.assertIn("Fonte apagada", session.guide)
            else:
                self.assertEqual(session.state["absorbance"], 0)
                self.assertEqual(session.state["transmittance"], 1)
            self.assertEqual(session.point[0], session.config["concentration_m"])

    def test_kinetics_transforms_a_into_b_with_conserved_total(self):
        session = ExperimentSession("kinetics", {"k_s": math.log(2)/10})
        session.seek(10)
        self.assertAlmostEqual(session.state["concentration_m"], .5)
        self.assertAlmostEqual(session.state["product_m"], .5)
        self.assertAlmostEqual(session.state["concentration_m"]+session.state["product_m"], 1)
        self.assertEqual(session.point, (10, .5))
        self.assertEqual(session.markers[0], (10., "t½"))

    def test_kinetics_zero_rate_and_empty_sample(self):
        inert = ExperimentSession("kinetics", {"k_s": 0})
        inert.seek(40)
        self.assertEqual(inert.state["concentration_m"], 1)
        self.assertEqual(inert.state["product_m"], 0)
        self.assertEqual(inert.markers, [])
        empty = ExperimentSession("kinetics", {"concentration0_m": 0})
        empty.seek(40)
        self.assertEqual(empty.state["product_m"], 0)

    def test_decay_half_lives_population_and_activity(self):
        session = ExperimentSession("nuclear")
        for half_lives in range(5):
            session.seek(half_lives*10)
            expected = 1000*2**(-half_lives)
            self.assertAlmostEqual(session.state["remaining"], expected)
            self.assertAlmostEqual(session.state["remaining"]+session.state["decayed"], 1000)
            self.assertAlmostEqual(session.state["activity_bq"], math.log(2)/10*expected)

    def test_seek_backwards_discards_future_trace_and_reset_restores_state(self):
        session = ExperimentSession("titration")
        initial = dict(session.state)
        session.seek(90)
        session.seek(20)
        self.assertTrue(all(x <= 10 for x, _ in session.history))
        self.assertEqual(session.history[-1], session.point)
        session.seek(0)
        self.assertEqual(session.state, initial)
        self.assertEqual(session.history, [session.point])

    def test_new_parameters_have_a_new_curve_and_zero_elapsed(self):
        first = ExperimentSession("kinetics")
        first.seek(20)
        second = ExperimentSession("kinetics", {"k_s": .2})
        self.assertEqual(second.elapsed, 0)
        self.assertEqual(len(second.history), 1)
        self.assertNotEqual(first.reference_curve, second.reference_curve)

    def test_a_tick_computes_only_its_current_state(self):
        session = ExperimentSession("titration")
        curve = session.reference_curve
        with patch.object(session, "_sample", wraps=session._sample) as sample:
            session.advance(.033)
            self.assertEqual(sample.call_count, 1)
        self.assertIs(session.reference_curve, curve)

    def test_invalid_duration_rate_and_nonfinite_fields_are_rejected(self):
        cases = [("titration", {"flow_ml_s": 0}), ("titration", {"flow_ml_s": -1}),
                 ("titration", {"max_volume_ml": 0}), ("gas", {"duration_s": 0}),
                 ("kinetics", {"duration_s": -2}), ("calorimetry", {"mass_g": 0}),
                 ("spectro", {"concentration_m": float("nan")}), ("nuclear", {"nuclei0": float("inf")}),
                 ("spectro", {"incident": -1}), ("haber", {"temp_k": 20})]
        for eid, config in cases:
            with self.subTest(eid=eid, config=config), self.assertRaises(ValueError):
                ExperimentSession(eid, config)


if __name__ == "__main__":
    unittest.main()
