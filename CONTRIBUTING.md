# Contribuir com o Nexum

O Nexum é um projeto proprietário com código-fonte disponível para inspeção. Contribuições são bem-vindas apenas sob os termos abaixo e não transformam o projeto em software open source.

## Termos para contribuições

Ao enviar código, documentação, arte, dados ou outro material protegido por direitos autorais para inclusão no Nexum, você declara que tem o direito de enviá-lo e concede ao mantenedor do Nexum uma licença perpétua, mundial, irrevogável, não exclusiva e livre de royalties para reproduzir, modificar, criar obras derivadas, distribuir, sublicenciar e relicenciar essa contribuição como parte do Nexum, inclusive em versões proprietárias e comerciais.

Se você não puder conceder esses direitos, não envie a contribuição sem antes obter um acordo escrito específico com o mantenedor.

A contribuição não concede ao colaborador direitos sobre o restante do Nexum. Bibliotecas, dados e outros componentes de terceiros continuam sujeitos às respectivas licenças.

## Requisitos técnicos

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

Consulte [arquitetura](docs/development/architecture.md), [métodos científicos](docs/science/laboratory-methods.md), [distribuição](docs/distribution/README.md) e [LICENSE](LICENSE). Não versione ambientes virtuais, tokens, dados particulares, caches ou binários temporários. A publicação é uma decisão separada do mantenedor.
