# Nexum Scientific Workbench v6.6 — Bancadas didáticas

- Bancadas de titulação, Daniell, calorimetria, equilíbrio, Beer–Lambert, cinética e decaimento refeitas em Cairo, com os valores ligados aos elementos do desenho.
- Erlenmeyer com enchimento calculado pela geometria cônica, indicadores e ponto da titulação no gráfico.
- Remoção dos botões redundantes de equilíbrio e Beer–Lambert; atualização explícita ao editar.
- Reprodução, pausa, avanço manual e navegação no tempo compartilham uma sessão; trocar parâmetros reinicia a trajetória.
- Curvas calculadas uma vez por configuração e linhas de medição reaproveitadas entre quadros.
- Entradas inválidas são indicadas na página e desabilitam a reprodução; nenhuma medição antiga é apresentada como atual.
- Corrente zero, fonte apagada, reagente ausente, esgotamento de Cu²⁺ e meia-vida infinita tratados explicitamente.
- Correção de cancelamento numérico no cálculo do pH após excesso de base.
- Nomenclatura do registro numérico padronizada como `ScientificEngine` / `default_engine` em `core/engine.py` e `core/advanced/engine.py`; imports e documentação atualizados.
- Testes científicos existentes preservados; novos testes de comportamento, Cairo e GTK.

---

# Nexum Scientific Workbench v6.5 — Scientific Engine

## Escopo desta versão

Nenhuma reformulação visual. A interface GNOME da v6.0 é preservada. A v6.5 trabalha exclusivamente no backend científico e na rastreabilidade dos cálculos.

## Novo motor científico

- `ScientificEngine` + `SolverSpec` + `CalculationTrace`.
- Presets são formalmente apenas entradas; nenhum contrato de solver possui resposta esperada embutida.
- Rastreamento de entradas, modelo, equações, hipóteses, validade, tempo e diagnósticos numéricos.

## Soluções e equilíbrio

- Debye–Hückel limite/estendido e Davies.
- Força iônica auto-consistente para especiação poliprótica.
- Solver genérico de complexação por constantes globais de formação.
- Equilíbrio multirreacional ideal por minimização de Gibbs.
- Gradiente analítico + refinamento Newton de afinidades, corrigindo falsa convergência próxima à fronteira de não negatividade.

## Gases e fases

- Peng–Robinson puro e mistura.
- Coeficientes de fugacidade por componente.
- Rachford–Rice.
- Flash TP `φ-φ` iterativo com balanço material e resíduo de fugacidade.

## Cinética

- Redes arbitrárias de ação das massas por ODE.
- Reversibilidade.
- Arrhenius calculado a partir de A/Ea/T.
- Diagnóstico de invariantes estequiométricos.

## Eletroquímica

- Butler–Volmer.
- Inversão de Butler–Volmer.
- Eletrodo polarizado com `η + iR`.
- Cottrell.

## Metrologia e espectroscopia

- GUM matricial.
- Monte Carlo multivariado.
- Covariância validada como simétrica e semidefinida positiva.
- Regressão ponderada.
- Beer multicomponente LS/NNLS com condicionamento.

## Experimentos

- Nova camada `advanced/protocols.py`: trajetórias calculadas quadro a quadro a partir de controles reais.
- Testes metamórficos garantem que mudanças de parâmetros alterem estados por meio do modelo, e não por resultados pré-selecionados.

## Dependências

- SciPy passa a ser dependência explícita da v6.5.

## Testes

- v6.0: 100 testes.
- v6.5: 134 testes.
