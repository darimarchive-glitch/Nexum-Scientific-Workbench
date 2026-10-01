# Histórico de alterações

## 7.0.0 — estável

- Primeira release estável da série 7.
- Versão, metadados, nomes de artefatos e empacotadores alinhados em `7.0.0`.
- Pipeline de release passa a distinguir automaticamente versões estáveis de previews/RCs.
- Release só é publicada após testes científicos e builds nativos de Windows, Flatpak e macOS.
- Instalador Windows passa a exibir a licença proprietária; DMG macOS inclui uma cópia visível da licença.
- Licença do projeto promovida para proprietária/source-available, preservando direitos já concedidos em versões anteriormente publicadas sob MIT.
- README, documentação de distribuição, suporte, segurança e licenciamento comercial reorganizados para refletir o estado atual.
- Referências internas antigas do motor v6.5 removidas do código ativo sem alterar os algoritmos científicos.
- `CFBundleVersion` do macOS avançado para 70003, mantendo a progressão após a preview.2.

## 7.0.0-preview.2 — aparência

- Janela inicial respeita o tamanho do monitor; navegação compacta em larguras menores.
- Tema global Sistema/Claro/Escuro com preferência persistida.
- Presets moleculares preservam o tema e atualizam o painel lateral.
- Comparações 3D acompanham o tema; fundo usa a cor do GTK.
- Sessões e aparência reunidas no menu; botão redundante de câmera removido.
- Regressões GTK e captura da janela nos dois temas no CI Windows.

## 7.0.0-preview.1 — laboratório integrado

- Laboratório integrado com projetos, caderno, recuperação, dados originais e desfazer/refazer.
- Editor 2D/3D, conformeros, alinhamento RMSD e atribuições espectrais manuais.
- Importação tabular/JCAMP, fluxos reutilizáveis, planejamento fatorial e qualidade.
- Processos estacionários simples, investigações, cenas, GIF, apresentações e relatórios.
- Modelos de incerteza correlacionada, Monte Carlo, sensibilidade e distribuição ácido–base.
- Nomes de pacotes centralizados, documentação reorganizada e publicador obsoleto removido.
- Aplicativos nativos e instaladores verificados em CI: Windows, Flatpak e macOS Intel/Apple Silicon.

## 6.8.1 — compatibilidade gráfica no Windows

- Fallback Mesa/llvmpipe para máquinas em que o OpenGL nativo não inicializa corretamente.
- Diagnósticos gráficos e validação da cópia instalada.
- Consulte [notas 6.8.1](docs/releases/6.8.1.md).

## 6.8.0 — distribuição desktop

- Instalador Windows e bundle Flatpak com identidade visual e atalhos.
- Ferramentas de moléculas, análise, experimentos e busca em português consolidadas.
- Consulte [notas 6.8.0](docs/releases/6.8.0.md).

## 6.6 — bancadas e comportamento

- Bancadas de titulação, Daniell, calorimetria, equilíbrio, Beer–Lambert, cinética e decaimento refeitas em Cairo.
- Reprodução, pausa, avanço manual e navegação temporal passam a compartilhar uma sessão.
- Entradas inválidas deixam de exibir medições antigas como atuais.
- Casos-limite de corrente, reagentes, Cu²⁺ e meia-vida tratados explicitamente.
- Correção de cancelamento numérico no cálculo de pH após excesso de base.
- Registro numérico padronizado como `ScientificEngine` / `default_engine`.

## 6.5 — Scientific Engine

- `ScientificEngine`, `SolverSpec` e `CalculationTrace`.
- Debye–Hückel, Davies, especiação poliprótica, complexação e equilíbrio por minimização de Gibbs.
- Peng–Robinson, Rachford–Rice e flash TP φ-φ.
- Redes cinéticas por ODE, Arrhenius e invariantes estequiométricos.
- Butler–Volmer, Cottrell, GUM matricial, Monte Carlo, regressão ponderada e Beer multicomponente.
- SciPy tornou-se dependência explícita.
