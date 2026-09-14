import math
import unittest
import numpy as np
from nexum.core.structures import Atom,Molecule
from nexum.core.molecular_analysis import measurement,molecular_surface,parse_cube,isosurface,molecule_from_dict
from nexum.core.data_analysis import read_csv,analyze_spectrum,calibration,fit_kinetics,kinetic_curve,polyprotic_titration

class AnalysisWorkbench(unittest.TestCase):
    def test_geometry_and_degeneracy(self):
        m=Molecule("test",[Atom("C",0,0,0),Atom("C",1,0,0),Atom("C",1,1,0),Atom("C",1,1,1)],[])
        self.assertAlmostEqual(measurement(m,[0,1])[1],1)
        self.assertAlmostEqual(measurement(m,[0,1,2])[1],90)
        self.assertAlmostEqual(abs(measurement(m,[0,1,2,3])[1]),90)
        with self.assertRaises(ValueError):measurement(m,[0,0])
        m.atoms[2]=Atom("C",2,0,0)
        with self.assertRaises(ValueError):measurement(m,[0,1,2,3])

    def test_surface_radius_and_probe(self):
        m=Molecule("carbon",[Atom("C",0,0,0)],[])
        for mode,expected in [("vdw",1.7),("sas",3.1)]:
            mesh=molecular_surface(m,mode,resolution=32)
            radii=np.linalg.norm(mesh["vertices"],axis=1)
            self.assertLess(abs(np.median(radii)-expected),.08)
            self.assertTrue(np.isfinite(mesh["normals"]).all())
        ses=molecular_surface(m,"ses",resolution=48)
        self.assertLess(abs(np.median(np.linalg.norm(ses["vertices"],axis=1))-1.7),.35)

    def test_cube_units_and_validation(self):
        cube="title\nmethod\n1 0 0 0\n2 1 0 0\n2 0 1 0\n2 0 0 1\n6 0 1 0 0\n0 1 2 3 4 5 6 7"
        parsed=parse_cube(cube)
        self.assertAlmostEqual(parsed["molecule"].atoms[0].x,.529177210903)
        self.assertEqual(parsed["values"][1,0,0],4)
        with self.assertRaises(ValueError):parse_cube(cube+" 8")
        with self.assertRaises(ValueError):isosurface(np.ones((3,3,3)),[0,0,0],np.eye(3),1)

    def test_csv_baseline_and_exact_integral(self):
        x,y=read_csv("volume;sinal\n0;1,0\n1;3,0\n2;5,0")
        r=analyze_spectrum(x,y,lower=.25,upper=1.75)
        self.assertAlmostEqual(r["area"],4.5)
        self.assertTrue(np.allclose(analyze_spectrum(x,y,"linear")["corrected"],0))
        with self.assertRaises(ValueError):read_csv("0,1\n0,2\n1,3")
        with self.assertRaises(ValueError):analyze_spectrum(x,y,lower=-1)

    def test_calibration_and_kinetic_model(self):
        x=np.arange(6.);r=calibration(x,2*x+1,7)
        self.assertAlmostEqual(r["estimate"],3)
        self.assertLess(r["u"],1e-12)
        self.assertTrue(calibration(x,2*x+1,20)["extrapolation"])
        t=np.linspace(0,20,50);c=kinetic_curve(t,2,.15,1)
        fit=fit_kinetics(t,c)[0]
        self.assertEqual(fit["order"],1)
        self.assertAlmostEqual(fit["k"],.15,places=6)

    def test_polyprotic_charge_balance(self):
        v,p=polyprotic_titration((4.76,),max_ml=50)
        # Half-equivalence agrees with pKa up to finite acid dissociation.
        self.assertLess(abs(np.interp(12.5,v,p)-4.76),.002)
        self.assertTrue(np.all(np.diff(p)>0))
        _,triprotic=polyprotic_titration()
        self.assertTrue(np.isfinite(triprotic).all())

    def test_session_roundtrip(self):
        import tempfile
        from pathlib import Path
        from nexum.core.data_analysis import write_session,read_session
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/"sessão.nexum"
            write_session(p,{"array":np.array([1,2]),"note":"água"})
            self.assertEqual(read_session(p)["note"],"água")
            with self.assertRaises(ValueError):write_session(p,{"nan":float("nan")})
            self.assertEqual(read_session(p)["array"],[1,2])
