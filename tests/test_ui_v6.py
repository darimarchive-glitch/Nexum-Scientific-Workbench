import unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
class UIV6(unittest.TestCase):
    def test_calculator_sidebar_is_compact_and_collapsible(self):
        s=(ROOT/'nexum/ui/calculators_page.py').read_text(encoding="utf-8")
        self.assertIn('set_size_request(184,-1)',s);self.assertIn('Gtk.Revealer',s);self.assertIn('Gtk.DropDown',s)
    def test_calculator_has_native_plot(self):
        s=(ROOT/'nexum/ui/calculators_page.py').read_text(encoding="utf-8");self.assertIn('ScientificPlot',s)
    def test_experiment_sidebars_are_compact(self):
        s=(ROOT/'nexum/ui/experiments_page.py').read_text(encoding="utf-8");self.assertIn('set_size_request(244, -1)',s);self.assertIn('set_size_request(286, -1)',s)
    def test_tool_scope_badge_is_contextual(self):
        s=(ROOT/'nexum/ui/calculators_page.py').read_text(encoding="utf-8")
        self.assertIn('TOOL_SCOPE',s);self.assertIn('self.validation.set_text(scope)',s)
    def test_home_workspace_exists(self):
        s=(ROOT/'nexum/ui/main_window.py').read_text(encoding="utf-8");self.assertIn('HomePage',s);self.assertIn('"home","Início"',s)
if __name__=='__main__':unittest.main()
