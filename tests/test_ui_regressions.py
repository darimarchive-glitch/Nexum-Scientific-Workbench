from pathlib import Path
import unittest

ROOT=Path(__file__).resolve().parents[1]

class UIRegressionTests(unittest.TestCase):
    def test_calculator_workspace_expands_instead_of_collapsing(self):
        src=(ROOT/'nexum/ui/calculators_page.py').read_text()
        self.assertIn('self.paned.set_vexpand(True)',src)
        self.assertIn('sw.set_vexpand(True)',src)
    def test_glarea_requests_real_depth_buffer(self):
        src=(ROOT/'nexum/ui/gl_viewer.py').read_text()
        self.assertIn('self.set_has_depth_buffer(True)',src)
        self.assertIn('gl_FragDepth',src)
        self.assertIn('_cylinder_mesh',src)
    def test_experiments_have_persistent_selector(self):
        src=(ROOT/'nexum/ui/experiments_page.py').read_text()
        self.assertIn('self.exp_list = Gtk.ListBox()',src)
        self.assertIn('_experiment_row_selected',src)

if __name__=='__main__': unittest.main()
