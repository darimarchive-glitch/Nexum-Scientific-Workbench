"""Ideal, isothermal CSTR startup with constant volume and feed."""
import math

def cstr_startup(*, volume_l, flow_l_s, feed_m, initial_m, k_s, time_s):
    values=[float(v) for v in (volume_l,flow_l_s,feed_m,initial_m,k_s,time_s)]
    volume,flow,feed,initial,k,t=values
    if any(not math.isfinite(v) for v in values) or volume<=0 or flow<=0 or min(feed,initial,k,t)<0:
        raise ValueError('Volume e vazão positivos; concentrações, k e tempo não negativos e finitos.')
    rate=flow/volume+k
    steady=feed/(1+k*volume/flow)
    concentration=steady+(initial-steady)*math.exp(-rate*t)
    return {'concentration_m':concentration,'steady_m':steady,'time_constant_s':1/rate,
            'rate_m_s':flow/volume*(feed-concentration)-k*concentration,'time_s':t}
