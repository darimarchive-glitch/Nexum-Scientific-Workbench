<div align="center">

# Nexum · Scientific Workbench

### Da equação à descoberta.

Química computacional, estruturas 3D e experimentos em uma bancada nativa para o desktop GNOME.

![Versão 6.6](https://img.shields.io/badge/vers%C3%A3o-6.6-3584e4?style=for-the-badge)
![GTK4 e libadwaita](https://img.shields.io/badge/desktop-GTK4%20%2B%20libadwaita-9141ac?style=for-the-badge)
![Fedora](https://img.shields.io/badge/Linux-Fedora-51a2da?style=for-the-badge)
![Python](https://img.shields.io/badge/motor-Python-26a269?style=for-the-badge)

**35 calculadoras · 12 áreas da química · 8 bancadas · 14 modelos no registro avançado**

[Começar](#começar-no-fedora) · [Experimentos](#uma-bancada-que-responde-aos-seus-dados) · [Motor científico](#o-cérebro-científico) · [Documentação](#documentação) · [Contribuir](CONTRIBUTING.md)

</div>

---

## Química em uma bancada integrada

O **Nexum Scientific Workbench** reúne cálculos químicos, visualização molecular 3D e experimentos computados em uma aplicação nativa com **GTK4, libadwaita e OpenGL**. A interface organiza o trabalho em Início, Calculadoras, Estruturas 3D, Experimentos e Histórico.

A ideia central é simples: **você fornece as condições; o motor resolve o modelo; a bancada mostra o estado calculado.** Presets preenchem entradas. As equações determinam os resultados.

| Calcule | Explore | Experimente |
| :--- | :--- | :--- |
| Estequiometria, equilíbrio, termodinâmica, cinética e outras áreas, com gráficos nas ferramentas que os implementam. | Moléculas e macromoléculas, fitas com espessura, profundidade, ligantes e diferentes representações. | Titulação, eletroquímica, calorimetria e outras bancadas com medições e curvas ligadas ao mesmo estado. |

Os cálculos são locais. A instalação e a busca de estruturas em **PubChem/RCSB** precisam de conexão. Os módulos científicos avançados também podem ser usados diretamente em Python; nem todos possuem formulário próprio na interface.

> **Edição GNOME/Fedora 6.6:** aplicação desktop nativa. Este repositório reúne o código, os testes e a documentação desta edição.

## Começar no Fedora

Em uma sessão gráfica do Fedora, com Git instalado:

```bash
git clone https://github.com/darimarchive-glitch/Nexum-Scientific-Workbench.git nexum-gnome
cd nexum-gnome
chmod +x *.sh
./install-fedora.sh
./run.sh
```

O instalador usa `dnf` ou `dnf5`, solicita `sudo` para instalar as dependências nativas, cria um ambiente `.venv` com acesso aos pacotes GTK do sistema, instala as bibliotecas Python e executa a suíte de testes.

| Comando | O que faz |
| :--- | :--- |
| `./install-fedora.sh` | Prepara dependências e ambiente Python; executa os testes. |
| `./run.sh` | Abre a aplicação nativa. |
| `./test.sh` | Executa os testes e verifica a compilação dos módulos Python. |
| `./install-desktop-shortcut.sh` | Adiciona o Nexum ao menu de aplicativos. |

**Dependências:** Python 3, PyGObject, GTK4, libadwaita, Mesa/OpenGL, NumPy, SciPy, PyOpenGL, gemmi e RDKit. As faixas de versões das bibliotecas Python estão em [requirements.txt](requirements.txt); os pacotes do sistema estão no [instalador](install-fedora.sh). A validação automatizada desta publicação usou Python 3.12.

## Uma bancada que responde aos seus dados

Na v6.6, configuração, desenho e gráfico compartilham uma sessão experimental. Você pode pausar, avançar um passo, explorar um instante ou editar os parâmetros para construir outro cenário.

| Bancada | O que você explora | Base do cálculo |
| :--- | :--- | :--- |
| **Titulação** | Adição de titulante, indicador, curva de pH e equivalência. | Ácido forte ou monoprótico fraco com base forte; balanços de matéria e carga, equilíbrio ácido e autoionização da água. |
| **Célula de Daniell** | Consumo de espécies, massas depositadas e potencial reversível. | Carga elétrica, lei de Faraday e Nernst. |
| **Calorimetria elétrica** | Aquecimento e perdas térmicas para o ambiente. | Balanço de energia com potência e troca térmica. |
| **Equilíbrio de Haber** | Composição inicial e composição de equilíbrio. | Constante dependente da temperatura e extensão de reação no modelo ideal. |
| **Beer–Lambert** | Absorbância, caminho óptico e transmissão. | `A = εbc` e `T = 10⁻ᴬ`. |
| **Cinética** | Conversão de A em B e marcações de meia-vida. | Lei temporal de primeira ordem. |
| **Decaimento nuclear** | População esperada, atividade e meias-vidas. | Decaimento exponencial. |
| **Gás ideal** | Compressão e expansão isotérmicas. | `pV = nRT`. |

**Para começar:** escolha Titulação, altere as concentrações e use **Ir à equivalência**. Depois explore a curva com o controle de tempo. O indicador muda a representação da cor, mantendo o pH calculado pelo modelo.

A velocidade de reprodução controla o relógio visual. **Haber e Beer–Lambert são bancadas estáticas**, atualizadas ao editar os parâmetros. Cores e movimentos esquemáticos ajudam a interpretar o estado. Consulte as hipóteses em [Experimentos v6.6](EXPERIMENTOS-v6.6.md).

## Estruturas com profundidade

O visualizador combina `Gtk.GLArea`, depth buffer, perspectiva e geometria OpenGL. As fitas de macromoléculas são geradas como malhas com espessura.

- **Fontes:** busca em PubChem e RCSB; leitura de SDF, PDB e PDBx/mmCIF no núcleo.
- **Representações:** fitas, bolas e ligações, preenchimento, varetas, backbone e linhas.
- **Inspeção:** cadeias, ligantes, hidrogênios, névoa e perspectiva.
- **Conformadores:** quando não há 3D disponível no PubChem, o fluxo tenta gerar coordenadas com RDKit, ETKDG e otimização MMFF/UFF.

Experimente pesquisar **`4HHB`**, selecionar **RCSB** e usar **Fitas** para explorar a hemoglobina. A disponibilidade depende do serviço remoto; um conformador gerado computacionalmente é uma aproximação do método utilizado.

## O cérebro científico

O registro público `ScientificEngine` reúne modelos reutilizáveis com entradas, equações, hipóteses e domínio declarado. Uma chamada a `solve()` executa o solver e devolve um `CalculationTrace` com resultado, tempo de execução e diagnósticos disponíveis para aquele modelo.

| Área | Implementações no backend | Diagnósticos e escopo |
| :--- | :--- | :--- |
| **Soluções** | Força iônica, Debye–Hückel, Davies e especiação poliprótica. | Balanço de carga e domínio dos modelos de atividade. |
| **Equilíbrio** | Constantes de formação e equilíbrio multirreacional ideal. | Resíduos de balanço e afinidade química. |
| **Gases e fases** | Peng–Robinson puro/misturas, `kij`, fugacidades, Rachford–Rice e flash TP. | Fechamento material e igualdade de fugacidades. |
| **Cinética** | Redes de ação das massas e integração ODE, incluindo BDF. | Avaliações do solver e invariantes estequiométricos. |
| **Eletroquímica** | Butler–Volmer, inversão, polarização com queda `iR` e Cottrell. | Convenções de sinal e hipóteses de cinética/difusão. |
| **Metrologia** | GUM, Monte Carlo e regressão ponderada. | Sensibilidades, covariância, resíduos e `χ²`. |
| **Espectroscopia** | Beer–Lambert multicomponente por LS/NNLS. | Espectro reconstruído, RMSE, posto e condicionamento. |

### Use o motor diretamente em Python

Na raiz do projeto, com as dependências científicas instaladas:

```python
from nexum.core.engine import default_engine

engine = default_engine()

# Três comprimentos de onda, duas espécies e caminho óptico de 1 cm.
# ε em L mol⁻¹ cm⁻¹; absorbâncias adimensionais.
trace = engine.solve(
    "multicomponent-beer",
    absorbance=[0.12, 0.21, 0.15],
    epsilon_matrix=[[100, 10], [10, 100], [50, 50]],
    path_cm=1.0,
)

print(trace.result["concentrations_m"])  # ≈ [0.001, 0.002] mol/L
print(trace.diagnostics)                # RMSE e número de condição
print(engine.keys())                   # Modelos registrados
```

O [exemplo completo](examples/beer_multicomponente.py) pode ser executado com:

```bash
.venv/bin/python -m examples.beer_multicomponente
```

Esse exemplo foi executado nesta publicação e recuperou as concentrações com erro residual próximo da precisão de ponto flutuante. O trace registra equações declaradas e diagnósticos retornados; ele não representa uma derivação simbólica automática nem um histórico completo das iterações internas.

## Validação e limites científicos

**A suíte contém 170 testes.** O resultado reproduzido para esta publicação, o ambiente e as verificações não executadas estão em [docs/VALIDACAO-PUBLICACAO.md](docs/VALIDACAO-PUBLICACAO.md). Os testes cobrem cálculos, conservação, benchmarks, mudanças de entradas, sessões experimentais, renderização Cairo e integração GTK. Dependências ou display ausentes podem causar `skipped`; esses casos não contam como testes aprovados.

Precisão numérica e adequação física precisam ser avaliadas juntas. O projeto declara limites relevantes:

- **Flash Peng–Robinson:** ainda sem teste global completo de estabilidade por plano tangente.
- **Atividades:** Davies e Debye–Hückel têm domínio restrito; convergência não garante validade em soluções concentradas.
- **Cinética:** mecanismos e parâmetros devem ser fornecidos; a rede não é inferida automaticamente.
- **Metrologia:** Monte Carlo usa entradas normais multivariadas; regressão ponderada não trata incerteza em `x`.
- **Pesquisa:** Pitzer/SIT parametrizado, DFT e transporte eletroquímico acoplado não fazem parte desta entrega.

## Organização do projeto

| Caminho | Responsabilidade |
| :--- | :--- |
| [`nexum/core/`](nexum/core/) | Calculadoras, química, estruturas, experimentos e sessões. |
| [`nexum/core/advanced/`](nexum/core/advanced/) | Solvers científicos e registro auditável, independentes de GTK. |
| [`nexum/ui/`](nexum/ui/) | Interface GTK, renderização OpenGL e desenhos/gráficos Cairo. |
| [`nexum/history.py`](nexum/history.py) | Histórico local em SQLite. |
| [`tests/`](tests/) | Testes científicos, numéricos e de interface. |
| [`examples/`](examples/) | Exemplos de uso programático. |

## Licença

Distribuído sob a [licença MIT](LICENSE), conforme definida pelo mantenedor neste repositório.

## Documentação

| Documento | Para que serve |
| :--- | :--- |
| [Experimentos v6.6](EXPERIMENTOS-v6.6.md) | Controles, leitura das bancadas e limites de cada modelo. |
| [Arquitetura do backend](BACKEND-ARCHITECTURE.md) | Contratos, solvers, traces e separação da interface. |
| [Auditoria científica](SCIENTIFIC-AUDIT.md) | Hipóteses, equações e decisões de modelagem. |
| [Matriz de validação](VALIDATION-MATRIX.md) | Escopo e verificações científicas documentadas. |
| [Design da interface](UI-DESIGN.md) | Organização e linguagem visual. |
| [Changelog](CHANGELOG.md) | Evolução do projeto. |
| [Contribuição](CONTRIBUTING.md) | Como propor melhorias e relatar problemas reproduzíveis. |

---

<div align="center">

**Nexum Scientific Workbench · GNOME/Fedora 6.6**  
Projeto de [DarimArchive](https://github.com/darimarchive-glitch)

*Entradas explícitas. Modelos declarados. Resultados calculados.*

</div>
