# Arquitetura do motor científico — v6.5

## 1. Fluxo obrigatório

`entrada atual → validação → formulação do modelo → solver → resíduos/conservação → resultado → trace`

Um preset termina na primeira etapa. Ele nunca contém o valor que o solver deverá produzir.

## 2. Contrato de solver

Cada solver avançado possui:
- nome e chave estável;
- modelo declarado;
- equações documentais;
- hipóteses;
- domínio/limitações;
- função executável.

`ScientificEngine.solve()` copia os dados submetidos, executa a função e cria `CalculationTrace`.

## 3. Diagnósticos numéricos

### Raízes e equilíbrio
- solução em espaço logarítmico quando a variável atravessa muitas ordens de grandeza;
- resíduos de eletroneutralidade/afinidade;
- iterações;
- restrição de não negatividade.

### ODEs cinéticas
- `BDF` disponível para redes stiff;
- `rtol`/`atol` controláveis;
- `nfev`;
- erro máximo dos invariantes lineares obtidos do null-space de `Nᵀ`.

### Equilíbrio de fases
- raízes físicas de `Z`;
- coeficientes de fugacidade;
- Rachford–Rice;
- igualdade `f_i^L=f_i^V`;
- fechamento `z=(1-β)x+βy`.

### Metrologia
- matriz de covariância validada;
- sensibilidades;
- propagação linear e Monte Carlo;
- regressão ponderada com `χ²`.

## 4. Separação entre matemática e interface

Nenhum módulo em `nexum/core/advanced` importa GTK. Assim, o mesmo cálculo pode ser:
- testado em linha de comando;
- usado por calculadora;
- usado por experimento;
- executado em lote;
- futuramente exposto a notebook/API local;
sem duplicar a química.

## 5. Experimento não é animação

`advanced/protocols.py` recebe controles reais do protocolo e calcula todos os estados. A animação é apenas uma visualização desse vetor de estados.

Exemplo de titulação:

`tempo → vazão × tempo → volume de titulante → balanço de matéria/carga → [H+] → pH → quadro`

Não existe `pH_inicial + progresso × (pH_final-pH_inicial)`.

## 6. Política de precisão

Precisão numérica não corrige modelo inadequado. Por isso resultado e validade são duas saídas diferentes.

Exemplos:
- Davies pode convergir numericamente em força iônica onde não deveria ser usado; o backend marca a extrapolação.
- Peng–Robinson pode convergir sem um teste global de estabilidade; o backend informa essa limitação.
- Butler–Volmer não ganha transporte de massa fictício; Cottrell/transportes precisam ser acoplados explicitamente.


## 7. Sessão e desenho da bancada — v6.6

`core/experiment_session.py` valida a configuração, amostra as funções de `core/experiments.py`, calcula uma curva de referência e mantém o tempo/estado atual. O histórico visível é a parte dessa curva até o instante escolhido, mais o estado exato do cursor. Alterar parâmetros constrói outra sessão e elimina a trajetória anterior.

`ui/experiments_page.py` conecta controles GTK a essa sessão. Medições são atualizadas sem reconstruir os widgets a cada quadro. Trocar de experimento ou ocultar a página interrompe o timer GLib.

`ui/experiment_drawing.py` desenha vidrarias, aparelhos, populações e gráficos usando exclusivamente os valores da sessão. Pode ser renderizado sem GTK com Cairo, como nos testes de regressão visual. Cores e movimentos esquemáticos são identificados como tais na interface; não alteram os cálculos.

Equilíbrio é uma comparação de estados; Beer–Lambert é uma relação estática entre parâmetros e leitura teórica. Nenhum deles utiliza uma cronologia de reação fictícia.
