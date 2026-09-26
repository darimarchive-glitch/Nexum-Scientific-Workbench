Instaladores prontos para Windows e Linux, com o logo oficial do Nexum, 43 calculadoras, 10 bancadas experimentais e 5 ferramentas de análise de dados.

## Windows

Baixe **Nexum-Setup-6.8.0-x64.exe**, abra o arquivo e siga o instalador. Não é necessário instalar Python ou MSYS2 separadamente. O instalador cria a entrada no menu Iniciar e oferece o atalho da área de trabalho, marcado por padrão.

Requisitos: Windows 10/11 de 64 bits e driver gráfico compatível com OpenGL 3.3.

## Linux

Com Flatpak disponível, baixe **Nexum-x86_64.flatpak** e abra pela loja de aplicativos compatível, ou instale pelo terminal na pasta do arquivo:

```bash
flatpak install --user ./Nexum-x86_64.flatpak
```

Depois, procure **Nexum** no menu de aplicativos. Também é possível abrir com:

```bash
flatpak run io.github.nexum.ScientificWorkbench
```

Se uma instalação anterior abrir pela loja, mas não aparecer no menu, baixe **Reparar-atalho-Nexum.sh** e execute:

```bash
bash Reparar-atalho-Nexum.sh
```

O reparador restaura o atalho e o logo no menu do usuário, preservando uma cópia do atalho anterior quando ele for diferente. Se necessário, saia da sessão e entre novamente para atualizar o menu.

## Nesta versão

- Camada de van der Waals com contraste adaptado ao fundo.
- Medições moleculares, superfícies, comparação de estruturas e sessões salvas.
- Análise de espectros, calibração, cinética, titulação poliprótica e padrões isotópicos.
- Ferramentas de análise concentradas na aba Análise, com ícone próprio.
- Busca de compostos frequentes em português brasileiro.

## Verificação

Os instaladores são os mesmos arquivos aprovados na execução [35033588559](https://github.com/darimarchive-glitch/Nexum-Scientific-Workbench/actions/runs/35033588559), produzidos a partir de `4141cbad2d18cbc26214bf6e81e6a32bcc949645`. A árvore desse código é idêntica à do merge `ece08726171cc15ad24ff880bda45b893f7ff62b`, identificado pela tag desta versão.

210 testes passaram no desktop Windows. Os pacotes Windows e Flatpak foram instalados e abertos nos testes automatizados; a integração de atalhos também foi verificada. **SHA256SUMS.txt** contém as somas de verificação dos três arquivos de distribuição.

Use os arquivos EXE e Flatpak em **Assets** para instalar. Os arquivos **Source code** gerados automaticamente pelo GitHub são destinados ao desenvolvimento.
