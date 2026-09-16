GROUPS=[
('sto','Estequiometria'),('thermo','Termodinâmica'),('gases','Gases ideais e reais'),('solutions','Soluções'),('equilibrium','Equilíbrio e pH'),('kinetics','Cinética química'),('electro','Eletroquímica'),('atomic','Estrutura atômica'),('spectro','Espectroscopia'),('solid','Estado sólido'),('nuclear','Química nuclear'),('industrial','Química industrial')]
def F(key,label,default='',kind='text',options=None): return dict(key=key,label=label,default=str(default),kind=kind,options=options or [])
TOOLS=[
('molar','sto','Massa molar','Fórmulas, grupos e hidratos',[F('formula','Fórmula','CuSO4·5H2O')]),
('balance','sto','Balanceamento','Conservação de átomos com coeficientes mínimos',[F('equation','Equação','C3H8 + O2 -> CO2 + H2O')]),
('stoichiometry','sto','Reagente → produto','Massa teórica e rendimento a partir de uma reação',[F('equation','Equação','H2 + O2 -> H2O'),F('reactant','Reagente','H2'),F('reactant_mass_g','Massa reagente (g)','4.032'),F('product','Produto','H2O'),F('yield_percent','Rendimento (%)','100')]),
('empirical','sto','Fórmula empírica e molecular','Composição percentual livre',[F('composition','Composição','C:40,H:6.71,O:53.29'),F('experimental_molar_mass','Massa molar experimental (opcional)','180.156')]),
('calorimetry','thermo','Calorimetria','Calor sensível com dados editáveis',[F('mass_g','Massa (g)','100'),F('cp_j_gk','cₚ (J/g·K)','4.184'),F('ti_c','T inicial (°C)','20'),F('tf_c','T final (°C)','45')]),
('reaction','thermo','Gibbs e constante K','ΔG e K a partir de ΔH e ΔS',[F('delta_h_kj','ΔH (kJ/mol)','-92.4'),F('delta_s_jk','ΔS (J/mol·K)','-198.3'),F('temperature_k','T (K)','298.15')]),
('hess','thermo','Lei de Hess','Soma de etapas: fator:ΔH separadas por ;',[F('steps','Etapas','1:-393.5;-1:-283.0')]),
('clapeyron','thermo','Clausius–Clapeyron','Pressão de vapor em duas temperaturas',[F('p1','P₁','1'),F('t1','T₁ (K)','373.15'),F('t2','T₂ (K)','343.15'),F('hvap_jmol','ΔHvap (J/mol)','40650')]),
('arrhenius','thermo','Arrhenius entre duas temperaturas','Projeta k₂ a partir de k₁, Eₐ e temperaturas',[F('k1','k₁','1.0'),F('t1_k','T₁ (K)','298.15'),F('t2_k','T₂ (K)','323.15'),F('ea_kjmol','Eₐ (kJ/mol)','50')]),
('ideal','gases','Lei dos gases ideais','Deixe exatamente uma incógnita vazia',[F('p_atm','P (atm)','1'),F('v_l','V (L)',''),F('n_mol','n (mol)','1'),F('t_k','T (K)','298.15')]),
('real','gases','Gases reais','van der Waals ou Redlich–Kwong',[F('model','Modelo','van der Waals','select',['van der Waals','Redlich-Kwong']),F('n_mol','n (mol)','1'),F('v_l','V (L)','1'),F('t_k','T (K)','300'),F('a','a','3.592'),F('b','b','0.04267')]),
('concentration','solutions','Preparo e concentração','Molaridade e concentração mássica',[F('solute_mass_g','Massa soluto (g)','5.844'),F('molar_mass_gmol','Massa molar (g/mol)','58.44'),F('volume_l','Volume solução (L)','1')]),
('dilution','solutions','Diluição','Conservação de soluto',[F('c1','C₁ (mol/L)','1'),F('v1_ml','V₁ (mL)','10'),F('c2','C₂ (mol/L)','0.1')]),
('colligative','solutions','Propriedades coligativas','Elevação, depressão ou osmose',[F('mode','Modo','ebulição','select',['ebulição','criometria','osmose']),F('i','Fator de van’t Hoff i','1'),F('molality','Molalidade (mol/kg)','1'),F('kb','Kb (K·kg/mol)','0.512'),F('kf','Kf (K·kg/mol)','1.86'),F('molarity','Molaridade para osmose','1'),F('temperature_k','T para osmose (K)','298.15')]),
('constants','equilibrium','Conversão Kc ⇄ Kp','Relação por Δn gasoso',[F('k','Constante de origem','10'),F('delta_n','Δn gasoso','-2'),F('temperature_k','T (K)','298.15'),F('direction','Direção','Kc -> Kp','select',['Kc -> Kp','Kp -> Kc'])]),
('ice','equilibrium','Tabela ICE','Modelo A + B ⇌ C',[F('kc','Kc','4'),F('a0','[A]₀','1'),F('b0','[B]₀','1'),F('c0','[C]₀','0')]),
('ph','equilibrium','Ácidos e bases','pH forte/fraco monoprotônico',[F('kind','Tipo','ácido forte','select',['ácido forte','base forte','ácido fraco','base fraca']),F('concentration','Concentração (mol/L)','0.1'),F('ka_kb','Ka ou Kb (se fraco)','1.8e-5')]),
('buffer','equilibrium','Tampão','Henderson–Hasselbalch',[F('pka','pKa','4.76'),F('acid','[HA]','0.1'),F('base','[A⁻]','0.1')]),
('titration','equilibrium','Curva de titulação','Ácido forte ou fraco × base forte',[F('mode','Modelo','ácido forte','select',['ácido forte','ácido fraco']),F('acid_m','C ácido (mol/L)','0.1'),F('acid_ml','V ácido (mL)','25'),F('base_m','C base (mol/L)','0.1'),F('base_ml','V base adicionado (mL)','25'),F('pka','pKa (ácido fraco)','4.76')]),
('speciation','equilibrium','Especiação ácido-base','Frações α de HA/A⁻ em função do pH',[F('pka','pKa','4.76'),F('ph','pH de interesse','4.76'),F('ph_min','pH mínimo do gráfico','0'),F('ph_max','pH máximo do gráfico','14')]),
('kinetics','kinetics','Leis cinéticas integradas','Ordens zero, primeira e segunda com gráfico',[F('order','Ordem','1','select',['0','1','2']),F('c0','[A]₀ (mol/L)','1'),F('k','k','0.0693147'),F('time_s','Tempo avaliado (s)','10'),F('duration_s','Duração do gráfico (s)','40')]),
('cell','electro','Célula e Nernst','Potencial, Q e ΔG',[F('e_cathode','E° cátodo (V)','0.34'),F('e_anode','E° ânodo (V)','-0.76'),F('n_e','n elétrons','2'),F('q','Q','1'),F('temperature_k','T (K)','298.15')]),
('faraday','electro','Eletrólise · Faraday','Massa depositada',[F('current_a','Corrente (A)','2'),F('time_s','Tempo (s)','3600'),F('z','z elétrons','2'),F('molar_mass','M (g/mol)','63.546'),F('efficiency_percent','Eficiência (%)','100')]),
('configuration','atomic','Configuração eletrônica','Aufbau a partir de Z e carga',[F('z','Número atômico Z','26'),F('charge','Carga do íon','0')]),
('photon','atomic','Energia de fóton','λ, ν e E',[F('wavelength_nm','λ (nm)','500')]),
('photoelectric','atomic','Efeito fotoelétrico','Energia cinética e potencial de parada',[F('wavelength_nm','λ (nm)','300'),F('work_function_ev','Função trabalho φ (eV)','2.3')]),
('bohr','atomic','Transições de Bohr','Espécies hidrogenoides',[F('n_i','n inicial','3'),F('n_f','n final','2'),F('z','Z nuclear','1')]),
('beer','spectro','Beer–Lambert','Absorbância',[F('epsilon','ε (L/mol·cm)','100'),F('path_cm','b (cm)','1'),F('concentration','c (mol/L)','0.002')]),
('regression','spectro','Calibração e regressão','Pontos x,y separados por ;',[F('points','Pontos','0,0.01;1,1.02;2,2.01;3,3.03')]),
('lattice','solid','Redes cristalinas cúbicas','Densidade SC/BCC/FCC',[F('type','Rede','fcc','select',['sc','bcc','fcc']),F('a_angstrom','a (Å)','3.615'),F('molar_mass','M (g/mol)','63.546')]),
('bragg','solid','Lei de Bragg','Espaçamento interplanar',[F('wavelength_nm','λ (nm)','0.15406'),F('theta_deg','θ (graus)','22.5'),F('order','Ordem n','1')]),
('decay','nuclear','Decaimento e meia-vida','Lei exponencial',[F('initial','Quantidade inicial','100'),F('time','Tempo','10'),F('half_life','Meia-vida','10')]),
('nuclear','nuclear','Transformação nuclear','Conservação formal A/Z',[F('a','Número de massa A','238'),F('z','Número atômico Z','92'),F('mode','Transformação','alfa','select',['alfa','beta-','beta+','captura eletrônica','gama'])]),
('ethanol','industrial','Etanol · biomassa','Balanço ideal de fermentação',[F('feed_mass_kg','Massa de matéria-prima (kg)','1000'),F('fermentable_fraction','Fração mássica fermentável','0.14'),F('efficiency','Eficiência (%)','90')]),
('brix','industrial','Brix e concentração','Balanço de sólidos solúveis',[F('solution_mass_kg','Massa inicial (kg)','1000'),F('brix','°Brix inicial','15'),F('target_brix','°Brix alvo','65')]),
]


# Scientific scope shown in the UI. This is deliberately about model validity,
# not an educational-level badge or a claim of universal accuracy.
TOOL_SCOPE = {
    'molar': ('DADOS + CÁLCULO', 'Massa molar por composição e valores atômicos representativos.'),
    'balance': ('FORMAL', 'Conservação elementar para equações moleculares neutras.'),
    'stoichiometry': ('QUANTITATIVO', 'Estequiometria exata após definir reação e reagente limitante.'),
    'empirical': ('MODELO', 'Inferência de razões inteiras a partir de composição experimental.'),
    'calorimetry': ('MODELO', 'q=mcₚΔT com cₚ constante no intervalo.'),
    'reaction': ('MODELO', 'ΔH e ΔS constantes com a temperatura informada.'),
    'hess': ('QUANTITATIVO', 'Combinação linear de entalpias fornecidas.'),
    'clapeyron': ('MODELO', 'Vapor ideal e ΔH_vap constante.'),
    'arrhenius': ('MODELO', 'Eₐ constante e mecanismo invariável no intervalo.'),
    'ideal': ('MODELO', 'Gás ideal, Z=1.'),
    'real': ('MODELO', 'van der Waals/Redlich–Kwong; sem equilíbrio de fases.'),
    'concentration': ('QUANTITATIVO', 'Balanço de quantidade de matéria e volume informado.'),
    'dilution': ('MODELO', 'Soluto conservado e volumes tratados como aditivos.'),
    'colligative': ('MODELO', 'Solução ideal diluída e fator i efetivo informado.'),
    'constants': ('MODELO', 'Conversão Kc/Kp sob estados padrão e gás ideal declarados.'),
    'ice': ('MODELO', 'Equilíbrio específico A+B⇌C em solução ideal.'),
    'ph': ('MODELO', 'Balanço exato de concentração ideal; pH termodinâmico usa atividade.'),
    'buffer': ('MODELO', 'Balanço exato de concentração ideal; atividades≈concentrações.'),
    'titration': ('MODELO', 'Balanços de matéria/carga ideais a 25 °C.'),
    'speciation': ('MODELO', 'Ácido monoprótico ideal.'),
    'kinetics': ('MODELO', 'Lei integrada de uma única ordem e k constante.'),
    'cell': ('MODELO', 'Nernst é termodinâmico; Q deve ser construído com atividades.'),
    'faraday': ('QUANTITATIVO', 'Lei de Faraday com eficiência faradaica informada.'),
    'configuration': ('FORMAL', 'Configuração orbital de referência; não é cálculo multieletrônico ab initio.'),
    'photon': ('QUANTITATIVO', 'Relações exatas E=hν=hc/λ com constantes definidas.'),
    'photoelectric': ('MODELO', 'Modelo de Einstein com função trabalho informada.'),
    'bohr': ('MODELO', 'Somente espécies hidrogenoides de um elétron.'),
    'beer': ('MODELO', 'Beer–Lambert em meio homogêneo e faixa linear.'),
    'regression': ('QUANTITATIVO', 'OLS não ponderado; inferência estatística depende das hipóteses dos resíduos.'),
    'lattice': ('MODELO', 'Célula cúbica ideal, ocupação completa.'),
    'bragg': ('QUANTITATIVO', 'Geometria nλ=2d sinθ para os dados fornecidos.'),
    'decay': ('MODELO', 'Lei exponencial macroscópica de decaimento.'),
    'nuclear': ('FORMAL', 'Conserva A/Z; não prevê estabilidade, energia Q ou branching.'),
    'ethanol': ('MODELO', 'Balanço ideal em equivalente de glicose e eficiência informada.'),
    'brix': ('MODELO', '°Brix tratado como fração mássica idealizada de sólidos solúveis.'),
}


TOOLS += [
('titration_derivatives','sto','Derivadas da titulação','Dados experimentais, primeira e segunda derivadas',[F('points','Volume (mL),pH; use ponto decimal','20,2.65;23,3.05;24,3.39;24.5,3.69;25,7;25.5,10.99;26,11.29;27,11.59;30,11.96')]),
('combustion','industrial','Combustão de hidrocarbonetos','Ar teórico, excesso de ar e composição de saída',[F('carbon','Átomos de C','8'),F('hydrogen','Átomos de H','18'),F('feed_kg_h','Alimentação (kg/h)','1700'),F('conversion','Conversão (%)','72'),F('excess_air','Excesso de ar (%)','20')]),
('reactor','industrial','Dimensionamento CSTR e PFR','Reatores ideais de primeira ordem',[F('k','k (s⁻¹)','0.1'),F('flow','Vazão (L/s)','2'),F('conversion','Conversão (%)','80')]),
('spectral_units','spectro','Conversão de unidades espectrais','Comprimento de onda, número de onda e energia',[F('wavelength_nm','Comprimento de onda no vácuo (nm)','500')]),
('mass_spectrum','spectro','Espectrometria de massas','Erro em ppm e poder de resolução',[F('reference','m/z de referência (Th)','195.0877'),F('observed','m/z observado (Th)','195.0880'),F('width','Largura FWHM (Th)','0.002')]),
]
TOOL_SCOPE.update({
 'titration_derivatives':('NUMÉRICO','Diferenças divididas; derivação amplifica ruído; inflexão não certifica equivalência.'),
 'combustion':('MODELO','Hidrocarboneto puro; fração convertida queima a CO₂ e H₂O; ar seco 21/79.'),
 'reactor':('MODELO','Reação de primeira ordem; regime permanente; densidade e temperatura constantes.'),
 'spectral_units':('QUANTITATIVO','Conversões no vácuo com constantes SI definidas.'),
 'mass_spectrum':('QUANTITATIVO','Mesmo íon e carga; resolução definida por FWHM.'),
})


TOOLS += [
('pipe_loss','industrial','Perda de carga em tubulações','Darcy–Weisbach, Reynolds e Haaland',[F('rho','Densidade (kg/m³)','1000'),F('mu','Viscosidade (Pa·s)','0.001'),F('diam','Diâmetro interno (m)','0.05'),F('length','Comprimento (m)','10'),F('velocity','Velocidade média (m/s)','1'),F('rough','Rugosidade absoluta (m)','0.00001')]),
('exchanger','industrial','Trocador de calor em contracorrente','Diferença média logarítmica e potência térmica',[F('hot_in','T quente entrada (°C)','100'),F('hot_out','T quente saída (°C)','60'),F('cold_in','T fria entrada (°C)','20'),F('cold_out','T fria saída (°C)','40'),F('u','U (W/m²·K)','500'),F('area','Área (m²)','2')]),
('chromatography','spectro','Resolução cromatográfica','Retenção, seletividade e separação entre picos',[F('dead','Tempo morto (min)','1'),F('first','tR primeiro pico (min)','4'),F('second','tR segundo pico (min)','5'),F('w1','Largura na base 1 (min)','0.5'),F('w2','Largura na base 2 (min)','0.6')]),
]
TOOL_SCOPE.update({key:('MODELO',note) for key,note in {
'pipe_loss':'Darcy–Weisbach; laminar ou Haaland turbulento; sem transição nem perdas localizadas.',
'exchanger':'Contracorrente ideal, coeficiente global constante e F=1.',
'chromatography':'Larguras na base e tempos na mesma unidade; sem identificação química.'}.items()})
