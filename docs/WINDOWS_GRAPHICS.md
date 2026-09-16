# Compatibilidade gráfica no Windows — 6.8.1

O erro “Tentando usar EGL, mas ele foi desativado via GDK_DISABLE” pode
aparecer depois de o GTK falhar ao iniciar o OpenGL nativo. Essa mensagem
descreve a alternativa bloqueada, não necessariamente a falha original.
O visualizador usa OpenGL desktop 3.3 e shaders GLSL 330; habilitar EGL/GLES
sozinho não resolve a compatibilidade com esses shaders e com PyOpenGL/WGL.

O instalador 6.8.1 inclui Mesa 26.0.3 (llvmpipe) em uma pasta privada do
aplicativo. Antes de abrir a interface, o executável verifica o OpenGL nativo
em um processo separado. Em caso de erro, encerramento anormal ou demora
superior a 25 segundos, verifica o modo por software. Nenhuma DLL do Windows
é substituída. Computadores com OpenGL nativo funcional continuam usando-o.

A renderização por software usa o processador e pode ser mais lenta em
estruturas grandes. Atualizar o driver oficial da GPU pode restabelecer a
aceleração nativa. O programa verifica novamente a cada abertura.

Os diagnósticos ficam em `%LOCALAPPDATA%\Nexum\graphics`: `native.log`,
`software.log` (quando usado) e `selected.txt` (modo selecionado).
Para suporte técnico, `NEXUM_GRAPHICS=software` força o modo de compatibilidade,
`native` permite testar apenas o driver nativo e `auto` é o padrão.

O teste do instalador não instala Mesa globalmente no computador de testes.
Ele verifica a seleção automática no executável empacotado e força llvmpipe
na cópia instalada, com PATH sem Python/MSYS2. Além de verificar o nome do
renderizador, executa os shaders e exporta imagens do visualizador real.

O pacote Mesa é baixado de uma versão fixa e seu SHA-256 é conferido antes
de incluí-lo. Seus avisos de distribuição acompanham o programa.

Esta seleção automática se aplica ao executável Windows instalado. O
lançador de desenvolvimento em `scripts/windows/nexum.ps1` continua exigindo
OpenGL nativo funcional. O Flatpak mantém a integração gráfica do Linux.
