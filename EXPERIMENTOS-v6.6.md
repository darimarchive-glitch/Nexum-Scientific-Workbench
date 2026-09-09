# Bancadas didáticas — v6.6

Esta revisão mantém a estrutura desktop GNOME e concentra as mudanças na aba Experimentos. O motor numérico usa equações locais e recebe as entradas preenchidas pelo usuário.

## Comportamento das bancadas

| Bancada | O que observar | Relação com o cálculo |
| --- | --- | --- |
| Titulação | A bureta esvazia, o Erlenmeyer enche e o indicador muda de cor. O gráfico marca a equivalência, a faixa de viragem e o estado atual. | Volume entregue = vazão × tempo. O pH vem dos balanços de matéria e carga. O nível considera a geometria cônica do frasco. |
| Daniell | Elétrons no circuito externo, corrente convencional no sentido oposto, íons na ponte salina e transferência nos eletrodos. | A carga determina a quantidade transformada e as massas pela lei de Faraday. Nernst determina o potencial reversível. |
| Calorimetria | Resistência, termômetro e setas de troca térmica. A cor é uma escala de temperatura. | A energia elétrica fecha o balanço com a energia armazenada e o calor transferido. O nível do líquido fica constante. |
| Equilíbrio | Comparação entre composição inicial e final em reatores; barras em uma escala comum. | A solução satisfaz o equilíbrio e conserva os átomos. O desenho mostra proporções e o gráfico mostra mol. |
| Beer–Lambert | Fonte, cubeta, detector e atenuação do feixe. | A = εbc e a fração transmitida é 10⁻ᴬ. O marcador usa a concentração atual. |
| Cinética | A perde intensidade de cor e é convertido em B, com nível constante. | Modelo A → B (1:1), [A] = [A]₀ exp(−kt), [B] = [A]₀ − [A]. |
| Decaimento | População virtual restante e transformada; atividade e meias-vidas. | A população exibida é o valor esperado N₀ 2⁻ᵗ/ᵗ½. A atividade esperada é λN. |
| Pistão | Mesma relação entre deslocamento do pistão, volume e pressão. | Compressão/expansão isotérmica de gás ideal. |

## Controles

- **Iniciar / Retomar / Repetir:** executa, retoma ou recomeça a trajetória, conforme o estado atual.
- **Pausar:** congela o tempo simulado e libera a edição dos parâmetros.
- **Passo:** avança 1% da duração; em titulação, **+ 0,05 mL** entrega esse volume de base.
- **Reiniciar:** retorna ao estado inicial usando os mesmos parâmetros.
- **Explorar tempo:** posiciona a simulação em qualquer instante e pausa a reprodução.
- **Ir à equivalência:** posiciona a titulação no volume estequiométrico. Fica indisponível quando o volume máximo não alcança esse ponto.
- **Equilíbrio e Beer–Lambert:** atualizam ao editar; não exibem controles de execução temporal.

Campos vazios, não numéricos, infinitos ou fora do domínio deixam o problema visível na página e impedem a reprodução. Ao editar parâmetros válidos, um novo cenário começa em t = 0. A curva anterior não é reaproveitada. Ao trocar de bancada ou ocultar a página, o timer é interrompido.

## Limites das representações

A titulação representa ácido monoprótico genérico com base forte, a 25 °C e em solução ideal. Informar Ka não identifica uma substância. Os indicadores são opcionais; suas cores são interpolações didáticas de intervalos nominais de viragem e não alteram o cálculo do pH. Sem indicador, a solução permanece visualmente incolor. Equivalência estequiométrica e viragem do indicador são conceitos diferentes. A representação geométrica do frasco é idealizada.

Na Daniell, a corrente é imposta. Os pontos em movimento são representativos, sem escala de velocidade microscópica. O potencial é reversível, sem queda ôhmica ou sobrepotenciais. As dimensões dos eletrodos são esquemáticas; as quantidades transformadas aparecem em mg. O fluxo cessa ao esgotar o Cu²⁺ disponível, e o potencial indefinido não vira artificialmente zero no gráfico.

Na calorimetria, as capacidades térmicas são constantes, a mistura é homogênea e as perdas são lineares. O modelo não inclui ebulição ou outra mudança de fase. Calor transferido negativo significa energia recebida do ambiente.

No equilíbrio de Haber, não se inventa um tempo de reação a partir de um cálculo termodinâmico. A composição é ideal, com propriedades na faixa declarada pelo modelo. As cores apenas identificam as espécies.

Beer–Lambert usa meio homogêneo, luz monocromática e atenuação por absorção. A cor da cubeta não constitui uma previsão espectral. Com I₀ = 0, o desenho apaga os feixes; os valores de absorbância e transmitância são previsões teóricas, pois não existe leitura óptica nessa condição.

Na cinética, A azul e B incolor são uma convenção do exemplo. A concentração muda sem o líquido desaparecer. No decaimento, cada marca resume 1% da população inicial; arredondar a contagem visual não altera os valores calculados e não prevê qual núcleo individual se transforma.

## Referências conceituais

As relações entre curva de titulação, equivalência e indicadores podem ser consultadas no [OpenStax, Chemistry 2e, seção 14.7](https://openstax.org/books/chemistry-2e/pages/14-7-acid-base-titrations). A convenção de absorbância e as hipóteses de atenuação estão no [IUPAC Gold Book, lei de Lambert](https://goldbook.iupac.org/terms/view/L03445/pdf). Os coeficientes termodinâmicos e demais equações já presentes no projeto continuam documentados em `SCIENTIFIC-AUDIT.md` e `VALIDATION-MATRIX.md`.

## Validação desta entrega

- 134 testes existentes de ciência, backend e regressões: aprovados.
- 24 novos testes de sessão: aprovados, incluindo conservação, estados limite, titulação, indicadores, curva e navegação temporal.
- 6 novos testes de renderização Cairo: aprovados. Executam os desenhos reais em ambos os temas e verificam alterações visuais e ausência de movimento fictício com corrente/taxa zero.
- 6 novos testes de integração GTK incluídos: não executados nesta entrega por indisponibilidade de um display gráfico permitido no ambiente de validação.
- Compilação dos módulos Python verificada. As bancadas e gráficos foram renderizados e inspecionados em temas claro e escuro.

Portanto, 164 testes foram executados com sucesso. Os 6 testes GTK permanecem para execução em uma sessão gráfica com as dependências instaladas; não se declara uma execução interativa validada no Fedora.

Para repetir a suíte no sistema de destino:

```bash
./test.sh
```

Para executar somente a integração gráfica em uma sessão GNOME:

```bash
.venv/bin/python -m unittest discover -s tests -p test_gtk_experiments.py -v
```

## Organização do código

- `nexum/core/experiment_session.py`: entradas, validação, estado, curva e descrições didáticas.
- `nexum/ui/experiments_page.py`: ligação dos controles GTK com a sessão.
- `nexum/ui/experiment_drawing.py`: renderização Cairo independente de GTK.
- `nexum/core/engine.py` e `nexum/core/advanced/engine.py`: registro `ScientificEngine` / `default_engine`. As importações internas e a documentação usam esses nomes.

As calculadoras, os formatos de estruturas, o histórico e a instalação conservam seu funcionamento anterior. A pequena correção numérica da titulação é compartilhada com as calculadoras que usam o mesmo balanço ácido-base.
