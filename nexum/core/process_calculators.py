"""Additional process models, with explicit applicability checks."""
import math

def pipe_loss(d):
    from .calculators import R,pos,nonneg
    rho=pos(d['rho'],'Densidade');mu=pos(d['mu'],'Viscosidade');diam=pos(d['diam'],'Diâmetro');length=pos(d['length'],'Comprimento');v=pos(d['velocity'],'Velocidade');rough=nonneg(d['rough'],'Rugosidade')
    re=rho*v*diam/mu
    if rough/diam>.05:raise ValueError('Rugosidade relativa deve ser ≤ 0,05.')
    if 2300<=re<4000:raise ValueError('Regime de transição (2300 ≤ Re < 4000): este modelo não estima o atrito.')
    factor=64/re if re<2300 else (-1.8*math.log10((rough/diam/3.7)**1.11+6.9/re))**-2
    dp=factor*(length/diam)*rho*v*v/2
    return R('Perda de pressão',dp,'Pa','Re=ρvD/μ; ΔP=f(L/D)ρv²/2',f'Re={re:.8g}; f Darcy={factor:.8g}', ['Tubo circular, escoamento permanente incompressível e plenamente desenvolvido; perdas localizadas excluídas.','Laminar: f=64/Re; turbulento: aproximação de Haaland.'],{'reynolds':re,'darcy_factor':factor,'pressure_drop_pa':dp})

def exchanger(d):
    from .calculators import R,pos,num
    hi=num(d,'hot_in');ho=num(d,'hot_out');ci=num(d,'cold_in');co=num(d,'cold_out');u=pos(d['u'],'Coeficiente global');area=pos(d['area'],'Área')
    if not all(math.isfinite(x) for x in (hi,ho,ci,co)):raise ValueError('Temperaturas devem ser finitas.')
    if hi<=ho or co<=ci:raise ValueError('O fluido quente deve esfriar e o frio deve aquecer.')
    a,b=hi-co,ho-ci
    if min(a,b)<=0:raise ValueError('Diferenças terminais devem ser positivas em contracorrente.')
    lm=a if abs(a-b)<1e-10*max(a,b) else (a-b)/math.log(a/b)
    return R('Potência térmica',u*area*lm,'W','ΔTlm=(ΔT₁−ΔT₂)/ln(ΔT₁/ΔT₂); Q̇=UAΔTlm',f'ΔT₁={a:g} K; ΔT₂={b:g} K; ΔTlm={lm:.8g} K', ['Contracorrente ideal; U constante; correção geométrica F=1. Não fecha balanço de energia sem vazões e capacidades caloríficas.'],{'lmtd_k':lm,'duty_w':u*area*lm})

def chromatography(d):
    from .calculators import R,pos
    t0=pos(d['dead'],'Tempo morto');t1=pos(d['first'],'Primeiro pico');t2=pos(d['second'],'Segundo pico');w1=pos(d['w1'],'Largura 1');w2=pos(d['w2'],'Largura 2')
    if not t0<t1<t2:raise ValueError('Exige tempo morto < tR₁ < tR₂.')
    k1=(t1-t0)/t0;k2=(t2-t0)/t0;resolution=2*(t2-t1)/(w1+w2)
    return R('Resolução cromatográfica',resolution,'','Rs=2(tR₂−tR₁)/(w₁+w₂); k′=(tR−t₀)/t₀',f'k′₁={k1:.8g}; k′₂={k2:.8g}; seletividade α={k2/k1:.8g}', ['Todas as entradas de tempo na mesma unidade. Larguras na linha de base, não FWHM. Não identifica substâncias.'],{'resolution':resolution,'selectivity':k2/k1,'retention_factors':[k1,k2]})

PROCESS_CALCS={'pipe_loss':pipe_loss,'exchanger':exchanger,'chromatography':chromatography}
