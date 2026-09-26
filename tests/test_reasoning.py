import math
import unittest
import numpy as np
from nexum.lab.reasoning import uncertainty, speciation, R


class ReasoningTests(unittest.TestCase):
    def test_dilution_independent_relative_uncertainties(self):
        r = uncertainty("dilution", [0.1, 10, 100], [0.001, 0.1, 1], draws=10000)
        self.assertAlmostEqual(r["nominal"], 0.01)
        self.assertAlmostEqual(r["standard_uncertainty"], 0.01 * math.sqrt(3) * 0.01)
        self.assertLess(
            abs(r["monte_carlo"]["sd"] / r["standard_uncertainty"] - 1), 0.05
        )

    def test_correlated_volume_errors_cancel(self):
        corr = [[1, 0, 0], [0, 1, 1], [0, 1, 1]]
        r = uncertainty("dilution", [0.1, 10, 100], [0, 0.1, 1], corr, draws=1000)
        self.assertLess(r["standard_uncertainty"], 1e-11)
        self.assertLess(r["monte_carlo"]["sd"], 1e-10)

    def test_beer_analytic_gradient(self):
        r = uncertainty("beer", [0.5, 100, 1], [0, 0, 0], draws=1000)
        self.assertAlmostEqual(r["nominal"], 0.005)
        np.testing.assert_allclose(r["gradient"], [0.01, -0.00005, -0.005])

    def test_first_order_rate_and_zero_uncertainty(self):
        r = uncertainty("kinetics", [1, 0.5, 10], [0, 0, 0], draws=1000)
        self.assertAlmostEqual(r["nominal"], math.log(2) / 10)
        self.assertEqual(r["standard_uncertainty"], 0)

    def test_ideal_gas_si_units(self):
        r = uncertainty("gas", [R * 300, 0.001, 300], [0, 0, 0], draws=1000)
        self.assertAlmostEqual(r["nominal"], 0.001)

    def test_invalid_correlation_and_physical_samples_rejected(self):
        with self.assertRaises(ValueError):
            uncertainty(
                "beer",
                [1, 1, 1],
                [0.1, 0.1, 0.1],
                [[1, 0.9, 0.9], [0.9, 1, -0.9], [0.9, -0.9, 1]],
            )
        with self.assertRaises(ValueError):
            uncertainty("beer", [1, 1, 1], [2, 2, 2], draws=1000)
        with self.assertRaises(ValueError):
            uncertainty("kinetics", [1, 2, 10], [0, 0, 0], draws=1000)

    def test_seed_reproducibility(self):
        a = uncertainty("beer", [1, 10, 1], [0.01, 0.1, 0.01], draws=1000, seed=7)
        b = uncertainty("beer", [1, 10, 1], [0.01, 0.1, 0.01], draws=1000, seed=7)
        self.assertEqual(a, b)

    def test_speciation_ratio_midpoint_and_conservation(self):
        r = speciation(4, 2, 6, 5)
        np.testing.assert_allclose(
            r["acid_fraction"], [100 / 101, 10 / 11, 0.5, 1 / 11, 1 / 101]
        )
        np.testing.assert_allclose(
            np.asarray(r["acid_fraction"]) + r["base_fraction"], 1, atol=1e-15
        )
        self.assertLessEqual(r["balance_max_error"], 1e-15)

    def test_speciation_includes_pka_even_between_grid_points(self):
        r = speciation(4.76, 0, 14, 10)
        i = r["ph"].index(4.76)
        self.assertEqual(r["acid_fraction"][i], 0.5)


class NumericalPrecisionTests(unittest.TestCase):
    def test_distance_does_not_round_coordinates_to_render_precision(self):
        from nexum.core.structures import Atom, Molecule
        from nexum.core.molecular_analysis import measurement

        a = 10000.123456
        b = 10000.123459
        m = Molecule("Precisão", [Atom("C", a, 0, 0), Atom("C", b, 0, 0)], [])
        self.assertAlmostEqual(measurement(m, [0, 1])[1], b - a, places=15)

    def test_rmse_and_residual_standard_error_have_different_denominators(self):
        from nexum.lab.statistics import factorial, fit_design

        design = factorial(
            [{"name": "A", "low": 0, "high": 1}], replicates=3, centers=0
        )
        responses = [2 + r["coded"][0] + i * 0.1 for i, r in enumerate(design["runs"])]
        result = fit_design(design, responses)
        sse = sum(v * v for v in result["residuals"])
        self.assertAlmostEqual(result["rmse"], math.sqrt(sse / len(responses)))
        self.assertAlmostEqual(
            result["residual_standard_error"],
            math.sqrt(sse / result["degrees_of_freedom"]),
        )
