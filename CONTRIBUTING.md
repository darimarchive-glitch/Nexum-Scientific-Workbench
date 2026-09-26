# Contribuir com o Nexum

Uma contribuição científica deve explicar pergunta, modelo, unidades, hipóteses, entradas válidas e limitações. Inclua referências e teste contra um caso analítico, conservação ou fonte independente; reproduzir a própria implementação em outro teste não basta.

Mantenha o cálculo independente da interface. Operações longas devem liberar a thread GTK. Dados originais não podem ser substituídos silenciosamente por dados processados. Não use `eval`, pickle ou execução automática de código ao abrir projetos.

Antes de propor uma mudança:

```bash
python -m unittest discover -s tests -v
python -m compileall -q nexum
python scripts/update_catalog.py --check
python scripts/check_project.py
```

Informe casos ignorados, plataforma, dependências, limites conhecidos e comportamento esperado. Novas funcionalidades gráficas exigem verificação em uma sessão GTK real. Alterações de embalagem exigem teste do artefato instalado no sistema correspondente.

Consulte [arquitetura](docs/development/architecture.md), [métodos científicos](docs/science/laboratory-methods.md) e [distribuição](docs/distribution/README.md). Não versione ambientes virtuais, tokens, dados particulares, caches ou binários temporários. A publicação é uma decisão separada do mantenedor.
