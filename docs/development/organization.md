# Organização, limpeza e migração

A organização do repositório prioriza uma árvore única e verificável para desenvolvimento, empacotamento e distribuição. Histórico útil permanece em `docs/releases/`; referências operacionais antigas não devem aparecer como instruções atuais.

## Critérios

- Remover artefatos temporários: bytecode, caches, logs soltos, ambientes virtuais, pastas de build e resultados de tentativas.
- Evitar versões antigas hardcoded em empacotadores, documentação corrente e metadados.
- Preservar código ativo, exemplos executáveis, testes, dados de referência, identidade visual utilizada e documentação científica substantiva.
- Substituir relatórios de preparação duplicados e contagens antigas pelo registro atual de validação.
- Remover o publicador antigo que referenciava IDs de jobs, hashes e instaladores fixos da versão 6.8.1.
- Manter notas curtas de versões anteriores em `docs/releases/`; elas explicam migrações e correções, sem se apresentar como estado atual.
- Dar nomes de responsabilidade aos testes; a versão em que um teste foi criado não define seu nome atual.

## Mapeamento principal

| Antes | Agora |
| --- | --- |
| `BACKEND-ARCHITECTURE.md` | `docs/development/architecture.md` |
| `UI-DESIGN.md` | `docs/development/interface.md` |
| `SCIENTIFIC-AUDIT.md` | `docs/science/model-audit.md` |
| `VALIDATION-MATRIX.md` | `docs/science/validation-matrix.md` |
| `EXPERIMENTOS-v6.6.md` | `docs/user/experiments.md` |
| Relatórios `VALIDACAO-*` de preparação antiga | `docs/development/validation.md` |
| Documentação solta em `docs/` | `user/`, `science/`, `development/`, `distribution/` e `releases/` |

O SVG oficial é a origem dos ícones. O ICO em `nexum/assets/` permanece necessário para o atalho do lançador Windows em modo de desenvolvimento; não é lixo de build. Os instaladores geram ICO e ICNS novamente em `build/icons/`.

## Compatibilidade

Histórico Linux/Windows, identidade técnica legada, formato antigo de sessão e identificador de upgrade do instalador Windows foram preservados. O novo `.nexum7` é um formato separado: não renomeie uma sessão JSON antiga para essa extensão. A mudança futura de ID Flatpak precisa de migração planejada dos dados do sandbox.

Projetos `.nexum7` são arquivos ZIP com duas entradas: documento JSON e hash. Não utilizam pickle nem extração arbitrária de caminhos. São validados antes de substituir o projeto em memória.

## Proveniência e revisão

Limpeza significa remover ruído operacional e material obsoleto. Não significa reescrever a origem do código ou apagar declarações necessárias a uma distribuição. Consulte [proveniência e revisão](provenance.md).
