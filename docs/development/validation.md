# Validação — Nexum 7.0.0-preview.1

Executada em 26 de setembro de 2026, em Linux x86_64, Python 3.12.14. Nenhum build remoto foi executado e nenhuma alteração foi publicada no GitHub.

## Resultado da suíte

- **274 testes descobertos**.
- **254 aprovados**.
- **20 ignorados** por indisponibilidade de Cairo ou de GTK4/libadwaita com display.
- **0 falhas e 0 erros**.

Casos ignorados não são contados como aprovados. O resumo estruturado está em `validation-summary.json`, nesta pasta.

## O que foi exercitado

- Modelos e regressões do motor existente: equilíbrio, termodinâmica, cinética, espectroscopia, processos e protocolos.
- Construção real por RDKit: fórmula, valência, aromaticidade, hidrogênios explícitos, convergência e candidatos conformacionais.
- Recusa de estereoquímica, isótopos e radicais que o editor simplificado não preserva.
- Medidas geométricas em precisão dupla, sem arredondar para a precisão de renderização.
- Distinção entre RMSE e erro padrão residual no ajuste estatístico.
- Alinhamento rígido contra rotação/translação conhecida, correspondências inválidas e colinearidade.
- Motor químico em subprocesso real, incluindo as novas operações e preservação de Unicode. Executado em Linux, não em um Windows físico.
- Importação brasileira, colunas, dados inválidos, XYPOINTS, hashes e exportação.
- Derivação e integração comparadas com funções analíticas; calibração inversa e suavização polinomial.
- Persistência atômica, rollback, desfazer/refazer, rejeição de conteúdo alterado e de identificadores/caminhos inválidos.
- Recuperação de coeficientes fatoriais conhecidos; critérios de controle e especificação distintos.
- Conservação de massa, componentes e energia sensível em processos.
- Propagação analítica de incerteza, correlações que cancelam erros, domínio físico e repetibilidade Monte Carlo.
- Distribuição ácido–base: ponto pH=pKa, razão das espécies e soma das frações.
- Execução de extensão revisada, recusa após alteração e rejeição de resultado não finito.
- Consistência de nomes, metadados, identidade e caminhos macOS por seleção simulada de plataforma.

## Verificações adicionais

Compilação sintática Python, sintaxe dos scripts shell, catálogo automático, links locais, igualdade do logo e análise estática dos novos módulos. Os seis arquivos de exemplo foram gerados pelo motor e reabertos pela validação do formato.

## Dependências usadas

| Dependência | Versão |
| --- | --- |
| numpy | 2.3.5 |
| scipy | 1.17.0 |
| rdkit | 2026.3.6 |
| gemmi | 0.7.5 |
| Pillow | 12.3.0 |
| PyOpenGL | 3.1.10 |

## Limites concretos

Não foi possível abrir uma sessão GTK/OpenGL utilizável neste ambiente. Portanto, a disposição visual do novo laboratório, cliques, arraste, diálogos, capturas PNG/GIF, cenas e integração com o gerenciador de janelas ainda precisam de verificação nativa. Há testes de integração incluídos para esse fim, mas eles foram ignorados nesta execução.

Não foram compilados instaladores desta versão para Windows, Flatpak ou macOS. Não há EXE, Flatpak ou DMG homologado neste ZIP. As receitas foram revisadas e verificadas onde possível; isso não substitui instalação e execução dos binários de destino. Não se afirma assinatura, notarização, aprovação no Flathub ou compatibilidade universal de GPU.

## Como repetir

```bash
python scripts/validate.py
python -m compileall -q nexum packaging scripts tests
python scripts/update_catalog.py --check
python scripts/check_project.py
```

O primeiro comando gera logs em `build/validation/`, fora dos arquivos distribuídos. Para exercitar GTK, execute em uma sessão gráfica real com os módulos de sistema. Para validar o bundle, execute o self-test nativo e confira seu log antes de anunciar uma versão estável.
