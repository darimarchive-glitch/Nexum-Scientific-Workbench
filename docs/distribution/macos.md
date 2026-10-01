# macOS: compilação e verificação

**Estado:** o pipeline da série 7.0 compila DMGs nativos separados para Apple Silicon e Intel e executa o self-test do aplicativo empacotado antes da publicação. A release estável só é criada quando os dois jobs passam. Assinatura Developer ID e notarização não estão configuradas no repositório público; sem essas credenciais o build usa assinatura ad hoc e o macOS pode exibir aviso de desenvolvedor não identificado.

## Implementação

- Motor Python e interface GTK4/libadwaita compartilhados.
- Dados em `~/Library/Application Support/Nexum`; cache em `~/Library/Caches/Nexum`.
- `Nexum.app` com logo ICNS produzido a partir do SVG oficial.
- Bundle PyInstaller contendo dependências científicas e gráficas, sem exigir Python do usuário final.
- Build nativo separado para `arm64` e `x86_64`; nenhuma promessa de universal2 sem todas as dependências universais.
- DMG com aplicativo e atalho para Aplicativos.
- Teste do executável empacotado com variáveis de desenvolvimento removidas.
- Assinatura e notarização opcionais por credenciais locais do mantenedor; nenhum segredo vai para o projeto.

## Preparar um Mac

1. Instale as Command Line Tools da Apple e Miniforge para a arquitetura do Mac.
2. Na raiz do projeto: `conda env create -f packaging/macos/environment.yml`.
3. Execute `conda activate nexum-build`.
4. Confirme `python -m nexum.main`: abertura das páginas, construção de etanol, camadas, PNG e projeto.
5. Execute `bash packaging/macos/build.sh`.

O arquivo de ambiente declara intervalos compatíveis, não é um lock validado para os dois Macs. O build registra `conda list --explicit` e `pip freeze` em `build/macos/`; use esses registros para congelar o ambiente que efetivamente passou na homologação. O mínimo de implantação proposto é macOS 13; confirme que nenhuma biblioteca exige uma versão superior antes de anunciá-lo.

## Assinar e notarizar

O script lê `NEXUM_MAC_SIGN_IDENTITY` para a identidade Developer ID instalada no chaveiro. Se `NEXUM_MAC_NOTARY_PROFILE` também estiver definido, envia aplicativo/DMG pelo `notarytool`, aguarda a resposta e aplica `stapler`. O mantenedor cria o perfil no chaveiro previamente. Não cole senhas, chaves ou certificados na árvore do código.

Sem uma identidade de distribuição, o PyInstaller usa assinatura ad hoc quando aplicável. Isso não equivale a Developer ID, não garante aceitação pelo Gatekeeper e não deve ser anunciado como instalador final para o público. Não desative o Gatekeeper para mascarar falhas.

## Homologação necessária

- Instalar o DMG em um Mac sem conda/Homebrew/Python de desenvolvimento no PATH.
- Iniciar pelo Finder; confirmar logo, foco, escala Retina, diálogos de arquivos e caminhos graváveis.
- Renderizar molécula pequena e macromolécula; testar OpenGL, cores, camadas, corte e exportação.
- Gerar conformeros; validar importação mmCIF, espectros, projetos e recuperação.
- Repetir nos Macs/versões mínimos efetivamente suportados e nas duas arquiteturas.
- Guardar hashes, logs, versão do sistema, arquitetura e decisão de assinatura junto à versão.

## Referências consultadas

- [GTK em macOS](https://docs.gtk.org/gtk4/osx.html)
- [PyInstaller: uso e builds por plataforma](https://pyinstaller.org/en/stable/usage.html)
- [PyInstaller: arquitetura e assinatura macOS](https://pyinstaller.org/en/stable/feature-notes.html)
- [Apple: notarização](https://developer.apple.com/documentation/security/notarizing-macos-software-before-distribution)
- [GTK4 no conda-forge](https://anaconda.org/conda-forge/gtk4)

Consulta: 26 de setembro de 2026.
