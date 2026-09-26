import math, unittest, tempfile, json
from pathlib import Path
from unittest.mock import patch
from urllib.error import HTTPError

from nexum.core.constants import R_J, F, R_L_ATM
from nexum.core.calculators import CALCS
from nexum.core.chemistry import electron_configuration
from nexum.core.acidbase import buffer_state, titration_state, hydrogen_strong_acid
from nexum.core.structures import Molecule,Atom,pubchem,suggestions,StructureSuggestion

class ScientificAuditV6(unittest.TestCase):
    # CODATA 2022 constants used by the workbench.
    def test_codata_constants(self):
        self.assertEqual(R_J, 8.31446261815324)
        self.assertEqual(F, 96485.33212)
        self.assertAlmostEqual(R_L_ATM, 0.082057366080960, places=14)

    def test_ultradilute_strong_acid_includes_water(self):
        h=hydrogen_strong_acid(1e-8)
        self.assertAlmostEqual(-math.log10(h), 6.978294313542888, places=10)
        self.assertGreater(h,1e-7)  # acid shifts pure-water H+ upward

    def test_exact_buffer_equal_formal_concentrations(self):
        st=buffer_state(.1,.1,10**-4.76)
        # HH is close but not used as the solver; full charge balance remains exactly satisfied.
        residual=st['h_m'] + .1 - st['a_minus_m'] - st['oh_m']
        self.assertAlmostEqual(residual,0.0,places=13)
        self.assertLess(abs(st['ph']-4.76),3e-4)

    def test_weak_titration_charge_balance_at_half_equivalence(self):
        st=titration_state(mode='weak-strong',acid_c=.1,acid_v_ml=25,base_c=.1,base_added_ml=12.5,ka=10**-4.76)
        residual=st['h_m']+st['spectator_cation_m']-st['a_minus_m']-st['oh_m']
        self.assertAlmostEqual(residual,0.0,places=12)
        self.assertLess(abs(st['ph']-4.76),1e-3)

    def test_titration_calculator_returns_curve(self):
        r=CALCS['titration']({'mode':'ácido fraco','acid_m':'0.1','acid_ml':'25','base_m':'0.1','base_ml':'12.5','pka':'4.76'})
        self.assertIn('plot',r.data);self.assertGreaterEqual(len(r.data['plot']['series'][0]['points']),200)
        self.assertEqual(r.data['plot']['markers'][0]['label'],'equivalência')

    def test_speciation_at_pka(self):
        r=CALCS['speciation']({'pka':'4.76','ph':'4.76','ph_min':'0','ph_max':'14'})
        self.assertAlmostEqual(r.data['alpha_ha'],.5,places=12);self.assertAlmostEqual(r.data['alpha_a'],.5,places=12)

    def test_arrhenius_identity(self):
        r=CALCS['arrhenius']({'k1':'2.5','t1_k':'300','t2_k':'300','ea_kjmol':'50'})
        self.assertAlmostEqual(float(r.value.split()[0]),2.5,places=12)

    def test_integrated_kinetics_half_lives(self):
        for order,c0,k,t_half in [('0',2,.1,10),('1',1,math.log(2)/10,10),('2',2,.05,10)]:
            r=CALCS['kinetics']({'order':order,'c0':str(c0),'k':str(k),'time_s':str(t_half),'duration_s':'20'})
            self.assertAlmostEqual(float(r.value.split()[0]),c0/2,places=8)

    def test_transition_metal_cation_configuration(self):
        self.assertTrue(electron_configuration(26,2).endswith('3d6'))
        self.assertNotIn('4s',electron_configuration(26,2))
        self.assertTrue(electron_configuration(29,1).endswith('3d10'))

    def test_faraday_efficiency_range(self):
        with self.assertRaises(ValueError):
            CALCS['faraday']({'current_a':'1','time_s':'10','z':'2','molar_mass':'63.546','efficiency_percent':'120'})

    def test_brix_handles_dilution_direction(self):
        r=CALCS['brix']({'solution_mass_kg':'100','brix':'20','target_brix':'10'})
        self.assertIn('adicionar',r.details.lower());self.assertAlmostEqual(float(r.value.split()[0]),100,places=10)

    def test_regression_reports_uncertainty_and_plot(self):
        r=CALCS['regression']({'points':'0,0.01;1,1.02;2,2.01;3,3.03'})
        self.assertGreater(r.data['r2'],.999);self.assertIsNotNone(r.data['se_slope']);self.assertIn('plot',r.data)

    def test_pubchem_404_falls_back_to_local_conformer(self):
        calls=[]
        props={"PropertyTable":{"Properties":[{"CID":999,"Title":"Demo","MolecularFormula":"C","IsomericSMILES":"C"}]}}
        def fake_get(url,*args,**kwargs):
            calls.append(url)
            if '/property/' in url:return json.dumps(props)
            if '/SDF?record_type=3d' in url:raise HTTPError(url,404,'not found',None,None)
            raise AssertionError(url)
        fake=Molecule('Demo',[Atom('C',0,0,0)],[],source='PubChem + RDKit',identifier='999')
        with tempfile.TemporaryDirectory() as td, patch('nexum.core.structures._get',side_effect=fake_get), patch('nexum.core.structures._rdkit_conformer_from_smiles',return_value=fake) as gen:
            m=pubchem('999',Path(td))
        self.assertEqual(m.identifier,'999');gen.assert_called_once()


    def test_pubchem_2d_graph_fallback_when_smiles_missing(self):
        props={"PropertyTable":{"Properties":[{"CID":998,"Title":"Demo2","MolecularFormula":"NaCl"}]}}
        calls=[]
        def fake_get(url,*args,**kwargs):
            calls.append(url)
            if '/property/' in url:return json.dumps(props)
            if '/SDF?record_type=3d' in url:raise HTTPError(url,404,'not found',None,None)
            if '/SDF?record_type=2d' in url:return 'mock 2d mol block'
            raise AssertionError(url)
        fake=Molecule('Demo2',[Atom('Na',0,0,0),Atom('Cl',2,0,0)],[],source='PubChem + RDKit',identifier='998')
        with tempfile.TemporaryDirectory() as td, patch('nexum.core.structures._get',side_effect=fake_get), patch('nexum.core.structures._rdkit_conformer_from_molblock',return_value=fake) as gen:
            m=pubchem('998',Path(td))
        self.assertEqual(m.identifier,'998');gen.assert_called_once();self.assertTrue(any('record_type=2d' in x for x in calls))

    def test_macromolecule_hint_prioritizes_rcsb(self):
        r=[StructureSuggestion('RCSB PDB','4HHB','Hemoglobin','macro')]
        p=[StructureSuggestion('PubChem','1','Hemoglobin-like','small')]
        with patch('nexum.core.structures.rcsb_suggestions',return_value=r), patch('nexum.core.structures.pubchem_suggestions',return_value=p):
            out=suggestions('hemoglobina','Todos',4)
        self.assertEqual(out[0].source,'RCSB PDB')

if __name__=='__main__':unittest.main()
