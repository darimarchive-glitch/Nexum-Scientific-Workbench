# Análise e visualização — Nexum 6.8

O catálogo informa separadamente calculadoras, bancadas e ferramentas de análise. `nexum/catalog.py` consulta os registros; `python scripts/update_catalog.py` atualiza o resumo deste README e `--check` impede divergências na integração contínua.

## Estruturas

O painel de análise permite escolher distância (dois átomos), ângulo (três) ou diedro (quatro). A ordem dos cliques define o diedro. Distâncias usam Å; ângulos usam graus. Pontos coincidentes e diedros colineares são rejeitados. A seleção também funciona no diagrama 2D.

Seleção: símbolo de elemento (`O`), `água`, `ligantes`, `cadeia:A`, `resíduo:ALA` e `grupo:Carbonila`. Grupos disponíveis: Hidroxila, Carbonila, Carboxila, Amina, Amida e Anel aromático. Gerar 2D/grupos/cargas exige conectividade e ordens de ligação válidas, com limite de 3.000 átomos. As cargas são estimativas empíricas Gasteiger, não resultados ab initio. O destaque da seleção usa amarelo. Cores por categorias usam paleta cíclica; categorias com mais cores que a paleta podem repetir cor.

O contorno de van der Waals adapta contraste ao fundo e mantém o interior transparente. Não representa força, nuvem eletrônica ou potencial. Superfícies VDW/SAS usam união de esferas em grade; SES é uma aproximação por erosão da união expandida pelo raio da sonda, não uma superfície analítica exata. Resolução 20–80; máximo 30.000 átomos. O espaçamento efetivo é informado: refinar a grade pode alterar cavidades pequenas. Recalcule após alterar filtros. O plano de corte acompanha a profundidade da câmera; não fecha os cortes com tampas artificiais.

Fixar referência guarda uma cópia; a comparação abre duas vistas com rotação/zoom vinculados. PNG usa o framebuffer OpenGL em resolução ampliada, limitado a 4096 pixels por dimensão. Gráficos SVG/PDF conservam séries, eixos e legendas.

## Cube e modos vibracionais

Cube: um único campo escalar por arquivo, no máximo 128 pontos por eixo e 1,1 milhão de amostras. Contagens positivas significam coordenadas em Bohr; negativas em Å. Arquivos com lista de múltiplos orbitais devem ser exportados como campos separados. Informe método/base e unidade do campo. O Nexum não infere essas informações do valor numérico.

Orbital: azul indica sinal negativo e laranja positivo. Densidade e orbitais são isosuperfícies do campo importado. Potencial: calcule uma superfície antes; o Cube precisa estar no mesmo referencial espacial, e a superfície deve caber na grade. O programa interpola os valores, mas não verifica alinhamento químico automaticamente nem calcula o campo eletrônico.

Modos JSON: `method` (texto), `frequencies_cm1` (lista), `displacements` (modo × átomo × xyz) e `intensities` (lista opcional). A ordem dos átomos deve corresponder exatamente à estrutura carregada. Frequências nulas/imaginárias não são animadas como vibrações estáveis. A animação normaliza a amplitude para até 0,3 Å e usa 1 ciclo/s para visualização; não é dinâmica molecular. A superfície é removida durante a animação para evitar geometria inconsistente.

## Dados e experimentos

CSV aceita cabeçalho opcional, duas colunas, vírgula, ponto e vírgula ou tabulação. Vírgula decimal é aceita com ponto e vírgula/tabulação. Os pares são ordenados por x, mas duplicatas, valores não finitos e linhas numéricas inválidas são rejeitados. O original permanece separado do espectro corrigido. A integração usa trapézios e interpola os limites; picos são máximos por proeminência, sem identificação automática de moléculas.

Calibração: mínimos quadrados ordinários e incerteza padrão (k=1) da previsão inversa para uma leitura desconhecida. Pressupõe x sem incerteza e resíduos independentes homocedásticos. Extrapolação é indicada. Cinética: ajuste na escala de concentração de ordens 0, 1 e 2; resíduos e AIC ajudam a comparar, não provam mecanismo. Leituras negativas decorrentes do ruído não são silenciosamente truncadas; devem ser avaliadas antes de ajustar os modelos não negativos.

Titulação poliprótica: até três prótons, ácido inicialmente não neutralizado, base forte, equilíbrio ideal a 25 °C. Balanço de carga inclui água; etapas próximas podem não apresentar picos separados. Padrões isotópicos: abundâncias naturais do RDKit, até 150 átomos, 2048 combinações mais prováveis por passo, limiar de intensidade relativo; não simula fragmentação nem enriquecimento. Informe a fórmula completa da espécie iônica, incluindo aduto; o algoritmo corrige massa de elétrons, não adiciona prótons automaticamente.

As bancadas de calibração, comparação cinética e titulação poliprótica são acessíveis também pela aba Experimentos. Curvas podem ser reproduzidas ponto a ponto e guardadas para comparação; somente curvas do mesmo tipo e com as mesmas unidades são sobrepostas. Até oito referências por sessão.

## Sessões

Os botões no cabeçalho salvam/abrem `.nexum` (JSON versionado, até 100 MB). Incluem geometria e superfície, configuração visual, referência de comparação, calculadora atual e resultados, experimento e tempo, análise com dados originais, parâmetros, curvas e observações. Não salvam credenciais nem executam código. Sessões não são cópias de todo o histórico SQLite. Arquivos Cube completos não são embutidos; a superfície resultante e sua descrição são preservadas.

## Processos

Perda de carga: Darcy–Weisbach, laminar com f=64/Re e turbulento por Haaland; transição 2300≤Re<4000 rejeitada. Tubo circular, densidade/viscosidade constantes, sem perdas localizadas. Troca térmica: contracorrente ideal, F=1, U constante, temperaturas terminais coerentes. Cromatografia: larguras na base, não FWHM, tempos na mesma unidade.

Referências de implementação: [RDKit](https://www.rdkit.org/docs/source/rdkit.Chem.rdchem.html), [SciPy curve_fit](https://docs.scipy.org/doc/scipy/reference/generated/scipy.optimize.curve_fit.html), [superfícies moleculares no Jmol](https://jmol.sourceforge.net/docs/surface/).
