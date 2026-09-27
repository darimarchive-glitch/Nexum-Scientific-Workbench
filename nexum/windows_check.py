"""Fail explicitly if a required Windows runtime feature is unavailable."""
import tempfile
import os
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
            monitor=window.get_display().get_monitor_at_surface(window.get_surface())
            if monitor:
                geometry=monitor.get_geometry()
                assert window.get_width() <= max(860,geometry.width), "Window exceeds monitor width"
            if errors:
                raise RuntimeError("Falha em callback GTK/OpenGL") from errors[0][1]
            if window.struct.viewer.get_error():
                raise RuntimeError(str(window.struct.viewer.get_error()))
            assert len(window.struct.viewer.programs) == 3
            window.struct.viewer.make_current()
            assert GL.glGetError() == GL.GL_NO_ERROR
            renderer = GL.glGetString(GL.GL_RENDERER)
            print("OpenGL:", GL.glGetString(GL.GL_VERSION), "Renderer:", renderer, flush=True)
            if os.environ.get('NEXUM_GRAPHICS_ACTIVE') == 'software':
                assert b'llvmpipe' in renderer.lower(), 'Packaged software renderer was not used' 
            from nexum.core.molecular_analysis import molecular_surface
            from nexum.ui.session_actions import snapshot,restore
            output=Path(os.environ.get("NEXUM_RENDER_DIR",folder))/"visual-checks";output.mkdir(parents=True,exist_ok=True)
            viewer=window.struct.viewer
            for theme in ("light", "dark"):
                window.appearance.select(theme, persist=False)
                # Allow native GTK style transitions and a complete frame before capture.
                loop = GLib.MainLoop()
                GLib.timeout_add(600, lambda: (loop.quit(), False)[1])
                loop.run()
                assert viewer.dark == (theme == "dark")
                found, background = viewer.get_style_context().lookup_color("window_bg_color")
                if found:
                    assert numpy.allclose(viewer.bg, (background.red, background.green, background.blue))
                viewer.export_png(output / ("vdw-" + theme + ".png"))
                if sys.platform == "win32" and os.environ.get("NEXUM_RENDER_DIR"):
                    from PIL import ImageGrab
                    ImageGrab.grab().save(output / ("application-" + theme + ".png"))
            window.appearance.select("system", persist=False)
            viewer.surface_mesh=molecular_surface(molecule,"vdw",resolution=24)
            viewer.clip_enabled=True;viewer.export_png(output/"surface-cut.png")
            viewer.make_current();assert GL.glGetError()==GL.GL_NO_ERROR
            panel=window.struct.analysis;panel.mode.set_selected(1);panel.selected(1);panel.selected(0)
            assert "Distância" in panel.result.get_text()
            assert viewer.measurement_indices==[1,0]
            viewer.export_png(output/"measurement.png")
            window.analysis.mode.set_selected(1);window.analysis.simulate();window.analysis.analyze()
            assert "Concentração" in window.analysis.report.get_text()
            window.analysis.plot.export(output/"calibration.svg")
            state=snapshot(window);restore(window,state)
            assert window.struct.viewer.surface_mesh is not None
            assert window.struct.viewer.measurement_indices==[1,0]
            assert window.analysis.dataset["origin"]=="Simulado"
            window.analysis.mode.set_selected(3);window.analysis.analyze()
            assert window.analysis.tertiary.data
            from nexum.branding import APP_ID
            assert Gtk.IconTheme.get_for_display(Gdk.Display.get_default()).has_icon(APP_ID)
            assert Gtk.IconTheme.get_for_display(Gdk.Display.get_default()).has_icon("nexum-analysis-symbolic")
            if errors:raise RuntimeError("Falha no fluxo integrado") from errors[0][1]
            print("Medições/superfícies/PNG/SVG/calibração/titulação/sessão/logo: OK",flush=True)

            # The private delivery's laboratory must work in the frozen bundle too.
            with patch('nexum.ui.laboratory.data_dir', return_value=Path(folder)):
                window.open_laboratory()
            lab=window.lab
            from nexum.lab import molecules as lab_molecules, examples
            from nexum.lab.project import Project,write_project,read_project
            built=lab_molecules.chemistry('builder',lab_molecules.chemistry('smiles_graph','CCO'))
            lab.accept_molecule(built['molecule'],built['graph'])
            lab.project=Project(examples.example(0));lab.refresh();lab.use_current()
            lab.to_analysis();assert window.analysis.dataset['x']==lab.project.data['datasets'][0]['x']
            lab.capture_scene();lab.autosave(force=True)
            project_file=output/'laboratorio.nexum7';write_project(project_file,lab.project.data)
            assert len(read_project(project_file)['scenes'])==1
            lab.project=Project(examples.example(3));lab.refresh();lab.fit_design()
            lab.project=Project(examples.example(4));lab.refresh();lab.run_process()
            assert lab.project.data['results'][-1]['payload']['terminal_streams']
            window.close_laboratory()
            print('Laboratório/editor/motor separado/projeto/cena/DOE/processos: OK',flush=True)
            window.struct.influence.set_active(False)
            assert not window.struct.viewer.show_influence
            assert len(window.struct.viewer.scene["influence_pos"]) == 0
        finally:
            window.close_laboratory()
            window.destroy()
            sys.excepthook = original_hook
    print("GTK4/libadwaita/Cairo/NumPy/SciPy/OpenGL/RDKit/gemmi/SQLite: OK")


if __name__ == "__main__":
    main()


