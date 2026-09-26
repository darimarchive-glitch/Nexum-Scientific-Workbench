import unittest
from nexum.core.advanced.protocols import (
    gas_protocol,titration_protocol,daniell_protocol,calorimetry_protocol,
    first_order_protocol,nuclear_protocol,
)

class ComputedProtocolsV65(unittest.TestCase):
    def test_gas_frames_are_recomputed_from_control_path(self):
        a=gas_protocol(n=1,temp_k=300,volume_initial_l=10,volume_final_l=20,duration_s=10,points=11)
        b=gas_protocol(n=2,temp_k=300,volume_initial_l=10,volume_final_l=20,duration_s=10,points=11)
        self.assertLess(a['diagnostics']['pv_residual_max_l_bar'],1e-12)
        self.assertAlmostEqual(b['states'][5]['pressure_bar'],2*a['states'][5]['pressure_bar'],12)

    def test_titration_protocol_uses_burette_rate_as_real_control(self):
        a=titration_protocol(mode='strong-strong',acid_c=.1,acid_v_ml=25,base_c=.1,burette_rate_ml_s=1,duration_s=25,points=26)
        b=titration_protocol(mode='strong-strong',acid_c=.1,acid_v_ml=25,base_c=.1,burette_rate_ml_s=.5,duration_s=25,points=26)
        self.assertAlmostEqual(a['states'][-1]['base_added_ml'],25,12)
        self.assertAlmostEqual(a['states'][-1]['ph'],7.0,8)
        self.assertNotAlmostEqual(a['states'][-1]['ph'],b['states'][-1]['ph'],4)

    def test_daniell_protocol_obeys_faraday_every_frame(self):
        r=daniell_protocol(zn_conc0=1,cu_conc0=1,zn_volume_l=1,cu_volume_l=1,temp_k=298.15,current_a=1,duration_s=100,points=17)
        self.assertLess(r['diagnostics']['faraday_extent_residual_max_mol'],1e-15)
        self.assertGreater(r['states'][-1]['zn_conc_m'],r['states'][0]['zn_conc_m'])

    def test_calorimetry_protocol_closes_energy(self):
        r=calorimetry_protocol(mass_g=100,cp_j_gk=4.184,initial_temp_k=298.15,heater_power_w=20,duration_s=100,ambient_temp_k=298.15,loss_coefficient_wk=.2,points=31)
        self.assertLess(r['diagnostics']['energy_balance_residual_max_j'],1e-10)

    def test_kinetic_protocol_is_not_animation_interpolation(self):
        r=first_order_protocol(concentration0_m=1,k_s=.1,duration_s=20,points=21)
        self.assertTrue(r['diagnostics']['monotonic'])
        self.assertAlmostEqual(r['states'][10]['concentration_m'],2.718281828459045**-1,8)

    def test_nuclear_protocol_conserves_population_bookkeeping(self):
        r=nuclear_protocol(nuclei0=1000,half_life_s=10,duration_s=20,points=21)
        self.assertLess(r['diagnostics']['mass_balance_residual_max'],1e-10)
        self.assertAlmostEqual(r['states'][10]['remaining'],500,8)

if __name__=='__main__': unittest.main()
