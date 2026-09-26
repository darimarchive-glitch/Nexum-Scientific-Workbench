# Distribuição

O nome para o público é **Nexum**, com a descrição **Scientific Workbench**. A versão e os nomes dos artefatos vêm de `nexum/identity.py`. Não acrescente “FINAL”, “novo”, “corrigido”, nomes de distribuição Linux ou números de tentativa ao nome público do programa.

| Artefato | Padrão |
| --- | --- |
| Fonte | `Nexum-VERSAO-source.zip` |
| Windows | `Nexum-VERSAO-windows-x86_64-setup.exe` |
| Linux | `Nexum-VERSAO-linux-ARQUITETURA.flatpak` |
| macOS | `Nexum-VERSAO-macos-ARQUITETURA.dmg` |
| Integridade | `SHA256SUMS.txt` na release; `.sha256` no build local macOS |

A extensão de projeto é `.nexum7`. Os fluxos reutilizáveis usam `.nexumflow`.

## Compilação local

- Windows: `packaging/windows/build.ps1`, em Windows, com MSYS2 UCRT64, CPython e Inno Setup; fornece dependências no bundle e testa a cópia instalada.
- Linux: `bash packaging/flatpak/build.sh`, com Flatpak e flatpak-builder, runtime GNOME 50; resolve wheels no SDK, registra hashes e compila sem rede na etapa do builder. O script produz um pacote independente, não uma submissão ao Flathub.
- macOS: `bash packaging/macos/build.sh`, dentro do ambiente conda em um Mac; produz aplicativo e DMG da arquitetura nativa.

O bundle Flatpak pode ser instalado com `flatpak install --user CAMINHO.flatpak`. O nome no menu é Nexum; iniciar pela linha de comando continua possível com `flatpak run io.github.nexum.ScientificWorkbench`. Caso o ambiente não atualize seus atalhos, use `nexum-repair-shortcut.sh` fornecido pelo build Linux.

## Identidade técnica e futura conta

A ID existente `io.github.nexum.ScientificWorkbench` foi preservada para não fragmentar os diretórios de dados de usuários da versão anterior. Ela **não demonstra controle do namespace `nexum` no GitHub**. Antes da publicação em uma loja, escolha uma identidade que corresponda a uma conta/repositório ou domínio controlado por você e estabeleça uma migração dos dados Flatpak.

A mudança deve ser coordenada em `nexum/identity.py`, arquivos `.desktop`, `.metainfo.xml`, nome e conteúdo do manifesto Flatpak, verificações de atalhos e scripts de instalação. O identificador de upgrade do Inno Setup foi preservado para instalações Windows existentes. IDs internos não precisam ser tão curtos quanto o nome exibido.

O workflow `packages.yml` compila e verifica os pacotes nativos e publica a prévia somente após o sucesso de todos os jobs. O antigo publicador com hashes, versões e IDs de jobs fixos foi removido. Uma release já publicada não tem seus binários substituídos automaticamente.

O runtime do pacote independente foi atualizado de GNOME 49 para 50. O bundle foi compilado, instalado e testado no CI. Referência: [GNOME, recomendação de migração para o runtime 50](https://thisweek.gnome.org/posts/2026/03/twig-242/).
