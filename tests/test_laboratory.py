"""Independent numerical references and portable-project regression checks."""

import base64
import copy
import math
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch
import zipfile
import numpy as np
from nexum.lab import (
    datasets,
    examples,
    extensions,
    investigations,
    molecules,
    processes,
    reports,
    statistics,
    workflows,
)
from nexum.lab.project import (
    Project,
    fresh,
    validate,
    write_project,
    read_project,
    fingerprint,
)


def series(x=None, y=None):
    x = [0.0, 1.0, 2.0, 3.0, 4.0] if x is None else x
    y = [2 * v + 1 for v in x] if y is None else y
    return {
        "id": "sample",
        "name": "Amostra",
        "x": x,
        "y": y,
        "xunit": "s",
        "yunit": "mg/L",
        "origin": "Simulado",
        "source": {},
    }


class DataTests(unittest.TestCase):
    def test_brazilian_csv_mapping_raw_and_roundtrip(self):
        raw = "tempo;replica A;replica B\n2,0;7,0;8,0\n0,0;1,0;2,0\n1,0;4,0;5,0\n".encode()
        parsed = datasets.table(raw.decode())
        d = datasets.from_table(parsed, 0, 2, "réplica B", raw, "s", "Abs")
        self.assertEqual(d["x"], [0, 1, 2])
        self.assertEqual(d["y"], [2, 5, 8])
        self.assertEqual(base64.b64decode(d["source"]["original_base64"]), raw)
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "series.csv"
            datasets.export_csv(d, path)
            r = datasets.table(path.read_text(encoding="utf-8-sig"))
            self.assertEqual(r["rows"], [[0, 2], [1, 5], [2, 8]])

    def test_invalid_input_never_silently_drops_rows(self):
        for raw in (
            "x;y\n0;1\n1;\n2;3",
            "x;y\n0;1\n1;NaN\n2;3",
            "x;y\n0;1\n1;2;4\n2;3",
        ):
            with self.subTest(raw=raw), self.assertRaises(ValueError):
                datasets.table(raw)

    def test_duplicate_x_and_negative_column_rejected(self):
        parsed = datasets.table("x;y\n0;1\n1;2\n1;3")
        with self.assertRaises(ValueError):
            datasets.from_table(parsed, 0, 1, "bad")
        with self.assertRaises(ValueError):
            datasets.from_table(parsed, -1, 0, "bad")

    def test_jcamp_scaling_and_reject_compression(self):
        d = datasets.import_jcamp(
            "##TITLE=teste\n##XFACTOR=2\n##YFACTOR=0.5\n##XUNITS=cm-1\n##XYPOINTS=(XY..XY)\n1,2 2,4 3,6\n##END="
        )
        self.assertEqual(d["x"], [2, 4, 6])
        self.assertEqual(d["y"], [1, 2, 3])
        with self.assertRaises(ValueError):
            datasets.import_jcamp("##XYDATA=(X++(Y..Y))\n0 A12")

    def test_original_hash_checked(self):
        d = datasets.from_table(
            datasets.table("x;y\n0;1\n1;2\n2;3"), 0, 1, "x", b"original"
        )
        d["source"]["sha256"] = "0" * 64
        with self.assertRaises(ValueError):
            datasets.validate_dataset(d)

    def test_unsorted_project_series_rejected(self):
        with self.assertRaises(ValueError):
            datasets.validate_dataset(series([2, 0, 1], [2, 0, 1]))


class WorkflowTests(unittest.TestCase):
    def test_derivative_and_integral_have_analytic_reference(self):
        d = series()
        before = copy.deepcopy(d)
        result = workflows.execute(
            d,
            [
                {"op": "integrate", "parameters": {"lower": 0.5, "upper": 3.5}},
                {"op": "derivative"},
            ],
        )
        self.assertAlmostEqual(result["metrics"]["area_1"]["value"], 15.0)
        np.testing.assert_allclose(result["y"], 2, atol=1e-12)
        self.assertEqual(d, before)
        self.assertEqual(
            result["trace"][0]["output_sha256"], result["trace"][1]["input_sha256"]
        )

    def test_polynomial_smoothing_retains_quadratic(self):
        x = np.arange(11.0).tolist()
        y = [v * v - 3 * v + 4 for v in x]
        r = workflows.execute(
            series(x, y), [{"op": "smooth", "parameters": {"window": 5, "degree": 2}}]
        )
        np.testing.assert_allclose(r["y"], y, atol=1e-10)

    def test_baseline_then_normalization_fails_for_linear_series(self):
        with self.assertRaises(ValueError):
            workflows.execute(series(), [{"op": "baseline"}, {"op": "normalize"}])

    def test_calibration_inverts_forward_model(self):
        r = workflows.execute(
            series(),
            [
                {
                    "op": "calibrate",
                    "parameters": {"slope": 2, "intercept": 1, "unit": "mg/L"},
                }
            ],
        )
        np.testing.assert_allclose(r["y"], series()["x"])

    def test_bad_smoothing_and_bounds_rejected(self):
        for steps in (
            [{"op": "smooth", "parameters": {"window": 4}}],
            [{"op": "integrate", "parameters": {"lower": -1}}],
            [{"op": "calibrate", "parameters": {"slope": 0}}],
            [{"op": "unknown"}],
        ):
            with self.assertRaises(ValueError):
                workflows.execute(series(), steps)
        with self.assertRaises(ValueError):
            workflows.execute(
                series([0, 1, 3, 4, 8]), [{"op": "smooth", "parameters": {"window": 3}}]
            )


class ProjectTests(unittest.TestCase):
    def test_roundtrip_all_examples_and_independent_report(self):
        with tempfile.TemporaryDirectory() as folder:
            for i in range(len(examples.NAMES)):
                data = examples.example(i)
                path = Path(folder) / f"{i}.nexum7"
                write_project(path, data)
                self.assertEqual(read_project(path), data)
                reports.report(data, Path(folder) / f"{i}.html")

    def test_failed_edit_rolls_back_and_undo_redo_are_independent(self):
        p = Project()
        p.edit("title", lambda d: d.update(title="Novo título"))
        p.undo()
        self.assertEqual(p.data["title"], "Novo projeto")
        p.redo()
        self.assertEqual(p.data["title"], "Novo título")
        before = copy.deepcopy(p.data)
        with self.assertRaises(ValueError):
            p.edit("invalid", lambda d: d.update(pipeline=[{"op": "execute_python"}]))
        self.assertEqual(p.data, before)

    def test_invalid_write_does_not_replace_existing_project(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "data.nexum7"
            d = fresh()
            write_project(path, d)
            before = path.read_bytes()
            d["title"] = None
            with self.assertRaises(ValueError):
                write_project(path, d)
            self.assertEqual(path.read_bytes(), before)

    def test_tampering_and_zip_path_entries_rejected(self):
        with tempfile.TemporaryDirectory() as folder:
            p = Path(folder) / "x.nexum7"
            with zipfile.ZipFile(p, "w") as z:
                z.writestr("project.json", "{}")
                z.writestr("SHA256.txt", "0" * 64)
            with self.assertRaises(ValueError):
                read_project(p)
            with zipfile.ZipFile(p, "w") as z:
                z.writestr("../outside", "x")
                z.writestr("SHA256.txt", "0" * 64)
            with self.assertRaises(ValueError):
                read_project(p)

    def test_project_identity_cannot_escape_recovery_directory(self):
        data = fresh()
        data["id"] = "../../escape"
        with self.assertRaises(ValueError):
            validate(data)

    def test_invalid_graph_scene_design_and_pipeline_rejected(self):
        for key, value in [
            ("graph", {"atoms": [], "bonds": [[0, 1, 1]]}),
            ("scenes", [{"title": "x", "state": None}]),
            ("pipeline", [{"op": "no"}]),
        ]:
            data = fresh()
            data[key] = value
            with self.subTest(key=key), self.assertRaises(ValueError):
                validate(data)
        data = examples.example(3)
        data["design"]["runs"][0]["values"][0] += 1
        with self.assertRaises(ValueError):
            validate(data)

    def test_report_escapes_user_html(self):
        d = fresh("<script>alert(1)</script>")
        d["notes"] = "<img src=x onerror=alert(1)>"
        with tempfile.TemporaryDirectory() as folder:
            p = Path(folder) / "report.html"
            reports.report(d, p)
            s = p.read_text()
            self.assertNotIn("<script>", s)
            self.assertIn("&lt;script&gt;", s)
            self.assertIn("&lt;img", s)


class StatisticsTests(unittest.TestCase):
    def test_factorial_balanced_reproducible_and_known_coefficients(self):
        design = examples.example(3)["design"]
        again = statistics.factorial(design["factors"], 2, 3, 42)
        self.assertEqual(
            [r["coded"] for r in design["runs"]], [r["coded"] for r in again["runs"]]
        )
        r = statistics.fit_design(design, [row["response"] for row in design["runs"]])
        np.testing.assert_allclose(
            [c["value"] for c in r["coefficients"]], [50, 12, 5, 3], atol=1e-10
        )
        self.assertAlmostEqual(r["r2"], 1)

    def test_fit_requires_degrees_of_freedom(self):
        d = statistics.factorial([{"name": "A", "low": 0, "high": 1}], 1, 0)
        with self.assertRaises(ValueError):
            statistics.fit_design(d, [1, 2])

    def test_quality_reference_and_specification_are_separate(self):
        r = statistics.quality([9.9, 10, 10.1, 10.7], 10, 0.2, 9, 11)
        self.assertEqual(r["outside_control"], [4])
        self.assertEqual(r["outside_specification"], [])
        self.assertAlmostEqual(r["mean"], 10.175)
        self.assertAlmostEqual(r["bias"], 0.175)

    def test_recovery_reference_and_domain(self):
        self.assertAlmostEqual(statistics.recovery(10, 14.8, 5), 96)
        with self.assertRaises(ValueError):
            statistics.recovery(10, 15, 0)
        with self.assertRaises(ValueError):
            statistics.quality([1, 2], 1, 0)


class ProcessTests(unittest.TestCase):
    def test_mass_component_and_energy_conservation(self):
        result = processes.simulate(examples.example(4)["process"])
        s = result["streams"]
        self.assertAlmostEqual(s["Mistura"]["flow_kg_h"], 150)
        self.assertAlmostEqual(s["Mistura"]["fractions"]["soluto"] * 150, 10)
        heat = result["balances"][3]["heat_kj_h"]
        expected = 100 * 4.18 * (60 - 20) + 50 * 4 * (60 - 40)
        self.assertAlmostEqual(heat, expected)
        self.assertAlmostEqual(
            s["Divisão"]["flow_kg_h"] + s["Divisão:rest"]["flow_kg_h"], 150
        )
        self.assertEqual(result["terminal_streams"], ["Divisão:rest", "Divisão"])

    def test_no_double_consumption_or_cycle(self):
        nodes = examples.example(4)["process"]
        nodes.append(
            {
                "id": "Extra",
                "kind": "heater",
                "inputs": ["Mistura"],
                "parameters": {"temperature": 80},
            }
        )
        with self.assertRaises(ValueError):
            processes.simulate(nodes)
        with self.assertRaises(ValueError):
            processes.simulate(
                [
                    {
                        "id": "loop",
                        "kind": "heater",
                        "inputs": ["loop"],
                        "parameters": {"temperature": 80},
                    }
                ]
            )

    def test_conversion_keeps_total_mass_and_explicit_yield(self):
        r = processes.simulate(
            [
                {
                    "id": "F",
                    "kind": "feed",
                    "parameters": {"flow": 100, "composition": {"A": 0.6, "água": 0.4}},
                },
                {
                    "id": "R",
                    "kind": "convert",
                    "inputs": ["F"],
                    "parameters": {"reactant": "A", "product": "B", "conversion": 0.5},
                },
            ]
        )
        self.assertEqual(
            r["streams"]["R"]["fractions"], {"A": 0.3, "B": 0.3, "água": 0.4}
        )
        self.assertEqual(r["streams"]["R"]["flow_kg_h"], 100)

    def test_invalid_composition_rejected(self):
        with self.assertRaises(ValueError):
            processes.stream(100, {"A": 0.9})


class MoleculeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.graph = molecules.chemistry("smiles_graph", "CCO")
        cls.built = molecules.chemistry("builder", cls.graph)

    def test_real_builder_formula_indices_and_aromatic_bonds(self):
        m = self.built["molecule"]
        self.assertEqual(m["metadata"]["formula"], "C2H6O")
        self.assertEqual(len(m["atoms"]), 9)
        self.assertEqual([a["element"] for a in m["atoms"][:3]], ["C", "C", "O"])
        self.assertTrue(m["metadata"]["optimization_converged"])
        benzene = molecules.chemistry(
            "builder", molecules.chemistry("smiles_graph", "c1ccccc1")
        )["molecule"]
        self.assertEqual(sum(b[2] == 2 for b in benzene["bonds"]), 3)

    def test_invalid_valence_is_rejected(self):
        g = {
            "atoms": [{"element": "O"}] + [{"element": "C"}] * 3,
            "bonds": [[0, i, 1] for i in range(1, 4)],
        }
        with self.assertRaises(ValueError):
            molecules.chemistry("builder", g)

    def test_conformers_have_relative_energies(self):
        rows = molecules.chemistry("conformers", self.graph, 3)
        self.assertEqual(len(rows), 3)
        self.assertEqual(rows[0]["relative_energy_kcal_mol"], 0)
        self.assertTrue(all(r["relative_energy_kcal_mol"] >= 0 for r in rows))

    def test_alignment_removes_known_rigid_motion(self):
        ref = copy.deepcopy(self.built["molecule"])
        mov = copy.deepcopy(ref)
        for a in mov["atoms"]:
            a["x"], a["y"], a["z"] = -a["y"] + 5, a["x"] - 2, a["z"] + 3
        result = molecules.align(ref, mov)
        self.assertLess(result["rmsd_angstrom"], 1e-12)
        np.testing.assert_allclose(
            [[a[k] for k in ("x", "y", "z")] for a in result["molecule"]["atoms"]],
            [[a[k] for k in ("x", "y", "z")] for a in ref["atoms"]],
            atol=1e-10,
        )

    def test_alignment_rejects_collinear_or_duplicate_pairs(self):
        ref = copy.deepcopy(self.built["molecule"])
        with self.assertRaises(ValueError):
            molecules.align(ref, ref, [(0, 0), (0, 1), (2, 2)])
        for i, a in enumerate(ref["atoms"]):
            a.update(x=float(i), y=0.0, z=0.0)
        with self.assertRaises(ValueError):
            molecules.align(ref, ref)

    def test_manual_assignment_tied_to_molecule_version(self):
        a = molecules.assign(
            series(), self.built["molecule"], 0.5, 3.5, [0, 2], "carbono e oxigênio"
        )
        self.assertAlmostEqual(a["area"], 15)
        self.assertEqual(a["molecule_sha256"], fingerprint(self.built["molecule"]))
        altered = copy.deepcopy(self.built["molecule"])
        altered["atoms"][0]["x"] += 1
        self.assertNotEqual(a["molecule_sha256"], fingerprint(altered))

    def test_editor_rejects_stereochemistry_isotopes_and_radicals(self):
        for smiles in ("N[C@@H](C)C(=O)O", "[13CH4]", "C/C=C/C", "[CH3]"):
            with (
                self.subTest(smiles=smiles),
                self.assertRaises((ValueError, RuntimeError)),
            ):
                molecules.chemistry("smiles_graph", smiles)

    def test_aromatic_explicit_hydrogen_preserved(self):
        g = molecules.chemistry("smiles_graph", "c1cc[nH]c1")
        r = molecules.chemistry("builder", g)
        self.assertEqual(r["molecule"]["metadata"]["formula"], "C4H5N")

    def test_worker_protocol_supports_new_operations(self):
        with patch.dict(
            os.environ,
            {
                "NEXUM_CHEMISTRY_PYTHON": os.environ.get(
                    "NEXUM_CHEMISTRY_PYTHON", sys.executable
                )
            },
        ):
            g = molecules.chemistry("smiles_graph", "O")
            r = molecules.chemistry("builder", g)
            self.assertEqual(r["molecule"]["metadata"]["formula"], "H2O")
            self.assertEqual(len(molecules.chemistry("conformers", g, 2)), 2)


class TeachingAndExtensionsTests(unittest.TestCase):
    def test_teaching_seed_and_equivalence_ph(self):
        a = investigations.create("kinetics", 10, 0)
        b = investigations.create("kinetics", 10, 0)
        self.assertEqual(a["dataset"]["y"], b["dataset"]["y"])
        self.assertAlmostEqual(a["dataset"]["y"][-1], math.exp(-a["answer"] * 100))
        t = investigations.create("titration", 42, 0)
        y = np.interp(20 * t["answer"] / 0.1, t["dataset"]["x"], t["dataset"]["y"])
        self.assertLess(abs(y - 7), 1.5)
        r = investigations.submit(a, a["answer"], "Ajuste exponencial")
        self.assertEqual(r["relative_error_percent"], 0)

    def test_extension_runs_only_same_reviewed_source(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "sum.py"
            path.write_text(
                'def run(payload):\n return {"soma": sum(payload["dataset"]["y"])}\n'
            )
            info = extensions.inspect(path)
            r = extensions.run(path, {"dataset": series()}, info["sha256"])
            self.assertEqual(r["result"]["soma"], 25)
            path.write_text("def run(payload):\n return {}\n")
            with self.assertRaises(ValueError):
                extensions.run(path, {}, info["sha256"])

    def test_extension_has_bounded_finite_result(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "nan.py"
            path.write_text('def run(payload):\n return float("nan")\n')
            info = extensions.inspect(path)
            with self.assertRaises(ValueError):
                extensions.run(path, {}, info["sha256"])


if __name__ == "__main__":
    unittest.main()
