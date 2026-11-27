# Contexto do Claude Code

O `CLAUDE.md` na raiz do repositório é carregado automaticamente pelo Claude Code ao abrir esta pasta e já contém o
estado do projeto. Esta pasta guarda, além disso, as memórias que o Claude acumulou (atualizadas em 27/11/2026 no notebook Linux Mint).

Para restaurá-las em outra máquina (opcional), copie os arquivos para a pasta de memória do projeto. O nome da pasta
é o caminho absoluto do repositório com `/` e espaços trocados por `-`:

```bash
DESTINO=~/.claude/projects/$(pwd | sed 's#[/ ]#-#g')/memory
mkdir -p "$DESTINO" && cp contexto_claude/memoria/*.md "$DESTINO"/
```

Execute a partir da raiz do repositório. O histórico completo da conversa não foi publicado (repositório público).
