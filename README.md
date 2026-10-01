<div align="center">
<img src="docs/logo-nexum.svg" width="112" alt="Logo oficial do Nexum">

# Nexum

**Scientific Workbench — química, estruturas moleculares, dados experimentais e modelos rastreáveis.**

Versão **7.0.0** · release estável · aplicação desktop · interface em português brasileiro
</div>

<!-- nexum-catalog:start -->
**43 calculadoras · 12 áreas científicas · 10 bancadas · 5 ferramentas de análise de dados · 16 recursos de laboratório**
<!-- nexum-catalog:end -->

O **Nexum 7.0.0** é a primeira release estável da série 7. O projeto reúne cálculo químico, visualização molecular, experimentos didáticos, tratamento de dados, planejamento experimental, controle de qualidade, incerteza e relatórios em uma única aplicação desktop.

A publicação dos instaladores é bloqueada até que o pipeline científico e os builds nativos de Windows, Linux/Flatpak e macOS concluam com sucesso. Consulte [Validação](docs/development/validation.md) para escopo, evidências e limites.

**[Releases](https://github.com/darimarchive-glitch/Nexum-Scientific-Workbench/releases)** · **[Licenciamento comercial](COMMERCIAL.md)** · **[Suporte](SUPPORT.md)** · **[Segurança](SECURITY.md)**

## Capacidades principais

| Área | O que o Nexum oferece |
| --- | --- |
| Cálculo científico | Estequiometria, termodinâmica, equilíbrio, cinética, processos, eletroquímica, metrologia e espectroscopia. |
| Moléculas | Busca, importação, editor 2D, geração 3D, MMFF94/UFF, conformeros, medidas, superfícies, cortes e comparação por RMSD. |
| Dados experimentais | Importação tabular/JCAMP, linha de base, Savitzky–Golay, derivadas, integração, calibração e séries processadas sem sobrescrever o original. |
| Laboratório | Projetos `.nexum7`, caderno, recuperação automática, atribuições espectrais manuais, cenas e histórico. |
| Planejamento e qualidade | Fatorial 2^k, interações de dois fatores, resíduos, viés, RSD, recuperação, controle e especificação tratados separadamente. |
| Modelos e incerteza | Propagação correlacionada, Monte Carlo, sensibilidade e modelos ácido–base explícitos. |
| Comunicação | CSV, figuras, GIF de câmera, apresentação HTML e relatórios com rastreabilidade. |

Os seis projetos de exemplo usam dados identificados como simulados. Modelos, hipóteses e limitações são apresentados junto dos resultados sempre que a ferramenta correspondente fornece esse contexto.

## Downloads

A release estável usa nomes consistentes:

- Windows x86_64: `Nexum-7.0.0-windows-x86_64-setup.exe`
- Linux x86_64: `Nexum-7.0.0-linux-x86_64.flatpak`
- macOS Apple Silicon: `Nexum-7.0.0-macos-arm64.dmg`
- macOS Intel: `Nexum-7.0.0-macos-x86_64.dmg`
- Integridade: `SHA256SUMS.txt`

O Windows inclui fallback gráfico por software quando o OpenGL nativo falha. O Flatpak é um pacote independente e não significa publicação no catálogo Flathub. Os builds macOS públicos não possuem Developer ID/notarização configurados; os builds Windows públicos não possuem assinatura Authenticode configurada.

## Uso e desenvolvimento

Para o usuário final, prefira os instaladores publicados em **Releases**. Execução a partir do código é destinada a desenvolvimento.

**Linux/Fedora:**

```bash
bash install-fedora.sh
bash run.sh
```

**Windows:** consulte [Desenvolvimento e diagnóstico Windows](docs/distribution/windows.md). Os atalhos `install-windows.cmd`, `run-windows.cmd`, `test-windows.cmd` e `diagnose-windows.cmd` chamam o fluxo mantido em `scripts/windows/nexum.ps1`.

**macOS:**

```bash
conda env create -f packaging/macos/environment.yml
conda activate nexum-build
python -m nexum.main
bash packaging/macos/build.sh
```

## Verificação

```bash
python scripts/validate.py
python -m compileall -q nexum packaging scripts tests
python scripts/update_catalog.py --check
python scripts/check_project.py
```

Os testes gráficos exigem uma sessão GTK real. Os pipelines de empacotamento também exercitam a cópia instalada/empacotada antes de permitir a publicação.

## Licença e uso comercial

O Nexum é **software proprietário com código-fonte disponível para inspeção**. A presença do código em um repositório público não concede permissão geral para copiar, modificar, redistribuir, incorporar o código em outro produto ou explorá-lo comercialmente.

A licença atual permite a indivíduos instalar e executar cópias oficiais para uso pessoal, estudo, educação e avaliação. Uso institucional, comercial, laboratorial, organizacional, redistribuição, integração, OEM e serviços hospedados exigem autorização específica. Consulte [LICENSE](LICENSE) e [COMMERCIAL.md](COMMERCIAL.md).

Versões ou trechos que tenham sido publicados anteriormente sob MIT continuam sujeitos aos direitos validamente concedidos naquela publicação; a mudança de licença não é retroativa.

## Limites importantes

O Nexum é uma ferramenta científica e educacional. Ele não deve ser tratado como certificação regulatória, laudo clínico, sistema de segurança, substituto de validação metrológica ou prova de exatidão fora das hipóteses documentadas.

O editor molecular simplificado não preserva todos os casos de estereoquímica, isótopos ou radicais. MMFF/UFF não são cálculos quânticos. Algumas funções externas dependem de rede. Consulte a [matriz de validação](docs/science/validation-matrix.md) e a [auditoria dos modelos](docs/science/model-audit.md).

## Estrutura do projeto

| Diretório | Responsabilidade |
| --- | --- |
| `nexum/core/` | Modelos químicos, dados, importadores e motores científicos. |
| `nexum/lab/` | Projetos, processamento, construção molecular, DOE, qualidade, incerteza e relatórios. |
| `nexum/ui/` | Interface GTK4/libadwaita, gráficos e visualizador OpenGL. |
| `nexum/assets/` | Identidade visual e recursos do aplicativo. |
| `packaging/` | Receitas de distribuição Windows, Linux e macOS. |
| `examples/` | Projetos didáticos, dados e extensão de exemplo. |
| `tests/` | Referências numéricas, regressões, persistência e integração gráfica. |
| `docs/` | Uso, ciência, desenvolvimento, distribuição e histórico. |

## Documentação

- [Laboratório](docs/user/laboratory.md)
- [Análise e visualização](docs/user/analysis-and-visualization.md)
- [Experimentos](docs/user/experiments.md)
- [Métodos, incerteza e referências](docs/science/laboratory-methods.md)
- [Matriz de validação](docs/science/validation-matrix.md)
- [Arquitetura](docs/development/architecture.md)
- [Validação da série 7.0](docs/development/validation.md)
- [Distribuição](docs/distribution/README.md)
- [Histórico de releases](docs/releases/README.md)
