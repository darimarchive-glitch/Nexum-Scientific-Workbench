# Extensões científicas e distribuição desktop

## Avaliação do projeto

A base já separa os modelos científicos da interface GTK4/libadwaita, mantém o histórico em SQLite e apresenta equações, unidades e hipóteses junto dos resultados. A bancada usa estados calculados, e não animação independente dos modelos. Esse padrão foi mantido.

Os pontos corrigidos nesta alteração são a consulta molecular sem vocabulário brasileiro, a ausência das derivadas na interface de titulação e a distribuição Windows dependente de uma instalação manual de Python/MSYS2. A suíte existente cobre numerosos modelos, mas não substitui validação em equipamentos reais nem estabelece precisão universal.

## Ferramentas

- Titulação simulada: três gráficos separados (pH, primeira derivada e segunda derivada).
- Derivadas experimentais em Estequiometria: pares `volume,pH;volume,pH`, com ponto decimal; volumes estritamente crescentes, inclusive com espaçamento irregular. Usa diferenças divididas nos pontos médios. A estimativa usa uma mudança de sinal da segunda derivada próxima de um pico interno de |primeira derivada|; não certifica equivalência química nem suaviza ruído automaticamente.
- Combustão de hidrocarbonetos: ar teórico, excesso, conversão, vazões molares e composição úmida da saída. A parcela convertida forma somente CO₂ e H₂O; não simula combustão incompleta com CO/fuligem.
- CSTR/PFR: dimensionamento de reatores ideais de primeira ordem.
- Unidades espectrais: comprimento de onda, frequência, número de onda e energia.
- Espectrometria de massas: erro em ppm e resolução por FWHM.
- Experimentos: partida de CSTR e cinética por espectrofotometria, com controles, bancada, métricas e curvas calculadas.

## Busca brasileira

Vocabulário local com nomes brasileiros, sinônimos, fórmulas e CID. Água, agua, water, H₂O e H2O identificam o CID 962 sem depender do autocomplete remoto. Sugestões toleram um erro de edição; erros nunca são convertidos silenciosamente em outra identidade química.

O vocabulário inicial contém 21 compostos, não todo o PubChem. Para registros sem tradução revisada, a interface mostra “Composto + fórmula” e mantém o nome original como informação secundária. Isso evita apresentar traduções inventadas. O catálogo pode ser ampliado em `nexum/core/molecule_names.py`. O carregamento da estrutura ainda requer rede quando não existe cache. Títulos de macromoléculas RCSB continuam na língua original.

## Windows

`packaging/windows/build.ps1` cria dois bundles PyInstaller: interface GTK e motor químico CPython. O worker empacotado é chamado por JSON, sem interpretador externo instalado. Em seguida executa o autoteste do aplicativo congelado e compila um instalador Inno Setup por usuário, com desinstalador e atalhos. A instalação não exige Python, MSYS2 ou privilégios de administrador no computador final.

O fluxo **Build desktop installers** em GitHub Actions prepara as dependências, verifica o bundle e disponibiliza `Nexum-Setup-6.7.0-x64.exe` como artefato se a compilação passar. O autoteste cobre GTK, OpenGL, RDKit, gemmi e histórico. Ainda é necessário testar instalação, atualização e desinstalação em um Windows limpo, sem ferramentas de desenvolvimento. Os pacotes não possuem assinatura digital configurada.

## Linux / Flatpak

Em Linux x86_64, execute `bash packaging/flatpak/build.sh` com Flatpak e flatpak-builder instalados. O script usa GNOME 49, resolve wheels com o Python do próprio SDK e faz a instalação das dependências offline no builder. O aplicativo próprio é distribuído como arquivo de bytecode, sem a árvore de arquivos `.py`. As dependências conservam os arquivos necessários de suas distribuições.

Saída: `dist/Nexum-x86_64.flatpak`.

Instalação pelo usuário: `flatpak install --user Nexum-x86_64.flatpak`.

Abertura: `flatpak run io.github.nexum.ScientificWorkbench`.

Acesso à rede atende PubChem/RCSB; acesso gráfico usa Wayland/X11 e DRI. Não concede acesso geral aos arquivos do computador. Histórico/cache seguem XDG dentro do sandbox. O bundle ainda depende do runtime Flatpak, obtido do Flathub. Este fluxo **não publica o aplicativo no Flathub**; submissão à loja exige metadados, revisão e um fluxo de distribuição apropriado. Os hashes dos wheels usados acompanham o bundle; o resolvedor ainda usa os intervalos do requirements.txt, portanto builds futuros podem selecionar versões diferentes.

## Código e distribuição

Instaladores, bytecode e PyInstaller evitam entregar a árvore de desenvolvimento como interface ao usuário, mas permitem extração e engenharia reversa. Não são criptografia nem licenciamento. Segredos devem permanecer fora do programa distribuído. A licença existente do repositório não foi alterada; tampouco foram introduzidos pagamentos ou validação de licenças. Avisos/licenças das dependências devem acompanhar sua redistribuição.

## Referências de empacotamento

- https://pyinstaller.org/en/stable/hooks-config.html
- https://packages.msys2.org/packages/mingw-w64-ucrt-x86_64-pyinstaller
- https://jrsoftware.org/ishelp/topic_compilercmdline.htm
- https://docs.flatpak.org/en/latest/first-build.html
- https://docs.flatpak.org/en/latest/python.html
