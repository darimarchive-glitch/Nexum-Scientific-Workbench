# Guia do laboratório

Abra **Laboratório** pela tela inicial ou pelo botão da barra superior. Ele complementa as calculadoras, bancadas e análises existentes. A janela lateral organiza um projeto de trabalho completo.

## Primeiro contato

1. Em **Projeto e caderno**, escolha **UV-Vis: concentração desconhecida** e clique em **Abrir exemplo**.
2. Leia a pergunta, as unidades e os dados conhecidos no caderno ou em **Investigações didáticas**.
3. Em **Dados e importação**, selecione a série, escolha **Calibração linear** como método de destino e envie para Análise. No exemplo UV-Vis, o sinal da amostra desconhecida também é transferido. Espectros e comparação de ordens cinéticas têm destinos próprios.
4. Use as ferramentas do laboratório para registrar resultados; salve o projeto e exporte o relatório.

Os exemplos são simulados, nunca resultados de um equipamento real. O gabarito faz parte do arquivo: as investigações são atividades formativas, não provas protegidas.

## Projeto, caderno e recuperação

O arquivo `.nexum7` contém dados, resultados, desenhos, molécula associada, atribuições, cenas e registro de operações. Ao salvar manualmente, o estado principal do aplicativo também é incluído. A recuperação automática guarda as alterações do laboratório a cada 20 segundos quando não existe cálculo em andamento; ela não captura continuamente todos os controles da janela principal.

O salvamento escreve primeiro um arquivo temporário e só então substitui o destino. Um hash SHA-256 verifica corrupção. Esse hash não é assinatura digital nem prova de autoria. Mantenha cópias independentes dos trabalhos importantes.

Desfazer/refazer mantém até 15 alterações, limitado por orçamento de memória; projetos grandes podem ter menos etapas disponíveis. Recuperar última cópia procura o projeto anterior mais recente. Abrir um projeto não autoriza execução de extensões Python.

## Dados e importação

CSV/TSV: escolha cabeçalho, separador, decimal e colunas X/Y. Os índices começam em 1. O arquivo deve ter dados numéricos retangulares; linhas ausentes ou inválidas geram erro. Os pontos são ordenados por X; X repetido é rejeitado. Organize réplicas em séries separadas ou colunas distintas.

O lote importa até 32 arquivos com o mesmo formato. Se um falhar, o lote não é parcialmente adicionado. Limites: 12 MB por arquivo, 100.000 pontos por série e 48 MiB de conteúdo por projeto. Arquivos originais ficam incorporados com hash. Os CSV exportados usam ponto e vírgula e vírgula decimal.

JCAMP aceita somente XYPOINTS explícito, sem compressão, com fatores XFACTOR/YFACTOR. XYDATA comprimido, NTUPLES e formatos proprietários não estão implementados. Exporte CSV no software do instrumento quando necessário.

## Editor molecular

Carregue SMILES ou desenhe: escolha elemento, ação e ordem da ligação. No modo adicionar, um novo átomo é ligado ao selecionado. Use selecionar para soltar a seleção antes de iniciar outra parte. Cargas formais podem ser alteradas no átomo selecionado; ligações aromáticas do SMILES são mostradas com traço interrompido.

**Gerar e abrir em 3D** verifica a conectividade e cria uma geometria ETKDGv3, minimizada por MMFF94 ou UFF. O editor limita-se a 200 átomos e uma espécie conectada por geração. Geometrias com átomos sem parâmetros ou valência inválida são recusadas. A configuração estereoquímica especificada somente em SMILES não é preservada pelo editor simplificado: moléculas com estereoquímica explícita são recusadas; use importação estrutural para esses casos.

A alteração do desenho invalida a geometria associada ao laboratório. Gere novamente o 3D antes de fazer atribuições espectrais. **Usar estrutura 3D atual** associa a estrutura para análise; não transforma automaticamente qualquer macromolécula importada em um desenho editável.

Conformeros são candidatos gerados por amostragem, não uma busca exaustiva. A energia relativa só compara candidatos do mesmo sistema e campo de força; não representa energia livre nem população experimental. A convergência da minimização é informada.

## Alinhamento e espectros

Fixe a referência, associe a segunda estrutura e calcule RMSD. A correspondência automática exige a mesma sequência de elementos e usa átomos não H. Isso não prova equivalência topológica. Para outros casos, informe pares `1:1, 2:2, 3:3`. São exigidas três correspondências não colineares. O ajuste é rígido e não faz alinhamento de sequência de proteínas.

Em **Espectro e molécula**, clique no gráfico para sugerir uma região, ajuste limites, selecione átomos e registre a interpretação. A atribuição é manual. Cada registro guarda a versão da molécula e a série; se a molécula mudar, o aplicativo não aplica silenciosamente a seleção antiga à nova estrutura.

## Fluxos de análise

Adicione etapas, mude sua ordem e execute na série selecionada ou em todas. As saídas aparecem como novas séries. A origem continua disponível. Fluxos `.nexumflow` guardam etapas e parâmetros, sem código executável.

- Linha de base: reta entre extremos; não é uma identificação automática de fundo.
- Suavização: Savitzky–Golay, janela ímpar e espaçamento uniforme de X.
- Derivada: diferenças finitas; amplifica ruído.
- Integração: trapézios com interpolação nos limites.
- Calibração: inversão de uma reta fornecida; essa etapa não propaga incerteza de calibração.

## Planejamento, qualidade e processos

**Planejamento:** fatores em linhas `nome; mínimo; máximo`; gere a ordem e preencha apenas a resposta da última coluna. O ajuste usa efeitos principais e interações de dois fatores. Réplicas dão graus de liberdade, mas não corrigem um modelo inadequado. O gráfico de resíduos deve ser examinado junto de R².

**Qualidade:** informe valor alvo, σ de referência e, se houver, os dois limites de especificação. O aplicativo não escolhe critérios de aceitação. Um ponto fora de ±3σ não é automaticamente uma amostra fora da especificação.

**Processos:** cada operação recebe saídas anteriores pelos nomes. O divisor fornece `nome` e `nome:rest`. Uma corrente não pode ser consumida duas vezes; use um divisor. A mistura conserva massa e usa cp constante. A conversão A→B usa razão mássica 1:1 e não representa um reator estequiométrico geral. As operações são adicionadas por formulário; o fluxograma é desenhado a partir delas, sem edição por arrastar/conectar nesta prévia.

## Modelos e incerteza

Escolha diluição, Beer–Lambert, cinética de primeira ordem ou gás ideal. Use as unidades indicadas. Informe incertezas **padrão**, não amplitudes de tolerância sem conversão. As três correlações precisam formar uma matriz válida.

Compare o resultado nominal, a incerteza linear e a distribuição Monte Carlo. O efeito de aumentar cada entrada em uma incerteza padrão indica sensibilidade local; não é uma porcentagem universal de importância, especialmente com correlações. Amostras fora do domínio físico provocam erro, em vez de serem excluídas silenciosamente.

O diagrama ácido–base mostra como HA e A⁻ se repartem em função de um pH fornecido. Ele não calcula o pH de uma solução a partir de massa e volume nem corrige força iônica.

## Cenas, relatórios e extensões

Capture uma cena após ajustar o visualizador principal. A cena guarda imagem e estado de câmera/representação; a apresentação HTML funciona sem o Nexum. O GIF é uma rotação de câmera, não dinâmica molecular. Relatórios HTML incluem gráficos SVG e podem ser impressos em PDF pelo navegador.

A extensão Python recebe `payload['dataset']` e retorna um objeto serializável em JSON. Ela roda em processo separado e precisa ser revisada e autorizada. Processo separado não é uma barreira de segurança: o código pode acessar arquivos disponíveis ao aplicativo. No Windows empacotado, é necessário selecionar um Python externo para esse recurso opcional; as funções normais do Nexum não precisam desse Python externo.
