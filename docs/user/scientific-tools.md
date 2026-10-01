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

`packaging/windows/build.ps1` cria dois bundles PyInstaller: interface GTK e motor químico CPython. O worker empacotado é chamado por JSON, sem interpretador externo instalado. O instalador Inno Setup é produzido por usuário, inclui a licença proprietária, cria desinstalador e atalhos e não exige Python ou MSYS2 no computador final.

O fluxo **Build desktop installers** executa testes, compila o bundle, instala o EXE gerado em uma pasta limpa e executa o self-test da cópia instalada com PATH restrito. O artefato segue o padrão `Nexum-<versão>-windows-x86_64-setup.exe`.

Os binários públicos ainda não possuem assinatura Authenticode configurada. Isso não impede o teste funcional, mas pode gerar avisos do Windows e precisa ser tratado antes de uma distribuição comercial de maior escala.

## Linux / Flatpak

Em Linux x86_64, execute `bash packaging/flatpak/build.sh` com Flatpak e flatpak-builder instalados. O script usa o runtime GNOME 50, resolve as dependências no SDK e compila o aplicativo para um bundle Flatpak independente. A etapa do builder roda sem rede depois que os insumos são preparados.

Saída: `dist/Nexum-<versão>-linux-x86_64.flatpak`.

Instalação pelo usuário:

```bash
flatpak install --user ./Nexum-<versão>-linux-x86_64.flatpak
```

Abertura:

```bash
flatpak run io.github.nexum.ScientificWorkbench
```

Acesso à rede atende buscas externas; acesso gráfico usa Wayland/X11 e DRI. O bundle não concede acesso geral à pasta pessoal. Histórico e cache seguem XDG dentro do sandbox. Este fluxo produz um pacote independente; publicação no catálogo Flathub continua sendo uma etapa separada.

## Código, licença e distribuição

Instaladores, bytecode e PyInstaller dificultam a exposição casual da árvore de desenvolvimento, mas não são criptografia nem impedem engenharia reversa. Segredos devem permanecer fora do aplicativo distribuído.

A partir da série estável 7.0.0, o Nexum é distribuído sob licença proprietária. Uso institucional, comercial, laboratorial, organizacional, redistribuição, integração em outros produtos e serviços hospedados exigem autorização específica do mantenedor. Dependências de terceiros continuam sujeitas às respectivas licenças e avisos.

## Referências de empacotamento

- https://pyinstaller.org/en/stable/hooks-config.html
- https://packages.msys2.org/packages/mingw-w64-ucrt-x86_64-pyinstaller
- https://jrsoftware.org/ishelp/topic_compilercmdline.htm
- https://docs.flatpak.org/en/latest/first-build.html
- https://docs.flatpak.org/en/latest/python.html

