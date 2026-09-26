import math
import unittest
import numpy as np

from nexum.core.advanced.activities import (
    ionic_strength, debye_huckel_limiting_gamma, davies_gamma
)
from nexum.core.advanced.equilibrium import (
    polyprotic_fractions, solve_polyprotic_acid,
    formation_speciation_ideal, ideal_reaction_equilibrium,
)
from nexum.core.advanced.eos import (
    peng_robinson_pure, peng_robinson_mixture, rachford_rice,
    isothermal_flash_pr,
)
from nexum.core.advanced.kinetics import (
    mass_action_network, arrhenius_rate_constant, arrhenius_network,
)
from nexum.core.advanced.electrochem import (
    butler_volmer, invert_butler_volmer, polarized_electrode, cottrell_current,
)
from nexum.core.advanced.metrology import (
    gum_propagation, monte_carlo_propagation, weighted_linear_regression,
)
from nexum.core.advanced.spectroscopy import multicomponent_beer
from nexum.core.advanced.thermo import ShomateCoefficients, shomate, reaction_thermodynamics
from nexum.core.advanced.engine import default_engine


class AdvancedBackendV65(unittest.TestCase):
    def test_ionic_strength_reference(self):
        # 0.1 mol/L NaCl ideal bookkeeping: I = 1/2(0.1+0.1)=0.1
        self.assertAlmostEqual(ionic_strength([0.1,0.1],[1,-1]),0.1,14)

    def test_activity_coefficients_go_to_one_at_zero_I(self):
        self.assertAlmostEqual(debye_huckel_limiting_gamma(2,0),1.0,15)
        self.assertAlmostEqual(davies_gamma(-1,0),1.0,15)

    def test_davies_reduces_charged_species_activity(self):
        self.assertLess(davies_gamma(1,0.1),1.0)
        self.assertLess(davies_gamma(2,0.1),davies_gamma(1,0.1))

    def test_polyprotic_fractions_sum_to_one(self):
        fr=polyprotic_fractions(1e-7,[1e-2,1e-7,1e-12])
        self.assertAlmostEqual(sum(fr),1.0,14)
        self.assertTrue(all(0<=x<=1 for x in fr))

    def test_activity_corrected_weak_acid_closes_charge(self):
        r=solve_polyprotic_acid(0.01,[1.8e-5],activity_model='davies')
        self.assertLess(abs(r['charge_residual']),1e-11)
        self.assertTrue(r['solver'].converged)
        self.assertLess(r['ionic_strength'],0.5)

    def test_debye_huckel_solver_is_numerically_stable_in_dilute_domain(self):
        r=solve_polyprotic_acid(0.01,[1.8e-5],activity_model='debye-huckel')
        self.assertLess(abs(r['charge_residual']),1e-11)
        self.assertTrue(math.isfinite(r['pH_activity']))

    def test_formation_speciation_matches_independent_analytic_solution(self):
        # A+B <-> AB, beta=10, bA=bB=1. Symmetry gives x+10x^2=1.
        r=formation_speciation_ideal([1,1],[[1,1]],[1])
        x=(-1+math.sqrt(41))/20
        self.assertAlmostEqual(r['free_components'][0],x,9)
        self.assertAlmostEqual(r['free_components'][1],x,9)
        self.assertAlmostEqual(r['formed_species'][0],10*x*x,9)
        self.assertLess(r['mass_balance_residual_norm'],1e-8)
        self.assertTrue(r['converged'])

    def test_multireaction_equilibrium_computes_not_presets(self):
        # A <-> B, K=10. nB/nA should be 10 in ideal fixed-volume model.
        r=ideal_reaction_equilibrium([1.0,1e-9],[[-1,1]],[math.log(10)])
        self.assertTrue(r['converged'])
        self.assertLess(r['residual_norm'],1e-6)
        self.assertAlmostEqual(r['amounts'][1]/r['amounts'][0],10,5)

    def test_peng_robinson_pure_root_satisfies_cubic(self):
        T=300.0; P=50.0; Tc=190.564; Pc=45.99; w=0.01142
        r=peng_robinson_pure(T,P,Tc,Pc,w)
        # Reconstruct A,B using returned a,b and verify cubic residual.
        R=0.0831446261815324
        A=r.a_mix*P/(R*R*T*T); B=r.b_mix*P/(R*T); z=r.z
        f=z**3-(1-B)*z**2+(A-3*B*B-2*B)*z-(A*B-B*B-B**3)
        self.assertLess(abs(f),1e-9)
        self.assertGreater(r.fugacity_coefficients[0],0)

    def test_peng_robinson_mixture_outputs_component_fugacities(self):
        r=peng_robinson_mixture(250,30,[0.5,0.5],[190.564,305.32],[45.99,48.72],[0.01142,0.0995])
        self.assertEqual(len(r.fugacity_coefficients),2)
        self.assertTrue(all(x>0 and math.isfinite(x) for x in r.fugacity_coefficients))

    def test_rachford_rice_mass_balance(self):
        z=np.array([0.4,0.6]); K=np.array([2.0,0.5]); r=rachford_rice(z,K)
        beta=r['vapor_fraction']; x=np.array(r['x']); y=np.array(r['y'])
        self.assertLess(np.max(np.abs(z-((1-beta)*x+beta*y))),1e-12)
        self.assertLess(abs(r['rr_residual']),1e-12)

    def test_peng_robinson_flash_closes_material_and_fugacity(self):
        r=isothermal_flash_pr(200,20,[0.5,0.5],[190.564,305.32],[45.99,48.72],[0.01142,0.0995],max_iter=500)
        self.assertEqual(r['phase'],'duas fases')
        self.assertTrue(r['converged'])
        self.assertLess(r['material_balance_residual_norm'],1e-10)
        self.assertLess(r['fugacity_residual_norm'],2e-8)
        self.assertTrue(0<r['vapor_fraction']<1)

    def test_irreversible_mass_action_matches_analytic_first_order(self):
        # A -> B, dcA/dt=-k A
        k=0.2; t=5.0
        r=mass_action_network([1,0],[[-1],[1]],[k],t_end=t,points=51)
        self.assertTrue(r['success'])
        self.assertAlmostEqual(r['final'][0],math.exp(-k*t),7)
        self.assertAlmostEqual(sum(r['final']),1.0,9)
        self.assertLess(r['linear_invariant_max_error'],1e-8)

    def test_reversible_network_reaches_kinetic_equilibrium_ratio(self):
        # A <-> B with kf/kr=4 -> B/A -> 4.
        r=mass_action_network([1,0],[[-1],[1]],[2.0],k_reverse=[0.5],t_end=20,points=101)
        self.assertTrue(r['success'])
        self.assertAlmostEqual(r['final'][1]/r['final'][0],4.0,5)

    def test_arrhenius_rate_constant_direction_and_identity(self):
        A=1e12; Ea=60000
        k1=arrhenius_rate_constant(A,Ea,298.15); k2=arrhenius_rate_constant(A,Ea,350)
        self.assertGreater(k2,k1)
        self.assertAlmostEqual(math.log(k2/k1),-Ea/8.31446261815324*(1/350-1/298.15),12)

    def test_arrhenius_network_calculates_k_from_inputs(self):
        r1=arrhenius_network([1,0],[[-1],[1]],[1e5],[30000],temperature_k=300,t_end=1,points=5)
        r2=arrhenius_network([1,0],[[-1],[1]],[1e5],[30000],temperature_k=350,t_end=1,points=5)
        self.assertGreater(r2['k_forward'][0],r1['k_forward'][0])
        self.assertLess(r2['final'][0],r1['final'][0])

    def test_butler_volmer_zero_overpotential_zero_net_current(self):
        r=butler_volmer(0,10,1)
        self.assertAlmostEqual(r['current_density_a_m2'],0.0,14)

    def test_butler_volmer_inverse_roundtrip(self):
        eta=0.075
        j=butler_volmer(eta,12.0,1,T=298.15,alpha_a=0.5,alpha_c=0.5)['current_density_a_m2']
        inv=invert_butler_volmer(j,12.0,1,T=298.15,alpha_a=0.5,alpha_c=0.5)
        self.assertTrue(inv['converged'])
        self.assertAlmostEqual(inv['overpotential_v'],eta,11)

    def test_polarized_electrode_adds_kinetic_and_ohmic_terms(self):
        r=polarized_electrode(0.5,100,10,1,electrode_area_m2=0.01,series_resistance_ohm=0.2)
        self.assertAlmostEqual(r['ohmic_drop_v'],0.2,12)
        self.assertAlmostEqual(r['applied_potential_v'],0.5+r['overpotential_v']+0.2,12)

    def test_cottrell_inverse_sqrt_time(self):
        i1=cottrell_current(1,1e-4,1000,1e-9,1)['current_a']
        i4=cottrell_current(1,1e-4,1000,1e-9,4)['current_a']
        self.assertAlmostEqual(i1/i4,2.0,12)

    def test_shomate_water_reference_cp_500k(self):
        # NIST WebBook coefficients for H2O(g), 500-1700 K.
        c=ShomateCoefficients(30.09200,6.832514,6.793435,-2.534480,0.082139,-250.8810,223.3967,-241.8264,500,1700)
        r=shomate(500,c)
        self.assertAlmostEqual(r['cp_j_mol_k'],35.21836175,7)

    def test_reaction_thermo_obeys_delta_g_lnK_identity(self):
        pA={'h_kj_mol':0.0,'s_j_mol_k':100.0}; pB={'h_kj_mol':-10.0,'s_j_mol_k':120.0}
        r=reaction_thermodynamics(300,{'A':-1,'B':1},{'A':pA,'B':pB})
        self.assertAlmostEqual(r['lnK'],-r['delta_g_kj_mol']*1000/(8.31446261815324*300),12)

    def test_gum_product_matches_analytic_first_order(self):
        # y=a*b, independent: u_y^2=(b u_a)^2+(a u_b)^2
        r=gum_propagation('a*b',{'a':2,'b':3},{'a':0.1,'b':0.2})
        expected=math.sqrt((3*0.1)**2+(2*0.2)**2)
        self.assertAlmostEqual(r['value'],6.0,12)
        self.assertAlmostEqual(r['standard_uncertainty'],expected,5)

    def test_monte_carlo_linear_model_matches_analytic_uncertainty(self):
        r=monte_carlo_propagation('a+b',{'a':2,'b':3},[[0.01,0],[0,0.04]],samples=20000,seed=7)
        self.assertAlmostEqual(r['mean'],5.0,2)
        self.assertAlmostEqual(r['standard_uncertainty'],math.sqrt(0.05),2)

    def test_weighted_regression_recovers_exact_line(self):
        r=weighted_linear_regression([0,1,2,3],[1,3,5,7],[0.1]*4)
        self.assertAlmostEqual(r['intercept'],1.0,12)
        self.assertAlmostEqual(r['slope'],2.0,12)
        self.assertLess(r['chi2'],1e-20)

    def test_multicomponent_beer_recovers_concentrations(self):
        E=np.array([[100,20],[50,80],[10,120]],float); c=np.array([0.01,0.02]); A=E@c
        r=multicomponent_beer(A,E,path_cm=1.0)
        self.assertAlmostEqual(r['concentrations_m'][0],0.01,10)
        self.assertAlmostEqual(r['concentrations_m'][1],0.02,10)
        self.assertLess(r['rmse'],1e-10)

    def test_scientific_engine_records_real_submitted_inputs_and_diagnostics(self):
        engine=default_engine()
        t1=engine.solve('formation-speciation',component_totals=[1,1],formation_stoich=[[1,1]],log_beta=[1])
        t2=engine.solve('formation-speciation',component_totals=[2,1],formation_stoich=[[1,1]],log_beta=[1])
        self.assertEqual(t1.inputs['component_totals'],[1,1])
        self.assertEqual(t2.inputs['component_totals'],[2,1])
        self.assertNotEqual(t1.result['free_components'],t2.result['free_components'])
        self.assertIn('mass_balance_residual_norm',t1.diagnostics)
        self.assertGreaterEqual(t1.elapsed_ms,0)

    def test_engine_has_no_embedded_answer_field(self):
        engine=default_engine()
        for key in engine.keys():
            spec=engine.spec(key)
            self.assertIsNotNone(spec.solver)
            self.assertFalse(hasattr(spec,'expected_result'))


if __name__=='__main__':
    unittest.main()
