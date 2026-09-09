import math, unittest
from nexum.core.calculators import CALCS
from nexum.core.acidbase import titration_state, hydrogen_weak_acid, hydrogen_weak_base
from nexum.core.experiments import haber_equilibrium, electrical_calorimetry_state, daniell_current_state
from nexum.core.constants import R_J,F

class NumericalGridTests(unittest.TestCase):
    def test_ideal_gas_roundtrip_grid(self):
        for n in (.1,1,5):
            for T in (250,298.15,600):
                for V in (1,10,50):
                    p=CALCS['ideal']({'p_atm':'','v_l':str(V),'n_mol':str(n),'t_k':str(T)})
                    P=float(p.value.split()[0])
                    t=CALCS['ideal']({'p_atm':str(P),'v_l':str(V),'n_mol':str(n),'t_k':''})
                    self.assertAlmostEqual(float(t.value.split()[0]),T,places=6)

    def test_strong_titration_monotonic(self):
        vals=[titration_state(mode='strong-strong',acid_c=.1,acid_v_ml=25,base_c=.1,base_added_ml=v)['ph'] for v in range(0,51)]
        self.assertTrue(all(b>=a for a,b in zip(vals,vals[1:])))
        self.assertAlmostEqual(vals[25],7,places=10)

    def test_weak_titration_monotonic(self):
        vals=[titration_state(mode='weak-strong',acid_c=.1,acid_v_ml=25,base_c=.1,base_added_ml=v,ka=1.8e-5)['ph'] for v in range(0,51)]
        self.assertTrue(all(b>=a for a,b in zip(vals,vals[1:])))

    def test_weak_acid_charge_identity(self):
        for C in (1e-8,1e-5,.01,.1):
            h=hydrogen_weak_acid(C,1.8e-5);ka=1.8e-5;kw=1e-14
            a=C*ka/(ka+h)
            self.assertAlmostEqual(h-a-kw/h,0,places=12)

    def test_weak_base_charge_identity(self):
        for C in (1e-8,1e-5,.01,.1):
            kb=1.8e-5;h=hydrogen_weak_base(C,kb);ka=1e-14/kb;bh=C*h/(ka+h)
            self.assertAlmostEqual(h+bh-1e-14/h,0,places=12)

    def test_nernst_q10_reference(self):
        r=CALCS['cell']({'e_cathode':'0.34','e_anode':'-0.76','n_e':'2','q':'10','temperature_k':'298.15'})
        expected=1.10-R_J*298.15/(2*F)*math.log(10)
        self.assertAlmostEqual(float(r.value.split()[0]),expected,places=9)

    def test_faraday_one_faraday_copper(self):
        r=CALCS['faraday']({'current_a':str(F),'time_s':'2','z':'2','molar_mass':'63.546','efficiency_percent':'100'})
        self.assertAlmostEqual(float(r.value.split()[0]),63.546,places=6)

    def test_regression_exact_line(self):
        r=CALCS['regression']({'points':'0,1;1,3;2,5;3,7'})
        self.assertAlmostEqual(float(r.value.split()[0]),2,places=12)
        self.assertAlmostEqual(r.data['intercept'],1,places=12);self.assertAlmostEqual(r.data['r2'],1,places=12)

    def test_beer_transmittance_identity(self):
        r=CALCS['beer']({'epsilon':'100','path_cm':'1','concentration':'0.01'})
        self.assertAlmostEqual(float(r.value),1,places=12);self.assertAlmostEqual(r.data['transmittance'],.1,places=12)

    def test_copper_fcc_density_reference(self):
        r=CALCS['lattice']({'type':'fcc','a_angstrom':'3.615','molar_mass':'63.546'})
        self.assertTrue(8.8<float(r.value.split()[0])<9.1)

    def test_bragg_forward_identity(self):
        r=CALCS['bragg']({'wavelength_nm':'0.15406','theta_deg':'30','order':'1'})
        d=float(r.value.split()[0]);self.assertAlmostEqual(2*d*math.sin(math.radians(30)),.15406,places=10)

    def test_brix_solids_conserved_concentration(self):
        r=CALCS['brix']({'solution_mass_kg':'100','brix':'10','target_brix':'20'})
        evap=float(r.value.split()[0]);final=100-evap;self.assertAlmostEqual(final*.20,10,places=10)

    def test_brix_solids_conserved_dilution(self):
        r=CALCS['brix']({'solution_mass_kg':'100','brix':'20','target_brix':'10'})
        add=float(r.value.split()[0]);final=100+add;self.assertAlmostEqual(final*.10,20,places=10)

    def test_haber_grid_conserves_N_and_H(self):
        for T in (400,700,1000):
            for P in (1,50,200):
                s=haber_equilibrium(n_n2=1,n_h2=3,n_nh3=.2,temp_k=T,pressure_bar=P);e=s['equilibrium_moles']
                self.assertAlmostEqual(2*e['n_n2']+e['n_nh3'],2.2,places=9)
                self.assertAlmostEqual(2*e['n_h2']+3*e['n_nh3'],6.6,places=9)

    def test_calorimetry_energy_balance_grid(self):
        for k in (0,.1,1):
            s=electrical_calorimetry_state(mass_g=100,cp_j_gk=4.184,calorimeter_capacity_jk=20,initial_temp_k=298.15,ambient_temp_k=298.15,heater_power_w=50,loss_coefficient_wk=k,time_s=100)
            self.assertAlmostEqual(s['input_energy_j'],s['stored_energy_j']+s['heat_lost_j'],places=8)

    def test_daniell_mass_charge_grid(self):
        for I in (.1,1,5):
            s=daniell_current_state(zn_conc0=1,cu_conc0=1,zn_volume_l=1,cu_volume_l=1,current_a=I,time_s=100)
            self.assertAlmostEqual(s['charge_c'],I*100,places=10)
            self.assertAlmostEqual(s['zinc_mass_lost_g']/65.38,s['copper_mass_deposited_g']/63.546,places=12)

    def test_photoelectric_below_threshold(self):
        r=CALCS['photoelectric']({'wavelength_nm':'800','work_function_ev':'3'})
        self.assertEqual(r.value,'Sem emissão');self.assertFalse(r.data['emission'])

    def test_photoelectric_above_threshold(self):
        r=CALCS['photoelectric']({'wavelength_nm':'300','work_function_ev':'2.3'})
        self.assertTrue(r.data['emission']);self.assertGreater(float(r.value.split()[0]),0)

    def test_arrhenius_temperature_direction(self):
        hot=CALCS['arrhenius']({'k1':'1','t1_k':'298.15','t2_k':'350','ea_kjmol':'50'})
        cold=CALCS['arrhenius']({'k1':'1','t1_k':'298.15','t2_k':'250','ea_kjmol':'50'})
        self.assertGreater(float(hot.value.split()[0]),1);self.assertLess(float(cold.value.split()[0]),1)

    def test_speciation_fractions_sum_one(self):
        for ph in (0,2,4.76,7,14):
            r=CALCS['speciation']({'pka':'4.76','ph':str(ph),'ph_min':'0','ph_max':'14'})
            self.assertAlmostEqual(r.data['alpha_ha']+r.data['alpha_a'],1,places=12)

if __name__=='__main__':unittest.main()
