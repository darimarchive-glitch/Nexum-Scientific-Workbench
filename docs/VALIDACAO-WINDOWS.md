# Validação da adaptação Windows

Base: commit `acb6271` da edição GNOME/Fedora 6.6.

## Executado durante a preparação

Ambiente Linux, CPython 3.12; dependências científicas de `requirements.txt`.

| Verificação | Resultado |
| --- | --- |
| Suíte original | 170 testes: 158 aprovados, 12 ignorados por ausência de GTK/Cairo |
| Suíte com suporte Windows | 179 testes: 167 aprovados, os mesmos 12 ignorados |
| Subprocesso químico real | SMILES, molblock, mmCIF, coordenadas, metadados e Unicode aprovados |
| Falhas do subprocesso | Entrada inválida, operação desconhecida, timeout e executável ausente cobertos |
| Histórico | Gravação/reabertura SQLite e caminhos Windows/Linux cobertos |
| Compilação Python e diff | Sem erros |

Os testes de caminhos simulam a seleção de plataforma; não substituem execução
em Windows. O subprocesso foi realmente executado em Linux, não simulado nos
testes de geração e leitura química.

## Gate Windows

O workflow `.github/workflows/windows.yml` prepara CPython e MSYS2 UCRT64,
executa o instalador com Windows PowerShell, valida os shaders em Mesa,
constrói a janela completa e renderiza uma molécula no `Gtk.GLArea`, executa os
testes GTK/Cairo e chama o lançador CMD usando a configuração salva.

O resultado desse workflow deve ser consultado no GitHub Actions. Esta tabela
local não declara um resultado Windows antes da execução. A sessão manual em
Windows com GPU física, as buscas remotas e o comportamento em diferentes
monitores ainda precisam ser confirmados conforme [WINDOWS.md](WINDOWS.md).
