# Distribuição

O nome público é **Nexum** e a descrição é **Scientific Workbench**. A versão e os nomes dos artefatos vêm de `nexum/identity.py`; não mantenha números de versão duplicados em scripts quando a identidade central puder ser usada.

## Artefatos da release estável

| Plataforma | Artefato | Validação no pipeline |
| --- | --- | --- |
| Windows x86_64 | `Nexum-VERSAO-windows-x86_64-setup.exe` | bundle, instalador, atalhos e self-test da cópia instalada |
| Linux x86_64 | `Nexum-VERSAO-linux-x86_64.flatpak` | build, instalação, launcher e self-test dentro do sandbox |
| macOS arm64 | `Nexum-VERSAO-macos-arm64.dmg` | build nativo, bundle e self-test |
| macOS x86_64 | `Nexum-VERSAO-macos-x86_64.dmg` | build nativo, bundle e self-test |
| Integridade | `SHA256SUMS.txt` | gerado a partir dos artefatos que serão publicados |

A extensão de projeto é `.nexum7`. Fluxos reutilizáveis usam `.nexumflow`.

## Regra de publicação

`.github/workflows/packages.yml` executa a validação científica e compila os pacotes nativos. A release só é criada após o sucesso de todos os jobs. Versões com sufixo, como `-preview.1` ou `-rc.1`, são publicadas como pre-release; versões sem sufixo, como `7.0.0`, são publicadas como estáveis.

Uma release já publicada não tem seus binários substituídos automaticamente. Novas alterações exigem nova versão quando precisarem ser distribuídas.

## Compilação local

- Windows: `packaging/windows/build.ps1`, em Windows, com MSYS2 UCRT64, CPython e Inno Setup.
- Linux: `bash packaging/flatpak/build.sh`, com Flatpak e flatpak-builder, runtime GNOME 50.
- macOS: `bash packaging/macos/build.sh`, dentro do ambiente conda em um Mac da arquitetura alvo.

## Licença nos pacotes

O Windows inclui `LICENSE.txt` no bundle e o instalador apresenta a licença. O Flatpak instala a licença em `/app/share/nexum/LICENSE`. O DMG inclui `LICENSE.txt` ao lado do aplicativo, e o bundle macOS também carrega a cópia empacotada pelo PyInstaller.

Isso não substitui as licenças de dependências de terceiros, que continuam regidas pelos próprios termos.

## Assinatura e distribuição pública

Os pacotes públicos atuais não configuram Authenticode no Windows. No macOS, Developer ID e notarização só são usados quando as credenciais apropriadas são fornecidas fora do repositório; sem elas, o build usa assinatura ad hoc.

Essas limitações devem ser informadas ao usuário e tratadas antes de uma distribuição comercial ampla que exija uma cadeia de confiança de plataforma.

## Identidade técnica

A ID `io.github.nexum.ScientificWorkbench` foi preservada para continuidade das instalações existentes. Ela não demonstra controle do namespace `nexum` no GitHub. Uma futura mudança de ID precisa ser coordenada com migração dos dados do sandbox e dos identificadores de pacote.

A mudança deve abranger `nexum/identity.py`, arquivos `.desktop`, MetaInfo, manifesto Flatpak, atalhos e scripts de instalação. O identificador de upgrade do Inno Setup permanece estável para não quebrar instalações Windows existentes.

## Flathub

O bundle Flatpak independente não equivale à publicação no Flathub. Consulte [preparação](flathub.md) e a [auditoria histórica](flathub-audit.md) antes de iniciar uma submissão.
