# Auditoria de preparação para o Flathub

> **Registro histórico:** esta auditoria retrata a preview.2 em 28 de setembro de 2026. Ela é preservada para rastreabilidade e não descreve, sozinha, o estado da release estável 7.0.0. As lacunas de identidade, screenshots e submissão ao Flathub continuam devendo ser verificadas separadamente.

Data: 28 de setembro de 2026. Base examinada: `c5d35fda97a7b177d2a3ac5f98a1f2016ad934a2`, versão `7.0.0-preview.2`.

Este documento registra uma auditoria técnica do projeto feita com assistência de IA. Não é um manifesto, um pacote de submissão ou um texto para copiar em um pull request do Flathub. A preparação completa para a loja ainda está pendente. Consulte também as [restrições e referências oficiais](flathub.md).

## Arquivos que existem hoje

Os caminhos abaixo são relativos à raiz deste repositório.

| Componente | Arquivo | Situação observada |
| --- | --- | --- |
| Identidade e versão | `nexum/identity.py` | ID legada `io.github.nexum.ScientificWorkbench`; versão de desenvolvimento. |
| Receita independente | `packaging/flatpak/io.github.nexum.ScientificWorkbench.json` | GNOME 50; fonte local gerada; dependências em wheels. |
| Preparação e compilação | `packaging/flatpak/build.sh` | Baixa wheels usando o Python do SDK; prepara `build/flatpak-input`; gera bundle independente. |
| Instalação interna | `packaging/flatpak/install.py` | Gera arquivo Python compilado; instala recursos e registro dos wheels. |
| Comando de execução | `packaging/flatpak/nexum` | Inicia o aplicativo instalado em `/app`. |
| Integração com o menu | `packaging/flatpak/io.github.nexum.ScientificWorkbench.desktop` | Comando, ícone, categorias e palavras-chave presentes. |
| Catálogo de aplicativos | `packaging/flatpak/io.github.nexum.ScientificWorkbench.metainfo.xml` | Descrições em inglês e português; não contém screenshots. |
| Logo oficial | `nexum/assets/logo.svg` e `docs/logo-nexum.svg` | Arquivos iguais; o build instala o SVG com a ID atual. |
| Diagnóstico do atalho | `packaging/flatpak/check-launcher.py` | Verifica o aplicativo instalado e sua entrada de menu. |
| Compilação automatizada | `.github/workflows/packages.yml` | Compila, instala e testa o Flatpak antes da release. |

Não existe nesta árvore o arquivo `io.github.darimarchive_glitch.Nexum.yaml`. Usar esse nome em um comando não cria nem renomeia um manifesto.

## Evidências existentes

A [release 7.0.0-preview.2](https://github.com/darimarchive-glitch/Nexum-Scientific-Workbench/releases/tag/v7.0.0-preview.2) contém o bundle Linux x86_64, o código-fonte e `SHA256SUMS.txt`.

A [execução 36314373112](https://github.com/darimarchive-glitch/Nexum-Scientific-Workbench/actions/runs/36314373112) concluiu com sucesso a compilação, instalação do bundle, verificação do atalho e teste do aplicativo dentro do Flatpak. Isso demonstra funcionamento daquele pacote independente; não demonstra aprovação pelo linter ou pelos revisores do Flathub.

As capturas de interface existentes no [artefato de validação Windows](https://github.com/darimarchive-glitch/Nexum-Scientific-Workbench/actions/runs/36314373183) são evidências de teste. Não foram publicadas como imagens de catálogo Linux no MetaInfo.

## Lacunas concretas do projeto

1. **Identidade:** o namespace `nexum` da ID atual não corresponde ao proprietário `darimarchive-glitch` do repositório examinado. Não foi demonstrado controle daquele namespace. O mantenedor precisa resolver a identidade antes de migrar instalações.
2. **Entrada do build:** a receita lê `../../build/flatpak-input`. Essa pasta só existe depois da preparação local, portanto o manifesto atual não descreve sozinho como reconstruir o programa a partir de um checkout limpo.
3. **Dependências:** o script usa `pip download --only-binary=:all:` e intervalos de versões. O conjunto é resolvido durante cada preparação. `WHEELS.sha256` registra os arquivos obtidos, mas não fixa antecipadamente os insumos da receita.
4. **Acoplamento ao bundle:** `install.py` copia obrigatoriamente `WHEELS.sha256`. Mudar apenas a origem das dependências deixaria essa etapa inconsistente.
5. **Versão:** a release e o MetaInfo identificam explicitamente uma prévia. Não houve validação que justifique apenas remover o sufixo para anunciá-la como estável.
6. **Idiomas:** a interface examinada usa textos portugueses diretamente nos módulos. Não foram encontrados catálogos `.po`/`.mo` na árvore `nexum`; descrições bilíngues no MetaInfo não traduzem a interface.
7. **Catálogo:** faltam imagens no MetaInfo. A identidade de desenvolvedor ainda acompanha o namespace legado.
8. **Arquiteturas:** existe evidência de Flatpak x86_64. Os DMGs arm64 não comprovam funcionamento do Flatpak aarch64.
9. **Validação específica:** não há nesta auditoria um resultado de lint de manifesto, build ou repositório aprovado pelo Flathub. As ferramentas `flatpak`, `appstreamcli` e `desktop-file-validate` não estavam disponíveis no ambiente local desta auditoria.

## Dependências a inventariar no build por fontes

| Dependência direta | Intervalo declarado atualmente | Função no Nexum |
| --- | --- | --- |
| NumPy | `>=1.26,<3` | Matrizes e cálculos numéricos. |
| SciPy | `>=1.13,<2` | Métodos numéricos e análise. |
| PyOpenGL | `>=3.1.7,<4` | Acesso ao renderizador OpenGL. |
| gemmi | `>=0.7,<1` | Estruturas macromoleculares e formatos cristalográficos. |
| RDKit | `>=2026.3,<2027` | Estruturas químicas, conformeros e propriedades moleculares. |
| Pillow | `>=10,<13` | Imagens e exportações. |

Esta tabela não é uma lista completa de módulos de compilação. Dependências transitivas, compiladores, bibliotecas nativas e ferramentas de build devem ser levantados nas versões efetivamente escolhidas. GTK, libadwaita, Cairo e PyGObject também precisam ser conferidos no SDK/runtime escolhido; não se deve assumir que todos estarão disponíveis sem inspeção.

## Dados e permissões a preservar

`nexum/paths.py` usa os diretórios XDG no Linux. Dentro do Flatpak, os dados ficam associados à ID do aplicativo. Histórico, preferência de tema e recuperação do laboratório não devem se perder numa troca de ID. Antes de qualquer migração, teste a abertura dos projetos `.nexum7`, das sessões e a preservação dos dados da instalação legada. Uma nova ID não torna esses dados automaticamente visíveis.

A receita atual solicita rede, IPC, Wayland, X11 de fallback e acesso gráfico. Não solicita acesso geral à pasta pessoal. Rede é usada nas buscas externas; as funções locais precisam continuar utilizáveis sem conexão. Importação e exportação devem ser exercitadas pelo seletor de arquivos dentro do sandbox, incluindo cancelamento e nomes com acentos.

## Critérios externos que o mantenedor precisa verificar

As regras oficiais consultadas exigem autoria humana do manifesto, declaração de material produzido com IA, identidade verificável, build por fontes sem rede e runtime atual. A primeira inclusão precisa atender aos critérios de estabilidade e idioma; o canal beta não aceita novas submissões. A seleção de arquiteturas e os testes do catálogo também precisam ser concluídos. As referências são normativas; esta auditoria não concede exceções.

## Diagnóstico do manifesto existente

Na raiz do projeto, estes comandos apenas localizam e analisam a receita independente. Não a transformam em uma submissão elegível:

```bash
pwd
ls -l packaging/flatpak/io.github.nexum.ScientificWorkbench.json
flatpak run --command=flatpak-builder-lint org.flatpak.Builder manifest \
  packaging/flatpak/io.github.nexum.ScientificWorkbench.json
```

O último comando pressupõe que `org.flatpak.Builder` já esteja instalado. É possível obter erros ligados à receita local; eles não devem ser ocultados. Para diagnosticar uma falha, guarde a saída completa, especialmente as últimas linhas. Para os demais modos de lint e o procedimento de submissão, siga diretamente a documentação oficial.

## Próxima etapa humana

Um mantenedor precisa elaborar e manter a receita de submissão segundo as regras oficiais, resolver as lacunas acima e revisar pessoalmente a proveniência do projeto. Esta auditoria não fornece um manifesto alternativo, gerador de manifesto, descrição de PR ou declaração de autoria em nome do mantenedor.

Referências consultadas em 28/09/2026:

- [Requisitos e política de IA](https://docs.flathub.org/docs/for-app-authors/requirements)
- [Submissão](https://docs.flathub.org/docs/for-app-authors/submission)
- [Linter](https://docs.flathub.org/docs/for-app-authors/linter)
- [MetaInfo](https://docs.flathub.org/docs/for-app-authors/metainfo-guidelines)
- [Runtimes](https://docs.flathub.org/docs/for-app-authors/runtimes)
