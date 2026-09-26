"""Run with GTK4/libadwaita and a display; never fake toolkit integration."""

import sys
import tempfile
import time
from pathlib import Path
import unittest
import uuid
from unittest.mock import patch

try:
    import gi

    gi.require_version("Gtk", "4.0")
    gi.require_version("Adw", "1")
    gi.require_foreign("cairo")
    from gi.repository import Gtk, Adw, Gdk, GLib

    AVAILABLE = bool(Gtk.init_check() and Gdk.Display.get_default())
except (ImportError, ValueError):
    AVAILABLE = False


@unittest.skipUnless(AVAILABLE, "GTK4/libadwaita com sessão gráfica indisponível")
class LaboratoryGtkTests(unittest.TestCase):
    def setUp(self):
        Adw.init()
        from nexum.ui.main_window import MainWindow

        self.folder = tempfile.TemporaryDirectory()
        self.addCleanup(self.folder.cleanup)
        self.patch = patch(
            "nexum.ui.main_window.data_dir", return_value=Path(self.folder.name)
        )
        self.patch.start()
        self.addCleanup(self.patch.stop)
        self.app = Adw.Application(application_id="io.github.nexum.LaboratoryTest.t" + uuid.uuid4().hex)
        self.app.register(None)
        self.main = MainWindow(self.app)
        with patch("nexum.ui.laboratory.data_dir", return_value=Path(self.folder.name)):
            self.main.open_laboratory()
        self.lab = self.main.lab
        self.errors = []
        self.old_hook = sys.excepthook
        sys.excepthook = lambda *e: self.errors.append(e)

    def tearDown(self):
        sys.excepthook = self.old_hook
        self.main.close_laboratory()
        self.main.destroy()
        self.assertFalse(self.errors, [str(e[1]) for e in self.errors])

    def drain(self):
        # Run the real event loop: polling one event then sleeping can starve
        # idle callbacks behind the macOS native window event source.
        loop = GLib.MainLoop()
        deadline = time.monotonic() + 30
        def check():
            if not self.lab.busy or time.monotonic() >= deadline:
                loop.quit()
                return False
            return True
        GLib.timeout_add(10, check)
        loop.run()
        if self.lab.busy:
            import faulthandler
            faulthandler.dump_traceback()
        self.assertFalse(self.lab.busy)

    def test_all_examples_refresh_and_transfer_analysis(self):
        for i in range(6):
            self.lab.example_select.set_selected(i)
            self.lab.load_example()
        self.lab.example_select.set_selected(0)
        self.lab.load_example()
        self.main.analysis.mode.set_selected(1)
        self.lab.to_analysis()
        self.assertEqual(
            self.main.analysis.dataset["x"], self.lab.project.data["datasets"][0]["x"]
        )

    def test_pending_notes_survive_other_actions_and_undo(self):
        from nexum.ui.lab_widgets import settext

        settext(self.lab.notes, "Não perder estas anotações")
        self.lab.project_title.set_text("Ensaio da bancada")
        self.lab.flush_notes()
        self.lab.add_step()
        self.lab.undo()
        self.assertEqual(self.lab.project.data["notes"], "Não perder estas anotações")

    def test_molecular_builder_and_assignment(self):
        self.lab.example_select.set_selected(0)
        self.lab.load_example()
        self.lab.load_smiles("CCO")
        self.drain()
        self.lab.build_molecule()
        self.drain()
        self.assertEqual(
            self.lab.project.data["molecule"]["metadata"]["formula"], "C2H6O"
        )
        self.lab.add_assignment()
        self.lab.highlight_assignment()
        self.assertEqual(self.main.struct.viewer.selection, {0})

    def test_flow_and_doe_and_process(self):
        self.lab.example_select.set_selected(2)
        self.lab.load_example()
        self.lab.run_flow()
        self.drain()
        self.assertEqual(len(self.lab.project.data["datasets"]), 2)
        self.lab.example_select.set_selected(3)
        self.lab.load_example()
        self.lab.fit_design()
        self.assertAlmostEqual(self.lab.project.data["results"][-1]["payload"]["r2"], 1)
        self.lab.example_select.set_selected(4)
        self.lab.load_example()
        self.lab.run_process()
        self.assertEqual(len(self.lab.project.data["results"]), 1)

    def test_autorecovery_validated_roundtrip(self):
        from nexum.lab.project import read_project

        self.lab.project_title.set_text("Título recuperável")
        self.lab.autosave(force=True)
        data = read_project(
            self.lab.recovery / (self.lab.project.data["id"] + ".nexum7")
        )
        self.assertEqual(data["title"], "Título recuperável")
