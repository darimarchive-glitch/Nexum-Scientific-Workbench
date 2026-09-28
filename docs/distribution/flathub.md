# Flatpak independente e Flathub

O projeto mantém um fluxo de **Flatpak independente**. Ele foi preparado para distribuição entre sistemas Linux com Flatpak funcional, sem restringir o nome do programa ao Fedora. O pacote é específico de arquitetura e depende do runtime e de recursos gráficos compatíveis.

O manifesto em `packaging/flatpak/` pertence a esse fluxo independente. **Não é um manifesto aprovado, pronto ou elegível para submissão ao Flathub.** Não há publicação na loja nem PR de submissão nesta entrega.

A [auditoria de preparação](flathub-audit.md) registra os arquivos reais, as evidências de execução e as lacunas verificadas em 28/09/2026.

## Restrição atual relevante

As regras oficiais consultadas em 28/09/2026 estabelecem que:

- o uso de material gerado por IA na aplicação deve ser declarado, com partes afetadas e extensão aproximada;
- manifestos do Flathub não podem conter conteúdo gerado ou assistido por IA;
- agentes de IA não podem abrir/automatizar PRs de submissão nem produzir mensagens, descrições ou respostas dessas submissões.

Portanto, o manifesto oficial precisa ser preparado por um mantenedor humano conforme as regras vigentes. Este documento não é uma descrição de PR nem um manifesto substituto. A limpeza de arquivos temporários e documentação obsoleta não altera a proveniência do código.

## Pendências de distribuição

A receita atual usa wheels para gerar o bundle independente. As regras atuais do Flathub também exigem construção a partir de fontes para aplicações e dependências com fonte disponível, salvo exceções admitidas pela loja. Não basta renomear ou copiar esse manifesto.

O mantenedor precisa definir a identidade vinculada à conta/domínio correto, disponibilizar fontes e dependências verificáveis, cumprir o build sem rede, registrar screenshots reais, validar AppStream, testar acessibilidade e portais e sustentar manutenção. O arquivo MetaInfo desta árvore melhora os metadados do pacote independente, mas não certifica atendimento a todos os critérios da loja.

Evite mudar a ID da aplicação depois de adotada por usuários. A ID legada deste projeto não comprova controle do namespace; o repositório de destino confirmado é `darimarchive-glitch/Nexum-Scientific-Workbench`, administrado nesta colaboração pela conexão Juarchive. Isso não comprova controle do namespace legado `nexum`.

## Referências

- [Requisitos oficiais](https://docs.flathub.org/docs/for-app-authors/requirements)
- [Metadados](https://docs.flathub.org/docs/for-app-authors/metainfo-guidelines)
- [Verificação de identidade](https://docs.flathub.org/docs/for-app-authors/verification)
- [Convenções Flatpak](https://docs.flatpak.org/en/latest/conventions.html)

Reconsulte as regras antes de uma submissão. Este pacote não oculta nem declara aprovação inexistente.
