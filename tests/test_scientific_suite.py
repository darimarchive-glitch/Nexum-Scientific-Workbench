import math, unittest
from nexum.core.registry import TOOLS
from nexum.core.calculators import CALCS
from nexum.core.chemistry import molar_mass,balance_equation,parse_formula
from nexum.core.constants import R_J,F
from nexum.core.periodic import ELEMENTS
from nexum.core.structures import parse_sdf,parse_pdb,parse_mmcif,resolve_pubchem_cid,pubchem
from nexum.core.search import match
class ScientificSuite(unittest.TestCase):
    def test_all_default_cases_execute(self):
        self.assertEqual(len(TOOLS),35)
        for t in TOOLS:
            with self.subTest(tool=t[0]):
                d={f['key']:f['default'] for f in t[4]}; r=CALCS[t[0]](d); self.assertTrue(r.value); self.assertTrue(r.details)
    def test_periodic_table_complete(self): self.assertEqual(len(ELEMENTS),118)
    def test_water_molar_mass(self): self.assertAlmostEqual(molar_mass('H2O'),18.015,places=3)
    def test_cuso4_pentahydrate(self): self.assertAlmostEqual(molar_mass('CuSO4·5H2O'),249.677,places=3)
    def test_balance_propane(self): self.assertEqual(balance_equation('C3H8 + O2 -> CO2 + H2O')[0],'C3H8 + 5 O2 -> 3 CO2 + 4 H2O')
    def test_calorimetry_reference(self):
        r=CALCS['calorimetry']({'mass_g':'100','cp_j_gk':'4.184','ti_c':'20','tf_c':'45'}); self.assertAlmostEqual(float(r.value.split()[0]),10460,places=6)
    def test_ideal_gas_standard(self):
        r=CALCS['ideal']({'p_atm':'','v_l':'22.41396954','n_mol':'1','t_k':'273.15'}); self.assertAlmostEqual(float(r.value.split()[0]),1.0,places=7)
    def test_daniell_standard(self):
        r=CALCS['cell']({'e_cathode':'0.34','e_anode':'-0.76','n_e':'2','q':'1','temperature_k':'298.15'}); self.assertAlmostEqual(float(r.value.split()[0]),1.1,places=10)
    def test_titration_equivalence(self):
        r=CALCS['titration']({'mode':'ácido forte','acid_m':'0.1','acid_ml':'25','base_m':'0.1','base_ml':'25','pka':'4.76'}); self.assertAlmostEqual(float(r.value),7,places=10)
    def test_bohr_balmer_alpha(self):
        r=CALCS['bohr']({'n_i':'3','n_f':'2','z':'1'}); self.assertTrue(655 < float(r.value.split()[0]) < 657)
    def test_bragg(self):
        r=CALCS['bragg']({'wavelength_nm':'0.15406','theta_deg':'30','order':'1'}); self.assertAlmostEqual(float(r.value.split()[0]),0.15406,places=6)
    def test_decay_half_life(self):
        r=CALCS['decay']({'initial':'100','time':'10','half_life':'10'}); self.assertAlmostEqual(float(r.value),50,places=10)
    def test_fuzzy_multilingual_search(self):
        self.assertTrue(match('equillibrio','constants','Conversão Kc Kp','Equilíbrio','Equilíbrio e pH'))
        self.assertTrue(match('limiting reagent','stoichiometry','Reagente produto','Estequiometria','Estequiometria'))
        self.assertTrue(match('curva titulacion','titration','Curva de titulação','pH','Equilíbrio e pH'))
    def test_sdf_parser(self):
        sdf='''water\n  nexum\n\n  3  2  0  0  0  0            999 V2000\n    0.0000    0.0000    0.0000 O   0  0  0  0  0  0  0  0  0  0  0  0\n    0.9572    0.0000    0.0000 H   0  0  0  0  0  0  0  0  0  0  0  0\n   -0.2390    0.9270    0.0000 H   0  0  0  0  0  0  0  0  0  0  0  0\n  1  2  1  0  0  0  0\n  1  3  1  0  0  0  0\nM  END\n'''
        m=parse_sdf(sdf,'water'); self.assertEqual(len(m.atoms),3);self.assertEqual(len(m.bonds),2)
    def test_pdb_parser(self):
        pdb='''ATOM      1  N   GLY A   1      11.104  13.207   2.100  1.00 20.00           N  \nATOM      2  C   GLY A   1      12.000  13.500   2.100  1.00 20.00           C  \nCONECT    1    2\n'''; m=parse_pdb(pdb,'x');self.assertEqual(len(m.atoms),2);self.assertEqual(len(m.bonds),1)
    def test_pubchem_name_resolves_to_canonical_cid(self):
        from unittest.mock import patch
        with patch('nexum.core.structures._get', return_value='{"IdentifierList":{"CID":[2244]}}'):
            self.assertEqual(resolve_pubchem_cid('aspirin'),'2244')
        self.assertEqual(resolve_pubchem_cid('2244'),'2244')

    def test_pubchem_3d_uses_cid_endpoint(self):
        from unittest.mock import patch
        from pathlib import Path
        import tempfile, json
        sdf=("aspirin\n  nexum\n\n  2  1  0  0  0  0            999 V2000\n"
             "    0.0000    0.0000    0.1000 C   0  0  0  0  0  0  0  0  0  0  0  0\n"
             "    1.2000    0.0000   -0.1000 O   0  0  0  0  0  0  0  0  0  0  0  0\n"
             "  1  2  1  0  0  0  0\nM  END\n")
        calls=[]
        def fake_get(url,*args,**kwargs):
            calls.append(url)
            if '/name/aspirin/cids/JSON' in url:return '{"IdentifierList":{"CID":[2244]}}'
            if '/property/' in url:return json.dumps({"PropertyTable":{"Properties":[{"CID":2244,"Title":"Aspirin","MolecularFormula":"C9H8O4","IsomericSMILES":"CC(=O)OC1=CC=CC=C1C(=O)O"}]}})
            if '/cid/2244/SDF?record_type=3d' in url:return sdf
            raise AssertionError(url)
        with tempfile.TemporaryDirectory() as td, patch('nexum.core.structures._get', side_effect=fake_get):
            m=pubchem('aspirin',Path(td))
        self.assertEqual(m.identifier,'2244'); self.assertEqual(len(m.atoms),2)
        self.assertTrue(any('/compound/cid/2244/SDF?record_type=3d' in u for u in calls))

    def test_mmcif_macromolecule_parser_deduplicates_altloc(self):
        cif="""data_demo
_entry.id demo
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
_atom_site.pdbx_PDB_ins_code
_atom_site.Cartn_x
_atom_site.Cartn_y
_atom_site.Cartn_z
_atom_site.occupancy
_atom_site.B_iso_or_equiv
_atom_site.pdbx_formal_charge
_atom_site.auth_seq_id
_atom_site.auth_comp_id
_atom_site.auth_asym_id
_atom_site.auth_atom_id
_atom_site.pdbx_PDB_model_num
ATOM 1 C CA . ALA A 1 1 ? 0 0 0 1 10 ? 1 ALA A CA 1
ATOM 2 N N . ALA A 1 1 ? 1 0 0 1 10 ? 1 ALA A N 1
ATOM 3 C CA B ALA A 1 1 ? 0.1 0 0 0.5 10 ? 1 ALA A CA 1
"""
        m=parse_mmcif(cif,'demo')
        self.assertEqual(len(m.atoms),2)
        self.assertEqual(m.metadata.get('polymer_backbone_atoms'),1)

if __name__=='__main__': unittest.main()
