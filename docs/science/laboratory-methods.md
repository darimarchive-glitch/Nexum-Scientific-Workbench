# Métodos científicos do laboratório

A precisão numérica é avaliada por referências analíticas, conservação e regressões. A validade de uma conclusão depende adicionalmente das hipóteses físicas, qualidade da medição e adequação estatística. Esta entrega não recebeu uma auditoria universitária independente.

## Incerteza e sensibilidade

Para y=f(x), a aproximação de primeira ordem usa u²(y)=JΣJᵀ, com J formado pelas derivadas analíticas e Σ pela covariância das entradas. O usuário informa incertezas padrão e correlações; a matriz precisa ser simétrica, ter diagonal unitária e ser semidefinida positiva.

A simulação usa 20.000 amostras normais correlacionadas na interface, com semente registrada. O intervalo apresentado usa quantis 2,5% e 97,5%. Não pressupõe que U=2u tenha cobertura exata de 95%. A comparação entre a aproximação linear e a simulação ajuda a identificar efeitos de não linearidade; não demonstra ausência de erro de modelo.

Modelos implementados: diluição C₂=C₁V₁/V₂; Beer–Lambert c=A/(εl); primeira ordem k=ln(C₀/C)/t; gás ideal n=PV/(RT). O valor de R é N_Ak_B=8,31446261815324 J mol⁻¹ K⁻¹, produto das constantes definidoras do SI. Pressão e temperatura no modelo de gás são absolutas.

Nenhuma distribuição é truncada silenciosamente para caber no domínio. Caso uma amostra gere entrada não física, o cálculo pede revisão das distribuições. O uso de gaussianas perto de zero não deve ser corrigido apenas aumentando o número de amostras.

Referências: [JCGM 100:2008](https://www.bipm.org/documents/20126/2071204/JCGM_100_2008_E.pdf), [JCGM 101:2008](https://www.bipm.org/documents/20126/2071204/JCGM_101_2008_E.pdf), [NIST/CODATA — R](https://physics.nist.gov/cgi-bin/cuu/Value?r=).

## Distribuição ácido–base

Para HA ⇌ H⁺ + A⁻, sob aproximação ideal, αHA=1/(1+10^(pH−pKa)) e αA⁻=1/(1+10^(pKa−pH)). As duas expressões evitam obter frações muito pequenas pela subtração de números quase iguais. Testam-se conservação da soma e frações iguais em pH=pKa.

O pH é um eixo fornecido. O modelo não substitui um balanço de carga para calcular pH, não cobre ácidos polipróticos e não incorpora atividades dependentes da força iônica. A aba Análise possui a ferramenta de titulação poliprótica separadamente.

Referência: [IUPAC Gold Book — Henderson–Hasselbalch](https://goldbook.iupac.org/terms/view/H02781).

## Geometria molecular

RDKit realiza sanitização de valência/aromaticidade, geração ETKDGv3 e minimização MMFF94, com UFF como alternativa quando há parâmetros. O status de convergência é armazenado. O editor simplificado não modela explicitamente quiralidade, isótopos ou geometria de coordenação; entradas que exigem estereoquímica/isótopos explícitos são recusadas para impedir perda silenciosa dessas informações. Use os importadores estruturais para esse escopo.

Conformeros compartilham composição e campo de força. ΔE não é ΔG. Não existe cálculo quântico, otimização de estado eletrônico, solvatação explícita ou validação experimental de estrutura neste recurso.

O RMSD usa Kabsch sem reflexão, em float64, com correspondência fornecida ou por índice. A correspondência por elementos não resolve simetrias ou mapeamento químico. A comparação de estruturas distintas exige revisão manual dos pares. Três pontos colineares não definem orientação única e são recusados.

Referências técnicas: [RDKit Book](https://www.rdkit.org/docs/RDKit_Book.html) e [RDKit: geração de coordenadas e campos de força](https://www.rdkit.org/docs/GettingStartedInPython.html).

## Dados e sinais

Os originais permanecem incorporados ao projeto. Operações produzem novas séries e rastros com parâmetros/hashes. Savitzky–Golay exige amostragem uniforme; as derivadas usam diferenças finitas, e as integrais usam trapézios com limites interpolados. Suavizar ou corrigir uma linha de base pode alterar áreas e picos: essas escolhas ficam registradas, não são correções universais.

As atribuições espectrais são manuais. Nenhuma correlação espectro–átomo exibida comprova identidade molecular ou mecanismo. O resultado guarda o hash da versão da molécula para impedir correspondências silenciosamente obsoletas.

## Planejamento e controle

O planejamento fatorial completo usa fatores codificados −1/+1, centros zero e ordem pseudoaleatória com semente. O ajuste inclui intercepto, efeitos principais e interações de dois fatores. Intervalos de confiança t dependem das hipóteses usuais de erro do modelo linear; R² alto não demonstra causalidade nem ausência de falta de ajuste. Pontos centrais não identificam termos quadráticos separados.

Controle de qualidade usa alvo e σ fornecidos. Limites ±3σ são de controle; especificações são critérios distintos. RSD usa desvio padrão amostral dividido pelo módulo da média, e não é apresentado quando a média é próxima de zero. Recuperação exige resultados na mesma unidade e base de diluição.

## Processos

O fluxograma é acíclico e estacionário. Os testes conferem conservação de massa total, componentes na mistura/divisão e energia sensível com cp constante. A conversão A→B usa rendimento mássico 1:1, sem cinética, calor de reação, equilíbrio de fases ou estequiometria molar geral. As calculadoras industriais existentes continuam separadas.

## Rastreabilidade

O relatório inclui origem, método, parâmetros, séries, hashes e registro de ações. Hash não é assinatura, autenticação ou garantia de correção científica. Resultados de extensões locais são identificados como não auditados. As limitações específicas devem acompanhar qualquer figura ou tabela exportada usada em aula, relatório ou publicação.
