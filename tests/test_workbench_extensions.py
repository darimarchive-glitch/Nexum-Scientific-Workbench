import math
import unittest
from unittest.mock import patch
from nexum.core.calculators import CALCS
from nexum.core.registry import TOOLS
from nexum.core.titration_analysis import analyze_curve
from nexum.core.structures import resolve_pubchem_cid, suggestions, pubchem_suggestions, _pubchem_properties
from nexum.core.molecule_names import local_candidates, display_name
from nexum.core.experiment_session import ExperimentSession
from nexum.core.process_models import cstr_startup


def defaults(tid):
    return {f['key']: f['default'] for t in TOOLS if t[0]==tid for f in t[4]}


class ExtensionTests(unittest.TestCase):
    def test_portuguese_water_resolves_without_network(self):
        with patch('nexum.core.structures._get',side_effect=AssertionError('Network forbidden')):
            for name in ('água','AGUA',' water ','H₂O','H2O','7732-18-5','962'):
                self.assertEqual(resolve_pubchem_cid(name),'962')
                self.assertEqual(suggestions(name)[0].title,'Água')

    def test_isomeric_formula_is_not_an_exact_name(self):
        from nexum.core.molecule_names import exact_compound
        self.assertIsNone(exact_compound("C2H6O"))
        self.assertIsNone(exact_compound("C12H22O11"))

    def test_sucrose_identifier(self):
        self.assertEqual(resolve_pubchem_cid('sacarose'),'5988')
        self.assertEqual(resolve_pubchem_cid('sucrose'),'5988')

    def test_xdg_paths_inside_flatpak(self):
        import os
        from pathlib import Path
        from nexum import paths
        with patch.object(paths.sys,'platform','linux'),patch.dict(os.environ,{'XDG_DATA_HOME':'/tmp/flatpak-data','XDG_CACHE_HOME':'/tmp/flatpak-cache'}):
            self.assertEqual(paths.data_dir(),Path('/tmp/flatpak-data/nexum-lab'))
            self.assertEqual(paths.cache_dir(),Path('/tmp/flatpak-cache/nexum-lab'))

    def test_fuzzy_results_are_suggestions_only(self):
        self.assertEqual(local_candidates('agau'),[])  # Not an edit-distance-one guess.
        self.assertEqual(local_candidates('aguua')[0][0],'962')
        with patch('nexum.core.structures._get',side_effect=OSError('offline')):
            self.assertEqual(pubchem_suggestions('aguua')[0].identifier,'962')
            with self.assertRaises(OSError):resolve_pubchem_cid('aguua')

    def test_unknown_names_preserve_identifier(self):
        self.assertEqual(display_name('999999','Unknown','C9H9'),'Composto C9H9')
        self.assertIn('999999',display_name('999999'))

    def test_current_smiles_properties_keep_stereochemistry(self):
        with patch('nexum.core.structures._get',return_value='{"PropertyTable":{"Properties":[{"SMILES":"C[C@H](O)F","ConnectivitySMILES":"CC(O)F"}]}}'):
            self.assertEqual(_pubchem_properties('1')['IsomericSMILES'],'C[C@H](O)F')

    def test_nonuniform_quadratic_differences(self):
        result=analyze_curve([(x,x*x) for x in (0,1,2,4,7,11)])
        for x,y in result['first_derivative']:self.assertAlmostEqual(y,2*x)
        for x,y in result['second_derivative']:self.assertAlmostEqual(y,2)
        self.assertIsNone(result['estimated_equivalence_ml'])

    def test_symmetric_increasing_and_decreasing_curves(self):
        for direction in (-1,1):
            result=analyze_curve([(i/10,7+direction*5*math.tanh(i/10-5)) for i in range(101)])
            self.assertAlmostEqual(result['estimated_equivalence_ml'],5,delta=.02)

    def test_invalid_titration_data(self):
        for points in ([(0,1)]*5,[(x,1) for x in (0,2,1,3,4)],[(0,1),(1,2),(2,float('nan')),(3,4),(4,5)]):
            with self.assertRaises(ValueError):analyze_curve(points)
        self.assertIsNone(analyze_curve([(x,7) for x in range(6)])['estimated_equivalence_ml'])

    def test_titration_plots_have_separate_units(self):
        data=CALCS['titration'](defaults('titration')).data
        self.assertEqual([p['ylabel'] for p in data['plots']],['pH','pH/mL','pH/mL²'])
        self.assertAlmostEqual(data['estimated_equivalence_ml'],25,delta=.3)

    def test_combustion_conserves_atoms(self):
        for conversion in (0,72,100):
            data=CALCS['combustion']({**defaults('combustion'),'conversion':str(conversion)}).data
            out=data['outlet_kmol_h']; fuel=data['fuel_kmol_h']; left=out['combustível não convertido']
            self.assertAlmostEqual(out['CO2']+8*left,8*fuel)
            self.assertAlmostEqual(2*out['H2O']+18*left,18*fuel)
            self.assertAlmostEqual(2*out['CO2']+out['H2O']+2*out['O2'],2*.21*data['air_kmol_h'])

    def test_reactors_analytical_values(self):
        data=CALCS['reactor'](defaults('reactor')).data
        self.assertAlmostEqual(data['cstr_l'],80)
        self.assertAlmostEqual(data['pfr_l'],20*math.log(5))
        with self.assertRaises(ValueError):CALCS['reactor']({**defaults('reactor'),'conversion':'100'})

    def test_spectral_reference(self):
        data=CALCS['spectral_units'](defaults('spectral_units')).data
        self.assertEqual(data['wavenumber_cm'],20000)
        data=CALCS['mass_spectrum']({'reference':'100','observed':'100.001','width':'0.001'}).data
        self.assertAlmostEqual(data['error_ppm'],10)
        self.assertAlmostEqual(data['resolving_power'],100001)

    def test_cstr_initial_and_stationary_states(self):
        args=dict(volume_l=10,flow_l_s=1,feed_m=1,initial_m=0,k_s=.1)
        self.assertEqual(cstr_startup(**args,time_s=0)['concentration_m'],0)
        self.assertAlmostEqual(cstr_startup(**args,time_s=1000)['concentration_m'],.5)
        for eid in ('cstr','spectro_kinetics'):
            session=ExperimentSession(eid); self.assertTrue(session.reference_curve)
            session.seek(session.duration);self.assertTrue(session.complete)
            self.assertTrue(session.metrics);self.assertTrue(session.guide)

    def test_absorbance_halves_at_chemical_half_life(self):
        session=ExperimentSession('spectro_kinetics',{'k_s':math.log(2)/10})
        initial=session.state['absorbance'];session.seek(10)
        self.assertAlmostEqual(session.state['absorbance'],initial/2)

    def test_model_boundaries(self):
        for eid,key in [('cstr','volume_l'),('spectro_kinetics','path_length_cm')]:
            with self.assertRaises(ValueError):ExperimentSession(eid,{key:0})
        for tid,key in [('combustion','feed_kg_h'),('reactor','k'),('spectral_units','wavelength_nm'),('mass_spectrum','width')]:
            for value in ('nan','inf','-1','0'):
                with self.assertRaises(ValueError):CALCS[tid]({**defaults(tid),key:value})
