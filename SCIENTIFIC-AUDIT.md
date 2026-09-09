# Auditoria científica — Nexum GNOME / Fedora v6.5

## Objetivo

A v6.5 abandona a ideia de que um cálculo é “validado” só porque reproduz um exemplo. O backend deve satisfazer três camadas simultâneas:

1. **equação/modelo correto**;
2. **solver numérico convergente e diagnosticável**;
3. **conservações/resíduos compatíveis com o modelo**.

Um resultado pode estar numericamente convergido e ainda estar fora do domínio físico do modelo; por isso convergência e validade são reportadas separadamente.

## Referências primárias de base

- NIST/CODATA 2022: constantes fundamentais `R` e `F`.
- IUPAC Gold Book: atividade, potencial químico, equilíbrio químico e constante de equilíbrio.
- IUPAC Gold Book: Debye–Hückel e Cottrell.
- NIST Chemistry WebBook: forma de Shomate e coeficientes termodinâmicos usados nos benchmarks.

## Atividades

O backend trata atividade como grandeza distinta de concentração. Debye–Hückel/Davies são modelos aproximados; não são usados para fingir exatidão em alta força iônica. O solver ácido-base calcula força iônica de forma auto-consistente e retorna a mensagem de validade do modelo escolhido.

## Equilíbrio

### Especiação por formação

O solver recebe totais analíticos, matriz de formação e `β`. As concentrações livres são incógnitas em espaço logarítmico; espécies formadas são calculadas por ação das massas. A solução fecha os balanços de componentes e retorna o resíduo máximo escalado.

### Equilíbrio multirreacional

O estado é obtido por minimização de Gibbs sob não negatividade e refinado por Newton diretamente nas afinidades `lnQ-lnK`. O gradiente analítico evita a falsa convergência na fronteira que foi descoberta durante a auditoria desta própria versão.

## Equações de estado e fases

Peng–Robinson usa as raízes físicas `Z>B`, regras de mistura quadráticas e coeficientes de fugacidade. O flash TP combina Wilson somente como chute inicial, Rachford–Rice para balanço de fase e atualização `K=φL/φV` até a igualdade de fugacidades.

Limitação explícita: ainda não há análise global de estabilidade por tangent-plane distance. Portanto um estado monofásico indicado pela inicialização/flash não deve ser tratado como prova matemática global de estabilidade de fase.

## Cinética

Redes de ação das massas usam a matriz estequiométrica e são integradas com SciPy `solve_ivp`, com BDF disponível para stiffness. O backend mede invariantes lineares a partir do null-space de `Nᵀ`. Arrhenius calcula as constantes a partir dos parâmetros fornecidos; não infere mecanismo.

## Eletroquímica

Butler–Volmer é implementado direta e inversamente. A inversão encontra o sobrepotencial por raiz numérica. O modelo de eletrodo polarizado soma `Eeq + η + iR`, mantendo transporte de massa fora do modelo em vez de escondê-lo em parâmetros artificiais. Cottrell é tratado somente sob suas hipóteses de difusão planar semi-infinita.

## Metrologia

GUM usa matriz de covariância e coeficientes de sensibilidade. A matriz é rejeitada se não for finita, simétrica ou semidefinida positiva. Monte Carlo fornece distribuição empírica da grandeza de saída. Regressão ponderada retorna covariância dos coeficientes e estatística χ².

## Espectroscopia

Beer–Lambert multicomponente é resolvido por LS/NNLS. O número de condição é retornado porque uma solução algébrica com matriz quase colinear pode ser numericamente frágil mesmo com resíduo pequeno.

## Experimentos calculados

Os protocolos da v6.5 obedecem:

`controle experimental → estado físico/químico → diagnóstico → quadro visual`

Não há interpolação de resultado químico entre dois números previamente escolhidos.

Exemplos:
- titulação: `V_b(t)=vazão×t`, depois novo balanço ácido-base em cada ponto;
- Daniell: `q=It`, `ξ=q/(2F)`, nova composição e novo Nernst em cada ponto;
- calorimetria: balanço de energia em cada instante;
- gás: cada quadro satisfaz `pV=nRT`;
- cinética/decaimento: cada quadro vem da lei temporal correspondente.

## Validação automatizada

A entrega executa **134 testes**, incluindo a suíte completa da v6.0 mais 34 testes específicos da v6.5.

Os novos testes incluem referências analíticas, round-trips, resíduos, fechamento material, igualdade de fugacidades, invariantes de ODE e testes metamórficos contra resultados pré-moldados.

## O que ainda não deve ser prometido

Mesmo este backend não é “toda a química de doutorado”. Para problemas específicos podem ser necessários bancos de parâmetros e modelos externos: Pitzer/SIT, propriedades críticas/`kij` validadas, SAFT/CPA, teste rigoroso de estabilidade, eletroquímica com transporte acoplado, mecanismos cinéticos experimentais, modelos de superfície, DFT/ab initio, dinâmica molecular e bases termodinâmicas especializadas.

A política do Nexum é não inventar esses dados. Quando faltarem, o modelo deve dizer que faltam.
