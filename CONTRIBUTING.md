# Como contribuir

## Ambiente

```bash
uv sync --extra dev --locked   # instala o pacote e as dependências travadas no uv.lock
cp .env.example .env           # preencha OPENAI_API_KEY
```

O `.env` é ignorado pelo git. Nunca faça commit de chaves — nem em exemplos,
issues ou logs colados.

## Antes de abrir o PR

Os três comandos abaixo são exatamente os que a CI executa:

```bash
make lint      # ruff check .
make typecheck # mypy
make test      # coverage run -m pytest && coverage report --fail-under=75
```

## O que a CI exige

| Gate | Critério |
|---|---|
| `ruff check` | sem violações |
| `mypy` | sem erros em `src/` |
| `pytest` | suíte verde |
| cobertura de branch | ≥ 75% |
| `docker build` | imagem constrói |

## Testes precisam rodar sem chave de API

A suíte não pode depender de `OPENAI_API_KEY` nem de rede. Há dois caminhos:

- **Injeção**: `TripleExtractor(llm=...)` e `VectorStore(embeddings=...)`
  aceitam um cliente pronto. Use o `FakeChatModel` do `tests/conftest.py`.
- **Fallback**: a fixture `no_api_key` remove a chave, para exercitar o
  comportamento degradado (por exemplo, `semantic_search` caindo para a busca
  textual).

Um teste que só passa com chave real é um teste que a CI não roda.

## Escopo dos testes

Priorize as fronteiras frágeis, não os getters:

- **Parsing de resposta do LLM** — é texto livre que só *deveria* ser JSON.
  Toda forma malformada nova encontrada em produção merece um caso.
- **Persistência** — roundtrip preservando relações e acentuação; e a recusa
  de carregar pickle sem opt-in explícito.
- **Semântica de busca** — expansão de vizinhança e os textos de "nenhum
  resultado", que a UI exibe literalmente.

## Estilo

`ruff` decide formatação e ordem de imports; não discuta com ele. Comentários
explicam *por quê*, não *o quê* — o código já diz o quê. Mensagens de log e
texto de usuário em português, para acompanhar o resto da base.

## Commits

Assunto no imperativo, em uma linha. Se o PR muda comportamento visível,
acrescente a entrada correspondente no `CHANGELOG.md` em `Unreleased`.
