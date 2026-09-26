# Exemplos

Todos os dados são simulados ou definidos explicitamente para fins didáticos. Os exemplos estão disponíveis também dentro do aplicativo, em Laboratório → Projeto e caderno.

| Arquivo em `projects/` | Objetivo |
| --- | --- |
| `uv-vis.nexum7` | Calibrar absorbância e estimar uma concentração desconhecida. |
| `kinetics.nexum7` | Investigar uma constante cinética de primeira ordem. |
| `titration.nexum7` | Estimar concentração por equivalência e examinar derivadas. |
| `factorial-design.nexum7` | Recuperar efeitos e interação de um modelo fatorial conhecido. |
| `process-balance.nexum7` | Conferir massa, composição e energia de mistura/aquecimento/divisão. |
| `quality-control.nexum7` | Distinguir um ponto fora de controle de uma especificação. |

`data/` contém CSV com ponto e vírgula, vírgula decimal e cabeçalho. `extensions/descriptive_statistics.py` exemplifica a interface `run(payload)`. Revise o código antes de autorizar a execução. `beer_multicomponente.py` demonstra o motor multicomponente existente.

Para gerar novamente os arquivos: `python scripts/generate_examples.py`. Para instruções completas, consulte [o guia](../docs/user/laboratory.md).
