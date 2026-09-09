from __future__ import annotations

"""Computed experiment trajectories for Nexum 6.5.

A protocol is not an animation script. It is a sequence of control inputs
(volume delivered, elapsed time, current, etc.) evaluated by the scientific
model at each point. The UI may animate the returned states, but cannot invent
or interpolate a chemical result independently of this module.
"""

import math
import numpy as np

from ..experiments import (
    ideal_gas_path,
    titration_state,
    daniell_current_state,
    electrical_calorimetry_state,
    first_order_state,
    nuclear_decay_state,
)


def _times(duration_s, points):
    duration=float(duration_s)
    if not math.isfinite(duration) or duration <= 0:
        raise ValueError("Duração deve ser positiva e finita.")
    points=max(2,int(points))
    return np.linspace(0.0,duration,points)


def gas_protocol(*, n, temp_k, volume_initial_l, volume_final_l, duration_s, points=181):
    states=[ideal_gas_path(n=n,temp_k=temp_k,volume_initial_l=volume_initial_l,
                           volume_final_l=volume_final_l,duration_s=duration_s,time_s=t)
            for t in _times(duration_s,points)]
    # pV=nRT in L bar for every computed frame.
    residual=max(abs(s["pressure_bar"]*s["volume_l"]-float(n)*(8.31446261815324/100)*float(temp_k)) for s in states)
    return {"states":states,"diagnostics":{"pv_residual_max_l_bar":residual,"points":len(states)}}


def titration_protocol(*, mode, acid_c, acid_v_ml, base_c, burette_rate_ml_s,
                        duration_s, ka=1.8e-5, points=241):
    rate=float(burette_rate_ml_s)
    if not math.isfinite(rate) or rate < 0:
        raise ValueError("Vazão da bureta deve ser não negativa e finita.")
    states=[]
    for t in _times(duration_s,points):
        v=rate*float(t)
        s=titration_state(mode=mode,acid_c=acid_c,acid_v_ml=acid_v_ml,
                          base_c=base_c,base_added_ml=v,ka=ka)
        states.append({"time_s":float(t),"base_added_ml":v,**s})
    phs=[s["ph"] for s in states]
    return {"states":states,"diagnostics":{"points":len(states),
            "ph_min":min(phs),"ph_max":max(phs),
            "equivalence_ml":states[0]["equivalence_ml"]}}


def daniell_protocol(*, zn_conc0, cu_conc0, zn_volume_l, cu_volume_l,
                      temp_k, current_a, duration_s, e0_v=1.10, points=181):
    states=[daniell_current_state(zn_conc0=zn_conc0,cu_conc0=cu_conc0,
                                  zn_volume_l=zn_volume_l,cu_volume_l=cu_volume_l,
                                  temp_k=temp_k,current_a=current_a,time_s=t,e0_v=e0_v)
            for t in _times(duration_s,points)]
    # Charge/extent identity must hold until Cu2+ exhaustion clamps the time.
    residual=max(abs(s["extent_mol"]-s["charge_c"]/(2*96485.33212)) for s in states)
    return {"states":states,"diagnostics":{"faraday_extent_residual_max_mol":residual,
                                             "points":len(states)}}


def calorimetry_protocol(*, mass_g, cp_j_gk, initial_temp_k, heater_power_w,
                          duration_s, calorimeter_capacity_jk=0.0,
                          ambient_temp_k=None, loss_coefficient_wk=0.0, points=181):
    states=[electrical_calorimetry_state(mass_g=mass_g,cp_j_gk=cp_j_gk,
                                         calorimeter_capacity_jk=calorimeter_capacity_jk,
                                         initial_temp_k=initial_temp_k,
                                         ambient_temp_k=ambient_temp_k,
                                         heater_power_w=heater_power_w,
                                         loss_coefficient_wk=loss_coefficient_wk,time_s=t)
            for t in _times(duration_s,points)]
    residual=max(abs(s["input_energy_j"]-s["stored_energy_j"]-s["heat_lost_j"]) for s in states)
    return {"states":states,"diagnostics":{"energy_balance_residual_max_j":residual,
                                             "points":len(states)}}


def first_order_protocol(*, concentration0_m, k_s, duration_s, points=181):
    states=[]
    for t in _times(duration_s,points):
        s=first_order_state(concentration0_m=concentration0_m,k_s=k_s,time_s=t)
        states.append({"time_s":float(t),**s})
    return {"states":states,"diagnostics":{"points":len(states),
                                             "monotonic":all(states[i+1]["concentration_m"]<=states[i]["concentration_m"]+1e-15 for i in range(len(states)-1))}}


def nuclear_protocol(*, nuclei0, half_life_s, duration_s, points=181):
    states=[]
    for t in _times(duration_s,points):
        s=nuclear_decay_state(nuclei0=nuclei0,half_life_s=half_life_s,time_s=t)
        states.append({"time_s":float(t),**s})
    return {"states":states,"diagnostics":{"points":len(states),
                                             "mass_balance_residual_max":max(abs(float(nuclei0)-s["remaining"]-s["decayed"]) for s in states)}}
