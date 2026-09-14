"""Fail explicitly if a required Windows runtime feature is unavailable."""
import tempfile
from pathlib import Path


def main():
    import faulthandler
    faulthandler.enable()
    import gi
    gi.require_version("Gtk", "4.0")
    gi.require_version("Adw", "1")
    gi.require_foreign("cairo")
    from gi.repository import Gtk, Adw, Gdk
    import cairo
    import numpy
    import scipy
    from OpenGL import GL
    from nexum.history import HistoryStore
    from nexum.core.structures import _rdkit_conformer_from_smiles, parse_mmcif

    if not Gtk.init_check() or not Gdk.Display.get_default():
        raise RuntimeError("GTK não encontrou uma sessão gráfica.")
    Adw.init()
    molecule = _rdkit_conformer_from_smiles("CCO", "Etanol", "702")
    assert len(molecule.atoms) >= 3 and molecule.bonds
    cif = '''data_test
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
ATOM 1 C CA . ALA A 1 1 0 0 0 1 20 1 A 1
'''
    assert len(parse_mmcif(cif).atoms) == 1
    with tempfile.TemporaryDirectory(prefix="nexum-") as folder:
        history = HistoryStore(Path(folder) / "histórico" / "history.sqlite3")
        history.add("windows-check", {"concentração": 1}, {"resultado": 2})
        assert len(history.latest()) == 1
    print("Chemistry and storage: OK; opening application", flush=True)
    # Instantiate every page and exercise the actual GLArea render callback.
    import sys
    import time
    from gi.repository import GLib
    from nexum.main import NexumApplication
    from nexum.ui.main_window import MainWindow
    from unittest.mock import patch
    app = NexumApplication()
    app.register(None)
    errors = []
    with tempfile.TemporaryDirectory(prefix="nexum-ui-") as folder:
        with patch("nexum.ui.main_window.data_dir", return_value=Path(folder)):
            window = MainWindow(app)
        original_hook = sys.excepthook
        sys.excepthook = lambda *error: errors.append(error)
        try:
            window.struct.viewer.set_molecule(molecule)
            window.struct.influence.set_active(True)
            window.struct.influence_opacity.set_value(35)
            assert window.struct.viewer.show_influence
            assert len(window.struct.viewer.scene["influence_pos"]) > 0
            window.stack.set_visible_child_name("structures")
            window.present()
            deadline = time.monotonic() + 2
            while time.monotonic() < deadline:
                GLib.MainContext.default().iteration(False)
                time.sleep(.005)
            if errors:
                raise RuntimeError("Falha em callback GTK/OpenGL") from errors[0][1]
            if window.struct.viewer.get_error():
                raise RuntimeError(str(window.struct.viewer.get_error()))
            assert len(window.struct.viewer.programs) == 3
            window.struct.viewer.make_current()
            assert GL.glGetError() == GL.GL_NO_ERROR
            print("OpenGL:", GL.glGetString(GL.GL_VERSION), flush=True)
            window.struct.influence.set_active(False)
            assert not window.struct.viewer.show_influence
            assert len(window.struct.viewer.scene["influence_pos"]) == 0
        finally:
            window.destroy()
            sys.excepthook = original_hook
    print("GTK4/libadwaita/Cairo/NumPy/SciPy/OpenGL/RDKit/gemmi/SQLite: OK")


if __name__ == "__main__":
    main()
