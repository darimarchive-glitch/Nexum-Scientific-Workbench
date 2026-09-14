"""Native layer and search regression tests; exercised by desktop CI."""
import unittest
from unittest.mock import Mock
import numpy as np

try:
    import gi
    gi.require_version("Gtk","4.0")
    gi.require_version("Adw","1")
    from gi.repository import Gtk, Adw, Gdk
    AVAILABLE=bool(Gtk.init_check() and Gdk.Display.get_default())
except (ImportError,ValueError):
    AVAILABLE=False

@unittest.skipUnless(AVAILABLE,"GTK4/libadwaita e display não disponíveis")
class ViewerLayers(unittest.TestCase):
    def setUp(self):
        Adw.init()
        from nexum.ui.gl_viewer import GLMoleculeView
        from nexum.core.structures import Atom,Molecule
        self.view=GLMoleculeView()
        self.view.set_molecule(Molecule("Exemplo",[Atom("C",0,0,0),Atom("O",1.4,0,0),Atom("H",-1,0,0)],[(0,1,1),(0,2,1)]))

    def test_layer_preserves_base_geometry_and_uses_vdw_radii(self):
        from nexum.core.structures import vdw_radius
        base=self.view.scene["point_pos"].copy()
        self.assertFalse(self.view.show_influence)
        self.view.configure(show_influence=True,influence_opacity=.35)
        np.testing.assert_array_equal(base,self.view.scene["point_pos"])
        np.testing.assert_allclose(self.view.scene["influence_rad"],[vdw_radius("C"),vdw_radius("O")])
        self.assertEqual(self.view.influence_opacity,.35)
        self.view.configure(show_hydrogens=True)
        self.assertEqual(len(self.view.scene["influence_pos"]),3)
        self.view.configure(show_influence=False)
        self.assertEqual(len(self.view.scene["influence_pos"]),0)

    def test_layer_respects_chains_and_rejects_nan_opacity(self):
        self.view.configure(show_influence=True,visible_chains={"missing"})
        self.assertEqual(len(self.view.scene["influence_pos"]),0)
        with self.assertRaises(ValueError):self.view.configure(influence_opacity=float("nan"))

    def test_stale_search_does_not_replace_new_results(self):
        from nexum.ui.structures_page import StructurePage
        from nexum.core.structures import StructureSuggestion
        page=StructurePage(Mock())
        page.search_generation=2
        page._show_results([StructureSuggestion("PubChem","962","Água")],2)
        first=page.results.get_first_child()
        self.assertEqual(first.get_title(),"Água")
        self.assertEqual(first.get_subtitle(),"Molécula")
        page._show_results([StructureSuggestion("PubChem","702","Etanol")],1)
        self.assertIs(page.results.get_first_child(),first)
