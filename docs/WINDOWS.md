# Nexum no Windows

Suporte nativo a **Windows 10/11 x64**, mantendo GTK4/libadwaita, as calculadoras,
as oito bancadas, o visualizador OpenGL e o histórico SQLite. Não usa WSL.
Esta distribuição executa o código-fonte com dependências instaladas; não é um
instalador `.exe` independente.

## Instalar

1. Instale [MSYS2](https://www.msys2.org/) em `C:\msys64` e
   [CPython 3.12 x64](https://www.python.org/downloads/windows/) com o launcher `py`.
   Se tiver WinGet, pode executar no Terminal:

   ```powershell
   winget install --exact --id MSYS2.MSYS2
   winget install --exact --id Python.Python.3.12
   ```

2. Abra um novo terminal. Baixe e extraia o projeto, ou clone a branch desejada.
   Use uma pasta gravável pelo seu usuário, por exemplo `Documentos\Nexum`.
3. Dê dois cliques em **`install-windows.cmd`**. Ele instala as dependências,
   verifica GTK, Cairo, leitura mmCIF, geração RDKit, SQLite e shaders OpenGL,
   executa a suíte e cria um atalho na Área de Trabalho.
4. Abra **`run-windows.cmd`** ou o atalho **Nexum**.

A instalação precisa de internet e pode levar vários minutos. Ela atualiza os
pacotes da instalação MSYS2 escolhida; feche outras sessões MSYS2 antes de iniciar.
Se uma atualização do próprio MSYS2 encerrar o terminal, execute o instalador
novamente. Ele reaproveita o que já foi instalado. Falhas mantêm a janela aberta
e retornam código diferente de zero.

Para MSYS2 ou Python em outro local:

```powershell
.\install-windows.cmd -MsysRoot "D:\msys64" -PythonExe "C:\caminho\Python312\python.exe"
```

O caminho do MSYS2 fica salvo localmente. Os lançadores funcionam fora da pasta
do projeto e aceitam caminhos com espaços. Se mover o projeto, remova apenas
`.venv-science` e execute novamente o instalador para recriar o ambiente e o atalho.

## Comandos

| Arquivo | Função |
| --- | --- |
| `install-windows.cmd` | Instalar dependências, diagnosticar, testar e criar atalho |
| `run-windows.cmd` | Abrir o aplicativo |
| `test-windows.cmd` | Diagnóstico completo e suíte de testes |
| `diagnose-windows.cmd` | Diagnóstico de dependências, química e OpenGL |
| `install-windows-shortcut.cmd` | Recriar o atalho |

O PowerShell é configurado somente para o processo do lançador. Nenhum comando
modifica permanentemente o `PATH` ou a política de execução do Windows.

## Dados e arquitetura

O histórico fica em `%LOCALAPPDATA%\Nexum\history.sqlite3` e o cache em
`%LOCALAPPDATA%\Nexum\Cache\structures`. Atualizar o código não apaga esses dados.
Os caminhos usados anteriormente no Linux permanecem iguais.

A interface usa os pacotes nativos UCRT64 do MSYS2, conforme a
[orientação do GTK](https://www.gtk.org/docs/installations/windows/).
NumPy e SciPy também vêm desse ambiente. Gemmi e RDKit usam as wheels de CPython
em `.venv-science`, com as versões permitidas por `requirements.txt`.

Esses dois ambientes não compartilham módulos binários. Apenas leitura mmCIF e
geração de conformadores passam por um subprocesso local com mensagens JSON,
operações permitidas explícitas e timeout de 180 segundos. O mesmo código químico
produz os resultados nos dois sistemas. Não há serviço de rede nem troca de
equações ou métodos científicos. Não execute `pip install -r requirements.txt`
no Python MinGW para tentar instalar wheels de CPython.

## Gráficos e diagnóstico

O visualizador exige **OpenGL desktop 3.3**. O lançador seleciona Win32/WGL e
desabilita EGL/GLES para alinhar GTK e PyOpenGL. Instale o driver de vídeo do
fabricante se o diagnóstico não conseguir criar o contexto ou compilar os shaders.
Os ajustes de escala usam pixels físicos no framebuffer e preservam as coordenadas
lógicas de seleção do mouse.

## Validação

O workflow `Windows and scientific regressions` executa o backend em Linux e
Windows e o instalador real em Windows, em uma pasta com espaços, com GTK/Cairo,
RDKit/gemmi, testes e compilação dos shaders. O runner usa Mesa por software;
isso não comprova o comportamento de todas as GPUs físicas.

Antes de publicar como versão estável, confira o resultado do workflow e faça
uma sessão manual no Windows: abrir todas as páginas, calcular e reabrir o
histórico, controlar as oito bancadas, buscar no PubChem/RCSB, girar moléculas,
selecionar átomos, alternar tela cheia e testar escalas 100%, 150% e 200%.
Testes ignorados (`skipped`) não contam como aprovados. O resultado desta
preparação está em [VALIDACAO-WINDOWS.md](VALIDACAO-WINDOWS.md).
