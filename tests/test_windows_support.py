import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

from nexum import chemistry_worker, paths
from nexum.core.structures import _rdkit_conformer_from_smiles, _rdkit_conformer_from_molblock, parse_mmcif
from nexum.history import HistoryStore


CIF = '''data_example
loop_
_atom_site.group_PDB
_atom_site.id
_atom_site.type_symbol
_atom_site.label_atom_id
_atom_site.label_alt_id
_atom_site.label_comp_id
_atom_site.label_asym_id
_atom_site.label_entity_id
_atom_site.label_seq_id
_atom_site.Cartn_x
_atom_site.Cartn_y
_atom_site.Cartn_z
_atom_site.occupancy
_atom_site.B_iso_or_equiv
_atom_site.auth_seq_id
_atom_site.auth_asym_id
_atom_site.pdbx_PDB_model_num
ATOM 1 C CA . ALA A 1 1 1 2 3 1 20 1 A 1
'''


class PathsTests(unittest.TestCase):
    def test_windows_data_survives_a_project_location_change(self):
        with tempfile.TemporaryDirectory(prefix="nexum espaço ") as folder:
            with patch.object(paths.sys, "platform", "win32"), patch.dict(os.environ, {"LOCALAPPDATA": folder}):
                self.assertEqual(paths.data_dir(), Path(folder) / "Nexum")
                self.assertEqual(paths.cache_dir(), Path(folder) / "Nexum/Cache")
                db_path = paths.data_dir() / "history.sqlite3"
                HistoryStore(db_path).add("titulação", {"pH": 7}, {"válido": True})
                self.assertEqual(json.loads(HistoryStore(db_path).latest()[0]["result"]), {"válido": True})

    def test_linux_keeps_existing_history_and_cache(self):
        with patch.object(paths.sys, "platform", "linux"):
            self.assertEqual(paths.data_dir(), Path.home() / ".local/share/nexum-lab")
            self.assertEqual(paths.cache_dir(), Path.home() / ".cache/nexum-lab")

    def test_windows_without_localappdata(self):
        with patch.object(paths.sys, "platform", "win32"), patch.dict(os.environ, {"LOCALAPPDATA": ""}):
            self.assertEqual(paths.data_dir(), Path.home() / "AppData/Local/Nexum")


class ChemistryWorkerTests(unittest.TestCase):
    def setUp(self):
        # CI's MSYS2 interpreter uses the configured CPython; Linux uses itself.
        self.python = os.environ.get("NEXUM_CHEMISTRY_PYTHON", sys.executable)
        self.environment = patch.dict(os.environ, {"NEXUM_CHEMISTRY_PYTHON": self.python})
        self.environment.start()
        self.addCleanup(self.environment.stop)

    def test_real_smiles_generation_keeps_metadata_and_unicode(self):
        molecule = _rdkit_conformer_from_smiles("CCO", "Etanol – geração", "702")
        self.assertEqual(molecule.name, "Etanol – geração")
        self.assertEqual(molecule.identifier, "702")
        self.assertEqual(len(molecule.atoms), 9)
        self.assertTrue(molecule.bonds)
        self.assertIsInstance(molecule.bonds[0], tuple)
        self.assertIn("ETKDGv3", molecule.metadata["conformer"])
        self.assertGreater(max(a.z for a in molecule.atoms) - min(a.z for a in molecule.atoms), .01)

    def test_real_mmcif_preserves_coordinates_and_residue(self):
        molecule = parse_mmcif(CIF, "Proteína α")
        self.assertEqual(molecule.name, "Proteína α")
        self.assertEqual(molecule.atoms[0].position.tolist(), [1, 2, 3])
        self.assertEqual(molecule.atoms[0].residue, "ALA")
        self.assertFalse(molecule.atoms[0].hetero)

    def test_molblock_route_generates_a_conformer(self):
        block = """water
  Nexum

  1  0  0  0  0  0  0  0  0  0999 V2000
    0.0000    0.0000    0.0000 O   0  0  0  0  0  0  0  0  0  0  0  0
M  END
"""
        self.assertEqual(len(_rdkit_conformer_from_molblock(block, "Água", "962").atoms), 3)

    def test_invalid_molecule_reports_failure(self):
        with self.assertRaises(RuntimeError):
            _rdkit_conformer_from_smiles("invalid molecule", "Inválida", "0")

    def test_timeout_and_missing_executable_are_actionable(self):
        for error in (FileNotFoundError(), subprocess.TimeoutExpired("worker", 180)):
            with patch.object(chemistry_worker.subprocess, "run", side_effect=error):
                with self.assertRaisesRegex(RuntimeError, "install-windows.cmd"):
                    chemistry_worker.call("smiles", "O", "Água", "962")

    def test_unknown_operation_is_rejected(self):
        with self.assertRaises(RuntimeError):
            chemistry_worker.call("arbitrary-code")
