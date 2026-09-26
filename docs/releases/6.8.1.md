# Nexum 6.8.1 — compatibilidade gráfica no Windows

Corrige a tela vazia do visualizador molecular quando o Windows não consegue
iniciar o OpenGL nativo e exibe “Tentando usar EGL, mas ele foi desativado via
GDK_DISABLE”. O instalador agora inclui Mesa/llvmpipe e seleciona esse modo
automaticamente quando o teste inicial do driver nativo falha.

## Instalar

- **Windows:** baixe `Nexum-Setup-6.8.1-x64.exe`, feche o Nexum e execute o instalador. É possível instalar sobre a versão 6.8.0. Não é necessário instalar Python ou componentes gráficos separadamente.
- **Linux:** baixe `Nexum-x86_64.flatpak` e abra com a loja de aplicativos. A integração gráfica do Linux permanece a mesma.
- `Reparar-atalho-Nexum.sh` restaura a entrada do aplicativo no menu Linux quando necessário.
- `SHA256SUMS.txt` contém os hashes dos arquivos distribuídos.

## Funcionamento

Computadores com OpenGL nativo funcional continuam usando a GPU. O modo de
compatibilidade usa o processador e pode ser mais lento com estruturas grandes.
Os diagnósticos ficam em `%LOCALAPPDATA%\Nexum\graphics`.

O componente alternativo fica dentro da instalação do Nexum; o programa não
substitui drivers nem DLLs do Windows. O teste do instalador exige renderização
real com a cópia incluída no pacote, sem Mesa instalado globalmente no runner.

A validação automatizada não cobre todos os modelos de GPU e versões de driver.
Se a visualização continuar falhando, envie os arquivos de diagnóstico acima.
