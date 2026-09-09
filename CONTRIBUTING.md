# Contribuir com o Nexum GNOME

Esta edição usa a branch `main`. Crie sua branch de trabalho a partir dela e direcione os pull requests para essa mesma base.

## Preparar o ambiente

No Fedora, execute `./install-fedora.sh`. O instalador prepara o ambiente e roda a suíte. Use `./run.sh` para abrir o aplicativo e `./test.sh` para verificar alterações.

## Melhorar um modelo científico

Descreva equações, unidades, estados padrão, hipóteses e domínio de validade. Referencie a fonte dos parâmetros. Implemente o cálculo no núcleo, mantendo a interface responsável pela apresentação e pelos controles.

Inclua uma verificação independente adequada à mudança: solução analítica, benchmark rastreável, conservação de massa/carga/energia ou transformação de entradas cuja consequência seja conhecida. Registre tolerâncias e diagnósticos quando relevantes. Atualize a documentação científica afetada.

## Relatar um problema

Informe versão do Nexum, Fedora e Python, bancada ou calculadora, entradas completas, passos de reprodução, resultado observado e resultado esperado com sua referência. Para problemas visuais, inclua captura e resolução da janela. Para carregamento molecular, informe identificador e fonte, como CID/PubChem ou código PDB/RCSB.

## Abrir um pull request

Explique o problema, o comportamento resultante e como foi verificado. Diferencie testes aprovados de testes ignorados por dependências ou display ausentes. Para mudanças visuais, verifique a aplicação em uma sessão gráfica e anexe capturas reais.
