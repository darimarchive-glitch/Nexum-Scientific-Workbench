"""Additional calculators; all numeric inputs validated at the model boundary."""
import math
from .titration_analysis import analyze_curve

# Imported by calculators only after its common helpers have been defined.



def derivative_plots(points, analysis):
    from .calculators import R, pos, nonneg, plot
    marker=[] if analysis['estimated_equivalence_ml'] is None else [{'x':analysis['estimated_equivalence_ml'],'label':'estimativa'}]
    return [plot(title,'Volume / mL',unit,[{'name':title,'points':values}],marker)
            for title,unit,values in [('Curva de titulação','pH',points),
            ('Primeira derivada','pH/mL',analysis['first_derivative']),
            ('Segunda derivada','pH/mL²',analysis['second_derivative'])]]


def calc_derivatives(d):
    from .calculators import R, pos, nonneg, plot
    try: points=[tuple(map(float,p.strip().split(','))) for p in d['points'].split(';') if p.strip()]
    except ValueError as exc:raise ValueError('Use volume,pH;volume,pH e ponto decimal.') from exc
    analysis=analyze_curve(points)
    graphs=derivative_plots(points,analysis)
    estimate=analysis['estimated_equivalence_ml']
    return R('Estimativa de equivalência', 'Não identificada' if estimate is None else estimate,
             '' if estimate is None else 'mL',
             'D₁=ΔpH/ΔV nos volumes médios; D₂=ΔD₁/ΔV médio',
             f"Pico de |D₁| em {analysis['peak_volume_ml']:.8g} mL.\nZero de D₂ interpolado próximo ao pico interno de |D₁|.",
             ['Dados na ordem de aquisição; espaçamento pode variar.',
              'Derivação amplifica ruído. Sem suavização automática; estimativa não certifica equivalência química.',
              'Pico na borda ou ausência de inflexão: amplie a faixa medida.'],
             {**analysis,'plots':graphs,'plot':graphs[0]})


def calc_combustion(d):
    from .calculators import R, pos, nonneg, plot
    carbon=pos(d['carbon'],'Átomos de C'); hydrogen=pos(d['hydrogen'],'Átomos de H')
    if not carbon.is_integer() or not hydrogen.is_integer():raise ValueError('C e H devem ser inteiros.')
    feed=pos(d['feed_kg_h'],'Vazão'); conversion=nonneg(d['conversion'],'Conversão (%)')/100
    excess=nonneg(d['excess_air'],'Excesso de ar (%)')/100
    if conversion>1:raise ValueError('Conversão deve estar entre 0 e 100%.')
    molar_mass=12.011*carbon+1.008*hydrogen
    fuel=feed/molar_mass; oxygen=fuel*(carbon+hydrogen/4); air=oxygen/.21
    outlet={'CO2':fuel*conversion*carbon,'H2O':fuel*conversion*hydrogen/2,
            'O2':oxygen*(1+excess-conversion),'N2':air*(1+excess)*.79,
            'combustível não convertido':fuel*(1-conversion)}
    total=sum(outlet.values())
    lines='\n'.join(f'{k}: {v:.8g} kmol/h; y={v/total:.8g}' for k,v in outlet.items())
    return R('Ar alimentado',air*(1+excess),'kmol/h',
             'CₓHᵧ + (x+y/4)O₂ → xCO₂ + (y/2)H₂O',
             f'M combustível={molar_mass:.8g} kg/kmol; combustível={fuel:.8g} kmol/h\nO₂ teórico={oxygen:.8g} kmol/h; ar teórico={air:.8g} kmol/h\nEntrada: O₂={oxygen*(1+excess):.8g}; N₂={air*(1+excess)*.79:.8g} kmol/h\nSaída (base úmida):\n{lines}',
             ['Ar seco: 21% O₂ e 79% N₂ em mol.', 'Ar teórico e excesso referidos à conversão total da alimentação.',
              'A fração convertida produz somente CO₂/H₂O. Não prevê CO, fuligem, NOx ou condensação.'],
             {'outlet_kmol_h':outlet,'air_kmol_h':air*(1+excess),'fuel_kmol_h':fuel})


def calc_reactor(d):
    from .calculators import R, pos, nonneg, plot
    k=pos(d['k'],'k'); flow=pos(d['flow'],'Vazão volumétrica'); x=nonneg(d['conversion'],'Conversão (%)')/100
    if x>=1:raise ValueError('Conversão deve ser menor que 100%.')
    cstr=x/(k*(1-x)); pfr=-math.log1p(-x)/k
    return R('Volume do CSTR',flow*cstr,'L','τCSTR=X/[k(1−X)]; τPFR=−ln(1−X)/k; V=Qτ',
             f'τCSTR={cstr:.8g} s; VCSTR={flow*cstr:.8g} L\nτPFR={pfr:.8g} s; VPFR={flow*pfr:.8g} L',
             ['Estado estacionário; reação irreversível de primeira ordem; densidade, vazão e temperatura constantes.'],
             {'cstr_l':flow*cstr,'pfr_l':flow*pfr})


def calc_spectral(d):
    from .calculators import R, pos, nonneg, plot
    wavelength=pos(d['wavelength_nm'],'Comprimento de onda'); nu=299792458/(wavelength*1e-9)
    energy=6.62607015e-34*nu; wave=1e7/wavelength
    return R('Número de onda',wave,'cm⁻¹','ν=c/λ; E=hν; número de onda=1/λ',
             f'λ={wavelength:.8g} nm; ν={nu:.8g} Hz\nE={energy:.8g} J/fóton = {energy/1.602176634e-19:.8g} eV\nE molar={energy*6.02214076e23/1000:.8g} kJ/mol',
             ['Comprimento de onda no vácuo.'],{'frequency_hz':nu,'wavenumber_cm':wave})


def calc_mass_spectrum(d):
    from .calculators import R, pos, nonneg, plot
    reference=pos(d['reference'],'m/z de referência'); observed=pos(d['observed'],'m/z observado'); width=pos(d['width'],'Largura FWHM')
    ppm=(observed-reference)/reference*1e6; resolution=observed/width
    return R('Erro de massa',ppm,'ppm','erro=10⁶(m/zobs−m/zref)/(m/zref); R=(m/zobs)/FWHM',
             f'Δ(m/z)={observed-reference:.8g}; poder de resolução={resolution:.8g}',
             ['Compare o mesmo íon, aduto e estado de carga.', 'Largura a meia altura (FWHM); não identifica a molécula pelo pico isolado.'],
             {'error_ppm':ppm,'resolving_power':resolution})

ADDITIONAL_CALCS={'titration_derivatives':calc_derivatives,'combustion':calc_combustion,
                  'reactor':calc_reactor,'spectral_units':calc_spectral,'mass_spectrum':calc_mass_spectrum}
