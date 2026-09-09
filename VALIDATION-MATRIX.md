# Matriz de validação — Nexum v6.0

Esta matriz descreve **o que cada ferramenta resolve** e **o que ela não deve afirmar**. “Passou nos testes” significa que a implementação reproduziu benchmarks/identidades do modelo; não significa validade universal fora das hipóteses.

| Área | Ferramenta | Classe | Domínio/limite principal |
|---|---|---|---|
| Estequiometria | Massa molar | **DADOS + CÁLCULO** | Massa molar por composição e valores atômicos representativos. |
| Estequiometria | Balanceamento | **FORMAL** | Conservação elementar para equações moleculares neutras. |
| Estequiometria | Reagente → produto | **QUANTITATIVO** | Estequiometria exata após definir reação e reagente limitante. |
| Estequiometria | Fórmula empírica e molecular | **MODELO** | Inferência de razões inteiras a partir de composição experimental. |
| Termodinâmica | Calorimetria | **MODELO** | q=mcₚΔT com cₚ constante no intervalo. |
| Termodinâmica | Gibbs e constante K | **MODELO** | ΔH e ΔS constantes com a temperatura informada. |
| Termodinâmica | Lei de Hess | **QUANTITATIVO** | Combinação linear de entalpias fornecidas. |
| Termodinâmica | Clausius–Clapeyron | **MODELO** | Vapor ideal e ΔH_vap constante. |
| Termodinâmica | Arrhenius entre duas temperaturas | **MODELO** | Eₐ constante e mecanismo invariável no intervalo. |
| Gases ideais e reais | Lei dos gases ideais | **MODELO** | Gás ideal, Z=1. |
| Gases ideais e reais | Gases reais | **MODELO** | van der Waals/Redlich–Kwong; sem equilíbrio de fases. |
| Soluções | Preparo e concentração | **QUANTITATIVO** | Balanço de quantidade de matéria e volume informado. |
| Soluções | Diluição | **MODELO** | Soluto conservado e volumes tratados como aditivos. |
| Soluções | Propriedades coligativas | **MODELO** | Solução ideal diluída e fator i efetivo informado. |
| Equilíbrio e pH | Conversão Kc ⇄ Kp | **MODELO** | Conversão Kc/Kp sob estados padrão e gás ideal declarados. |
| Equilíbrio e pH | Tabela ICE | **MODELO** | Equilíbrio específico A+B⇌C em solução ideal. |
| Equilíbrio e pH | Ácidos e bases | **MODELO** | Balanço exato de concentração ideal; pH termodinâmico usa atividade. |
| Equilíbrio e pH | Tampão | **MODELO** | Balanço exato de concentração ideal; atividades≈concentrações. |
| Equilíbrio e pH | Curva de titulação | **MODELO** | Balanços de matéria/carga ideais a 25 °C. |
| Equilíbrio e pH | Especiação ácido-base | **MODELO** | Ácido monoprótico ideal. |
| Cinética química | Leis cinéticas integradas | **MODELO** | Lei integrada de uma única ordem e k constante. |
| Eletroquímica | Célula e Nernst | **MODELO** | Nernst é termodinâmico; Q deve ser construído com atividades. |
| Eletroquímica | Eletrólise · Faraday | **QUANTITATIVO** | Lei de Faraday com eficiência faradaica informada. |
| Estrutura atômica | Configuração eletrônica | **FORMAL** | Configuração orbital de referência; não é cálculo multieletrônico ab initio. |
| Estrutura atômica | Energia de fóton | **QUANTITATIVO** | Relações exatas E=hν=hc/λ com constantes definidas. |
| Estrutura atômica | Efeito fotoelétrico | **MODELO** | Modelo de Einstein com função trabalho informada. |
| Estrutura atômica | Transições de Bohr | **MODELO** | Somente espécies hidrogenoides de um elétron. |
| Espectroscopia | Beer–Lambert | **MODELO** | Beer–Lambert em meio homogêneo e faixa linear. |
| Espectroscopia | Calibração e regressão | **QUANTITATIVO** | OLS não ponderado; inferência estatística depende das hipóteses dos resíduos. |
| Estado sólido | Redes cristalinas cúbicas | **MODELO** | Célula cúbica ideal, ocupação completa. |
| Estado sólido | Lei de Bragg | **QUANTITATIVO** | Geometria nλ=2d sinθ para os dados fornecidos. |
| Química nuclear | Decaimento e meia-vida | **MODELO** | Lei exponencial macroscópica de decaimento. |
| Química nuclear | Transformação nuclear | **FORMAL** | Conserva A/Z; não prevê estabilidade, energia Q ou branching. |
| Química industrial | Etanol · biomassa | **MODELO** | Balanço ideal em equivalente de glicose e eficiência informada. |
| Química industrial | Brix e concentração | **MODELO** | °Brix tratado como fração mássica idealizada de sólidos solúveis. |

## Bancadas experimentais

| Bancada | Classe | O que é calculado | Limite principal |
|---|---|---|---|
| Pistão de gás ideal | MODELO | P, V, trabalho isotérmico e balanço energético | gás ideal; trajetória quase-estática imposta |
| Titulação | MODELO | pH por balanço de matéria/carga + Ka/Kw; curva completa | solução ideal, 25 °C, ácido monoprótico |
| Daniell sob corrente | MODELO | Faraday, composição e potencial reversível de Nernst | sem queda ôhmica, sobrepotencial ou transporte de massa |
| Calorimetria elétrica | MODELO | solução analítica de C dT/dt=P-k(T-Tamb) | C e k constantes; mistura homogênea |
| Haber | MODELO | propriedades Shomate, Kp(T), extensão Qp=Kp | gás ideal; sem fugacidade industrial |
| Beer–Lambert | MODELO | A e transmitância | região linear e meio homogêneo |
| Cinética 1ª ordem | MODELO | [A](t), fração e meia-vida | k constante e lei de 1ª ordem |
| Decaimento nuclear | MODELO | população esperada N(t) | modelo macroscópico; não prevê evento individual |

## Próximo nível científico

Antes de chamar o Nexum de ferramenta de pós-graduação em áreas específicas, os módulos seguintes devem ser adicionados como **novos modelos**, não como “mais precisão” sobre modelos simples:

- atividades e força iônica (Debye–Hückel/Davies/Pitzer conforme domínio);
- fugacidades e equilíbrio de fases com EOS apropriada;
- equilíbrio químico geral por minimização de Gibbs/material balance;
- cinética multirreacional e ajuste não linear com incerteza;
- tratamento de incerteza/metrologia e propagação covariante;
- especiação poliprótica/complexação/precipitação;
- eletroquímica não reversível (Butler–Volmer, iR, difusão) quando explicitamente modelada;
- análise espectroscópica com ponderação, LOD/LOQ e diagnóstico de resíduos;
- termodinâmica com Cp(T), fugacidade/atividade e bancos de dados rastreáveis.
## Backend avançado v6.5

| Núcleo | Modelo | Diagnóstico obrigatório | Limite declarado |
|---|---|---|---|
| Atividades | Debye–Hückel / Davies | força iônica, γ, validade | solução diluída; Davies não é Pitzer |
| Especiação | constantes de formação | balanço de componentes | ideal nesta função genérica |
| Equilíbrio | minimização de Gibbs | `||lnQ-lnK||∞` | ideal; atividades/fugacidades exigem modelo próprio |
| EOS | Peng–Robinson puro/mistura | raízes Z, φᵢ | depende de Tc/Pc/ω/kij |
| Flash TP | PR + Rachford–Rice | balanço material, igualdade de fugacidade | sem TPD global nesta versão |
| Cinética | rede de ação das massas | `nfev`, invariantes, concentração mínima | mecanismo é entrada, não inferência |
| Eletroquímica | Butler–Volmer | round-trip corrente↔η | transporte não incluído automaticamente |
| Transporte eletroquímico | Cottrell | lei `t^-1/2` | planar/semi-infinito/sem convecção |
| Metrologia | GUM | sensibilidades + covariância | linearização local |
| Metrologia | Monte Carlo | distribuição/intervalo | normal multivariada nesta implementação |
| Calibração | WLS | χ², covariância dos parâmetros | incerteza em x não incluída |
| Espectroscopia | Beer multicomponente | resíduo, RMSE, posto, condição | requer espectros de referência adequados |
| Protocolos | trajetórias calculadas | balanço específico por experimento | controle imposto ≠ cinética quando não há cinética |
