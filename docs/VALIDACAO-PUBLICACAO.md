# Verificação da publicação — Nexum GNOME 6.6

Data: 9 de setembro de 2026.

Origem: pacote `Nexum-Scientific-Workbench-GNOME-Fedora-v6.6(1).zip` fornecido pelo mantenedor nesta entrega. A preparação para GitHub atualizou o README, acrescentou guia de contribuição, exemplo executável, este registro e `.gitignore`, e marcou os quatro scripts shell como executáveis. O código da aplicação e os testes do pacote foram preservados.

## Resultado reproduzido

```text
Ran 170 tests
OK (skipped=12)
```

- 158 testes executados com sucesso.
- 6 testes de renderização ignorados por ausência de PyCairo.
- 6 testes de integração GTK ignorados por ausência de GTK4/libadwaita e display utilizável.
- Nenhuma falha ou erro na execução final.

A primeira execução identificou `gemmi` ausente. Após instalar a versão 0.7.5, a suíte foi executada novamente com sucesso. O teste de leitura mmCIF foi incluído nessa execução. A instalação de PyCairo foi tentada, mas as ferramentas/dependências nativas de compilação não estavam disponíveis.

## Ambiente e comandos

Ambiente Linux de preparação, sem sessão gráfica Fedora. Python 3.12.14, NumPy 2.3.5, SciPy 1.17.0 e gemmi 0.7.5. O gemmi foi instalado em um diretório temporário externo à árvore do projeto e disponibilizado por `PYTHONPATH` durante a execução de `bash test.sh`.

O script de testes executa `python -m unittest discover -s tests -v` e, em seguida, `python -m compileall -q nexum`. Também foram verificadas a sintaxe dos quatro scripts shell, a execução do exemplo Python do README e a existência dos destinos relativos da documentação.

O exemplo multicomponente recuperou aproximadamente 0,001 e 0,002 mol/L; RMSE de 2,27 × 10⁻¹⁷ e número de condição de aproximadamente 1,453. Foram confirmados no código: 35 ferramentas, 12 categorias, 8 sessões de bancada e 14 modelos registrados pelo motor avançado.

## Limites desta verificação

Esta execução não valida instalação interativa no Fedora, renderização OpenGL, geração de conformadores pelo RDKit, acesso real a PubChem/RCSB ou uso da GUI. RDKit e o stack gráfico não estavam disponíveis no Python utilizado. O resultado dos testes não constitui uma nova auditoria independente de todos os modelos científicos.

O documento `EXPERIMENTOS-v6.6.md` contém o resultado histórico informado no pacote original. Este arquivo registra especificamente a execução realizada durante a preparação para GitHub.

## Reproduzir no Fedora

```bash
chmod +x *.sh
./install-fedora.sh
./test.sh
```

Execute em uma sessão gráfica com as dependências nativas para também exercitar os testes GTK. Verifique explicitamente o total de casos `skipped` no resumo.
