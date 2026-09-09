# UI/UX — GNOME industrial v6.0

## Princípio

A interface deve parecer uma **ferramenta científica de trabalho**, não um dashboard decorativo. A informação principal recebe espaço; controles secundários cedem, recolhem ou rolam.

## Calculadoras

- Sidebar padrão: ~184 px e recolhível.
- Uma categoria científica por vez; busca global atravessa todas as categorias.
- Formulário e resultado dividem a área central com `Gtk.Paned`.
- Resultado tem largura mínima útil e scroll próprio.
- Escopo científico aparece como badge contextual, não como selo genérico de “correto”.
- Gráficos aparecem apenas quando uma série/curva realmente acrescenta informação.

## Experimentos

Prioridade visual:

1. bancada/gráfico;
2. controles de execução;
3. medições;
4. configuração e explicações.

Parâmetros ficam editáveis quando o protocolo está parado. `Iniciar`, `Pausar`, `Passo` e `Zerar` permanecem no mesmo fluxo. Não é necessário trocar de página para observar o resultado.

## 3D

O visualizador ocupa a maior área. Busca fica no topo; representação/câmera/cadeias ficam no inspetor. Tela cheia remove o máximo de chrome possível.

## Regra contra sobreposição

Nunca resolver falta de espaço com elementos sobrepostos. Usar, nesta ordem:

1. `hexpand/vexpand` corretos;
2. `Gtk.Paned` redimensionável;
3. `Gtk.ScrolledWindow` local;
4. sidebar/revealer recolhível;
5. quebra/reorganização do layout.
