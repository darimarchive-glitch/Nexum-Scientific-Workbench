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
            window.struct._apply_molecule(molecule)
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
            from nexum.core.molecular_analysis import molecular_surface
            from nexum.ui.session_actions import snapshot,restore
            output=Path("build/visual-checks");output.mkdir(parents=True,exist_ok=True)
            viewer=window.struct.viewer
            viewer.set_dark(False);viewer.export_png(output/"vdw-light.png")
            viewer.set_dark(True);viewer.export_png(output/"vdw-dark.png")
            viewer.surface_mesh=molecular_surface(molecule,"vdw",resolution=24)
            viewer.clip_enabled=True;viewer.export_png(output/"surface-cut.png")
            viewer.make_current();assert GL.glGetError()==GL.GL_NO_ERROR
            panel=window.struct.analysis;panel.mode.set_selected(1);panel.selected(0);panel.selected(1)
            assert "Distância" in panel.result.get_text()
            window.analysis.mode.set_selected(1);window.analysis.simulate();window.analysis.analyze()
            assert "Concentração" in window.analysis.report.get_text()
            window.analysis.plot.export(output/"calibration.svg")
            state=snapshot(window);restore(window,state)
            assert window.struct.viewer.surface_mesh is not None
            assert window.analysis.dataset["origin"]=="Simulado"
            window.analysis.mode.set_selected(3);window.analysis.analyze()
            assert window.analysis.tertiary.data
            from nexum.branding import APP_ID
            assert Gtk.IconTheme.get_for_display(Gdk.Display.get_default()).has_icon(APP_ID)
            if errors:raise RuntimeError("Falha no fluxo integrado") from errors[0][1]
            print("Medições/superfícies/PNG/SVG/calibração/titulação/sessão/logo: OK",flush=True)

            window.struct.influence.set_active(False)
            assert not window.struct.viewer.show_influence
            assert len(window.struct.viewer.scene["influence_pos"]) == 0
        finally:
            window.destroy()
            sys.excepthook = original_hook
    print("GTK4/libadwaita/Cairo/NumPy/SciPy/OpenGL/RDKit/gemmi/SQLite: OK")


if __name__ == "__main__":
    main()

