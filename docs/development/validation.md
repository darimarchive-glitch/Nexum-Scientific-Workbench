# Validação — Nexum 7.0.0-preview.2

Validação local executada em 27 de setembro de 2026, em Linux x86_64, Python 3.12.14. A atualização foi publicada no GitHub; as verificações nativas de CI estão registradas abaixo.

## Resultado da suíte local

- **276 testes descobertos**.
- **254 aprovados**.
- **22 ignorados** por indisponibilidade de Cairo ou de GTK4/libadwaita com display.
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

## Verificações nativas no GitHub

- [Windows: regressões e interface GTK](https://github.com/darimarchive-glitch/Nexum-Scientific-Workbench/actions/runs/36236515520): aprovado após corrigir o isolamento dos testes GTK e a expectativa de exceção do motor em subprocesso.
- [Instaladores Windows e Flatpak](https://github.com/darimarchive-glitch/Nexum-Scientific-Workbench/actions/runs/36236234219): ambos os jobs aprovados. O Windows instalou o EXE, verificou os atalhos e executou a cópia instalada com PATH restrito. O Linux instalou o Flatpak, verificou os atalhos e executou a interface e o laboratório em sessão gráfica de CI.
- [Release preview.1: todos os pacotes aprovados](https://github.com/darimarchive-glitch/Nexum-Scientific-Workbench/actions/runs/36279427899): Windows, Flatpak, macOS Apple Silicon e Intel. O aplicativo macOS empacotado passou pelo self-test sem as variáveis do ambiente de desenvolvimento; a assinatura ad hoc foi verificada. Não houve notarização Apple.
- Preview.2 acrescenta regressões para preferência de tema, presets, painel lateral e comparação; o estado de sua execução deve ser consultado no CI.

## Limites concretos

Os testes gráficos nativos de CI complementam os testes locais ignorados. Eles não substituem a avaliação manual da disposição visual, dos diálogos, de acessibilidade e da experiência de uso em computadores reais. Não se afirma assinatura comercial, notarização Apple, aprovação no Flathub ou compatibilidade universal de GPU.

A release exige que todos os jobs de empacotamento passem. Consulte [as execuções](https://github.com/darimarchive-glitch/Nexum-Scientific-Workbench/actions/workflows/packages.yml) e [os downloads publicados](https://github.com/darimarchive-glitch/Nexum-Scientific-Workbench/releases) para o estado atual dos binários.

## Como repetir

```bash
python scripts/validate.py
python -m compileall -q nexum packaging scripts tests
python scripts/update_catalog.py --check
python scripts/check_project.py
```

O primeiro comando gera logs em `build/validation/`, fora dos arquivos distribuídos. Para exercitar GTK, execute em uma sessão gráfica real com os módulos de sistema. Para validar o bundle, execute o self-test nativo e confira seu log antes de anunciar uma versão estável.
