import math, unittest
from nexum.core.experiments import *
from nexum.core.structures import Atom,Molecule,build_ribbon_mesh,backbone_traces

class ExperimentScienceTests(unittest.TestCase):
    def test_gas_stp_and_work_identity(self):
        s=ideal_gas_path(n=1,temp_k=273.15,volume_initial_l=22.41396954,volume_final_l=22.41396954,duration_s=10,time_s=5)
        self.assertAlmostEqual(s['pressure_bar']/1.01325,1.0,places=7)
        self.assertAlmostEqual(s['work_by_gas_j'],0.0,places=12)
        self.assertEqual(s['delta_u_j'],0.0)
    def test_titration_strong_equivalence_and_extremes(self):
        before=titration_state(mode='strong-strong',acid_c=.1,acid_v_ml=25,base_c=.1,base_added_ml=0)
        eq=titration_state(mode='strong-strong',acid_c=.1,acid_v_ml=25,base_c=.1,base_added_ml=25)
        after=titration_state(mode='strong-strong',acid_c=.1,acid_v_ml=25,base_c=.1,base_added_ml=50)
        self.assertAlmostEqual(before['ph'],1.0,places=10);self.assertAlmostEqual(eq['ph'],7.0,places=10);self.assertGreater(after['ph'],12)
    def test_weak_acid_half_equivalence(self):
        ka=1.8e-5;pka=-math.log10(ka)
        s=titration_state(mode='weak-strong',acid_c=.1,acid_v_ml=25,base_c=.1,base_added_ml=12.5,ka=ka)
        # Henderson–Hasselbalch gives pH≈pKa here; the Nexum solves the full charge balance,
        # so water autoionization and finite [H+] produce a small physically meaningful offset.
        self.assertLess(abs(s['ph']-pka),1e-3)
        h=s['h_m']; oh=s['oh_m']; residual=h+s['spectator_cation_m']-s['a_minus_m']-oh
        self.assertAlmostEqual(residual,0.0,places=12)
    def test_daniell_faraday_mass_and_nernst(self):
        t=1000;s=daniell_current_state(zn_conc0=1,cu_conc0=1,zn_volume_l=1,cu_volume_l=1,current_a=2,time_s=t)
        xi=2*t/(2*F);self.assertAlmostEqual(s['extent_mol'],xi,places=12);self.assertAlmostEqual(s['charge_c'],2000,places=10);self.assertLess(s['e_rev_v'],1.10)
    def test_calorimetry_no_loss(self):
        s=electrical_calorimetry_state(mass_g=100,cp_j_gk=4.184,calorimeter_capacity_jk=0,initial_temp_k=298.15,heater_power_w=41.84,loss_coefficient_wk=0,time_s=10)
        self.assertAlmostEqual(s['temperature_k'],299.15,places=10);self.assertAlmostEqual(s['heat_lost_j'],0,places=10)
    def test_calorimetry_loss_conserves_energy(self):
        s=electrical_calorimetry_state(mass_g=100,cp_j_gk=4.184,calorimeter_capacity_jk=20,initial_temp_k=298.15,ambient_temp_k=298.15,heater_power_w=50,loss_coefficient_wk=.4,time_s=120)
        self.assertAlmostEqual(s['input_energy_j'],s['stored_energy_j']+s['heat_lost_j'],places=8);self.assertGreater(s['heat_lost_j'],0)
    def test_beer(self):
        s=beer_lambert_state(epsilon_l_mol_cm=100,concentration_m=.01,path_length_cm=1);self.assertAlmostEqual(s['absorbance'],1,places=12);self.assertAlmostEqual(s['transmittance'],.1,places=12)
    def test_first_order_half_life(self):
        s=first_order_state(concentration0_m=1,k_s=math.log(2)/10,time_s=10);self.assertAlmostEqual(s['fraction_remaining'],.5,places=12)
    def test_nuclear_half_life(self):
        s=nuclear_decay_state(nuclei0=1000,half_life_s=10,time_s=10);self.assertAlmostEqual(s['remaining'],500,places=10)
    def test_haber_thermodynamic_benchmark(self):
        h=haber_thermodynamics(298.15);self.assertAlmostEqual(h['log10_kp'],5.7345489107,places=8)
    def test_haber_equilibrium_conserves_atoms(self):
        s=haber_equilibrium(n_n2=1,n_h2=3,n_nh3=0,temp_k=700,pressure_bar=200);eq=s['equilibrium_moles']
        self.assertAlmostEqual(2*eq['n_n2']+eq['n_nh3'],2,places=10)
        self.assertAlmostEqual(2*eq['n_h2']+3*eq['n_nh3'],6,places=10)
        self.assertAlmostEqual(s['ln_q'],s['ln_kp'],places=7)
    def test_ribbon_mesh_is_real_3d_geometry(self):
        atoms=[]
        for i in range(12):
            a=i*.55;atoms.append(Atom('C',math.cos(a)*3,math.sin(a)*3,i*.8,'CA','ALA',str(i+1),'A',False))
        m=Molecule('helix',atoms,[],metadata={'polymer_backbone_atoms':12,'chains':['A']})
        traces=backbone_traces(m);self.assertEqual(len(traces['A']),12)
        meshes=build_ribbon_mesh(m);self.assertEqual(len(meshes),1);self.assertGreater(len(meshes[0]['vertices']),40)
        zspan=float(meshes[0]['vertices'][:,2].max()-meshes[0]['vertices'][:,2].min());self.assertGreater(zspan,5)
    def test_ribbon_has_physical_visual_thickness(self):
        atoms=[Atom('C',i*1.5,0,0,'CA','ALA',str(i+1),'A',False) for i in range(8)]
        m=Molecule('straight',atoms,[],metadata={'polymer_backbone_atoms':8,'chains':['A']})
        mesh=build_ribbon_mesh(m,width=1.6,thickness=.3)[0]
        # A zero-thickness billboard strip can disappear edge-on. The v5.1 ribbon
        # is extruded and therefore spans a finite third dimension.
        spans=mesh['vertices'].max(axis=0)-mesh['vertices'].min(axis=0)
        self.assertGreater(float(sorted(spans)[1]),.25)

if __name__=='__main__':unittest.main()
