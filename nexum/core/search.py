import re,unicodedata
ALIASES={
'molar':'molar mass massa molecular peso molecular molar mass', 'balance':'balance balancing balanceamento ecuacion equation',
'stoichiometry':'stoichiometry estequiometria limiting reagent reagente limitante rendimiento yield', 'empirical':'empirical formula formula empirica molecular formula',
'calorimetry':'calorimetry calorimetria heat calor', 'reaction':'gibbs enthalpy entropy entalpia entropia free energy', 'hess':'hess law entalpia', 'clapeyron':'clausius vapor pressure pressao vapor',
'ideal':'ideal gas gases ideais pv nrt', 'real':'real gas gases reais van der waals redlich kwong',
'concentration':'solution concentration concentracao molarity molaridade', 'dilution':'dilution diluicao dilucion', 'colligative':'colligative coligativas osmosis boiling freezing osmose ebulicao crioscopia',
'constants':'kc kp equilibrium constante equilibrio', 'ice':'ice table equilibrium tabela equilibrio', 'ph':'ph acid base acido base', 'buffer':'buffer tampao buffer solution', 'titration':'titration titulacao titulacion curva titulacion',
'cell':'electrochemistry electroquimica nernst cell celula', 'faraday':'electrolysis eletrolise faraday',
'configuration':'electron configuration configuracao eletronica atom atomic', 'photon':'photon foton wavelength comprimento onda', 'photoelectric':'photoelectric fotoeletrico', 'bohr':'bohr hydrogen hidrogenio spectrum',
'beer':'beer lambert absorbance absorbancia', 'regression':'regression regressao calibration calibracao',
'lattice':'crystal lattice rede cristalina solid state estado solido', 'bragg':'bragg diffraction difracao',
'decay':'decay meia vida half life nuclear', 'nuclear':'nuclear transformation alpha beta decaimento',
'ethanol':'ethanol etanol fermentation fermentacao industrial', 'brix':'brix caldo concentracao industrial'}
def norm(s): return re.sub(r'[^a-z0-9]+',' ',''.join(c for c in unicodedata.normalize('NFKD',s.lower()) if not unicodedata.combining(c))).strip()
def dist(a,b):
    if not a:return len(b)
    prev=list(range(len(b)+1))
    for i,ca in enumerate(a,1):
        cur=[i]
        for j,cb in enumerate(b,1):cur.append(min(cur[-1]+1,prev[j]+1,prev[j-1]+(ca!=cb)))
        prev=cur
    return prev[-1]
def match(query,tid,title,desc,group=''):
    q=norm(query)
    if not q:return True
    hay=norm(' '.join((tid,title,desc,group,ALIASES.get(tid,'')))); words=hay.split()
    for token in q.split():
        if token in hay: continue
        if not any(dist(token,w)<=max(1,min(3,len(token)//4)) for w in words): return False
    return True
