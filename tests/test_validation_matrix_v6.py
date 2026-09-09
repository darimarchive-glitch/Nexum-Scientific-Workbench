import math
import unittest
import numpy as np

from nexum.core.calculators import CALCS
from nexum.core.acidbase import hydrogen_weak_acid, buffer_state, titration_state
from nexum.core.constants import R_J, F, R_L_ATM
from nexum.core.chemistry import molar_mass
from nexum.core.registry import TOOLS, TOOL_SCOPE
from nexum.core.experiments import haber_equilibrium, haber_thermodynamics


def _value(result):
    return float(result.value.split()[0])


def _positive_real_root(coeffs):
    roots=np.roots(coeffs)
    vals=[float(r.real) for r in roots if abs(float(r.imag))<1e-9 and float(r.real)>0]
    if not vals:
        raise AssertionError(f'No positive physical root: {roots}')
    return min(vals)


class ValidationMatrixV6(unittest.TestCase):
    def test_every_tool_has_declared_scope(self):
        self.assertEqual(len(TOOLS),35)
        self.assertEqual(set(t[0] for t in TOOLS),set(TOOL_SCOPE))

    def test_molar_mass_simple_reference_set(self):
        refs={'H2O':18.015,'CO2':44.009,'NaCl':58.44,'C6H12O6':180.156}
        for formula,expected in refs.items():
            self.assertAlmostEqual(molar_mass(formula),expected,delta=0.012)

    def test_stoichiometry_water_reference(self):
        r=CALCS['stoichiometry']({'equation':'H2 + O2 -> H2O','reactant':'H2','reactant_mass_g':'2.016','product':'H2O','yield_percent':'100'})
        self.assertAlmostEqual(_value(r),18.015,delta=0.02)

    def test_empirical_formula_glucose_like(self):
        r=CALCS['empirical']({'composition':'C:40,H:6.71,O:53.29','experimental_molar_mass':'180.156'})
        self.assertEqual(r.value,'CH2O')
        self.assertIn('C6H12O6',r.details)

    def test_hess_linear_reversal(self):
        r=CALCS['hess']({'steps':'2:-100;-1:-50'})
        self.assertAlmostEqual(_value(r),-150.0,places=12)

    def test_gibbs_k_identity(self):
        r=CALCS['reaction']({'delta_h_kj':'0','delta_s_jk':'0','temperature_k':'298.15'})
        self.assertAlmostEqual(_value(r),0.0,places=12)
        self.assertAlmostEqual(r.data['log10K'],0.0,places=12)
        self.assertIn('plot',r.data)

    def test_clausius_identity_and_plot(self):
        r=CALCS['clapeyron']({'p1':'1.25','t1':'350','t2':'350','hvap_jmol':'40000'})
        self.assertAlmostEqual(_value(r),1.25,places=12)
        self.assertIn('plot',r.data)

    def test_arrhenius_ratio_matches_independent_formula(self):
        inp={'k1':'0.5','t1_k':'300','t2_k':'330','ea_kjmol':'45'}
        r=CALCS['arrhenius'](inp)
        expected=.5*math.exp(-45000/R_J*(1/330-1/300))
        self.assertAlmostEqual(_value(r),expected,delta=expected*2e-9)
        self.assertIn('plot',r.data)

    def test_real_gas_vdw_reference(self):
        n,V,T,a,b=1.0,1.0,300.0,3.592,0.04267
        r=CALCS['real']({'model':'van der Waals','n_mol':str(n),'v_l':str(V),'t_k':str(T),'a':str(a),'b':str(b)})
        expected=n*0.08314462618*T/(V-n*b)-a*(n/V)**2
        self.assertAlmostEqual(_value(r),expected,delta=abs(expected)*2e-9)
        self.assertIn('plot',r.data)

    def test_concentration_mass_balance(self):
        r=CALCS['concentration']({'solute_mass_g':'5.844','molar_mass_gmol':'58.44','volume_l':'0.5'})
        self.assertAlmostEqual(_value(r),0.2,places=10)
        self.assertAlmostEqual(r.data['g_L'],11.688,places=10)

    def test_dilution_solute_is_conserved(self):
        r=CALCS['dilution']({'c1':'1.2','v1_ml':'25','c2':'0.15'})
        v2=_value(r)
        self.assertAlmostEqual(1.2*25,0.15*v2,places=9)

    def test_colligative_osmotic_pressure_reference(self):
        r=CALCS['colligative']({'mode':'osmose','i':'2','molality':'0','kb':'0.512','kf':'1.86','molarity':'0.05','temperature_k':'298.15'})
        self.assertAlmostEqual(_value(r),2*.05*R_L_ATM*298.15,delta=2e-8)

    def test_kc_kp_roundtrip(self):
        base={'k':'7.3','delta_n':'-2','temperature_k':'450'}
        kp=CALCS['constants']({**base,'direction':'Kc -> Kp'})
        kc=CALCS['constants']({'k':kp.value,'delta_n':'-2','temperature_k':'450','direction':'Kp -> Kc'})
        self.assertAlmostEqual(_value(kc),7.3,delta=1e-8)

    def test_ice_satisfies_equilibrium_expression(self):
        r=CALCS['ice']({'kc':'4','a0':'1','b0':'1','c0':'0'})
        x=_value(r); q=x/((1-x)*(1-x))
        self.assertAlmostEqual(q,4.0,delta=2e-8)

    def test_weak_acid_matches_independent_cubic(self):
        c=0.013; ka=1.8e-5; kw=1e-14
        h=hydrogen_weak_acid(c,ka,kw)
        href=_positive_real_root([1,ka,-(c*ka+kw),-kw*ka])
        self.assertAlmostEqual(h,href,delta=href*2e-9)

    def test_buffer_matches_independent_charge_balance_polynomial(self):
        ca,cb,ka,kw=.08,.12,10**-4.76,1e-14; ct=ca+cb
        st=buffer_state(ca,cb,ka,kw)
        # (h^2 + cb*h - kw)(Ka+h)-ct*Ka*h = 0
        coeff=[1,ka+cb,cb*ka-kw-ct*ka,-kw*ka]
        href=_positive_real_root(coeff)
        self.assertAlmostEqual(st['h_m'],href,delta=href*3e-8)

    def test_weak_titration_matches_independent_polynomial(self):
        st=titration_state(mode='weak-strong',acid_c=.1,acid_v_ml=25,base_c=.1,base_added_ml=18,ka=10**-4.76)
        ct=st['total_acid_m']; cm=st['spectator_cation_m']; ka=10**-4.76; kw=1e-14
        coeff=[1,ka+cm,cm*ka-kw-ct*ka,-kw*ka]
        href=_positive_real_root(coeff)
        self.assertAlmostEqual(st['h_m'],href,delta=href*3e-8)

    def test_nernst_slope_per_decade(self):
        base={'e_cathode':'0.34','e_anode':'-0.76','n_e':'2','temperature_k':'298.15'}
        e1=_value(CALCS['cell']({**base,'q':'1'})); e10=_value(CALCS['cell']({**base,'q':'10'}))
        expected=R_J*298.15/(2*F)*math.log(10)
        self.assertAlmostEqual(e1-e10,expected,delta=2e-9)

    def test_faraday_charge_mass_relation(self):
        r=CALCS['faraday']({'current_a':str(F),'time_s':'1','z':'1','molar_mass':'107.8682','efficiency_percent':'100'})
        self.assertAlmostEqual(_value(r),107.8682,delta=2e-7)

    def test_photon_500nm_independent(self):
        r=CALCS['photon']({'wavelength_nm':'500'})
        expected=6.62607015e-34*299792458/(500e-9)/1.602176634e-19
        self.assertAlmostEqual(_value(r),expected,delta=2e-9)

    def test_beer_plot_and_identity(self):
        r=CALCS['beer']({'epsilon':'150','path_cm':'1.2','concentration':'0.004'})
        self.assertAlmostEqual(_value(r),.72,places=12)
        self.assertAlmostEqual(r.data['transmittance'],10**-.72,places=13)
        self.assertIn('plot',r.data)

    def test_lattice_sc_bcc_fcc_atom_counts(self):
        for typ,z in [('sc',1),('bcc',2),('fcc',4)]:
            r=CALCS['lattice']({'type':typ,'a_angstrom':'4','molar_mass':'50'})
            expected=z*50/(6.02214076e23*(4e-8)**3)
            self.assertAlmostEqual(_value(r),expected,delta=expected*2e-9)

    def test_decay_has_graph_and_half_life(self):
        r=CALCS['decay']({'initial':'80','time':'12','half_life':'12'})
        self.assertAlmostEqual(_value(r),40,places=12)
        self.assertIn('plot',r.data)

    def test_haber_equilibrium_q_equals_k(self):
        for T,P in [(400,10),(600,100),(800,200),(1000,300)]:
            st=haber_equilibrium(n_n2=1,n_h2=3,n_nh3=.02,temp_k=T,pressure_bar=P)
            self.assertAlmostEqual(st['ln_q'],st['ln_kp'],delta=2e-8)

    def test_haber_temperature_trend_is_thermodynamically_consistent(self):
        # Exothermic reaction: within this Shomate/ideal-gas model Kp falls strongly with T.
        self.assertGreater(haber_thermodynamics(400)['kp'],haber_thermodynamics(800)['kp'])

    def test_new_plot_payloads_exist(self):
        cases={
            'reaction':{'delta_h_kj':'-50','delta_s_jk':'-100','temperature_k':'350'},
            'clapeyron':{'p1':'1','t1':'350','t2':'370','hvap_jmol':'40000'},
            'arrhenius':{'k1':'1','t1_k':'300','t2_k':'330','ea_kjmol':'50'},
            'real':{'model':'van der Waals','n_mol':'1','v_l':'1','t_k':'300','a':'3.592','b':'0.04267'},
            'cell':{'e_cathode':'.34','e_anode':'-.76','n_e':'2','q':'1','temperature_k':'298.15'},
            'beer':{'epsilon':'100','path_cm':'1','concentration':'.002'},
            'decay':{'initial':'100','time':'10','half_life':'10'},
        }
        for tid,data in cases.items():
            with self.subTest(tool=tid):
                r=CALCS[tid](data)
                self.assertTrue((r.data or {}).get('plot',{}).get('series'))


if __name__=='__main__':
    unittest.main()
