# TechScout AI

*[English version](README.en.md)*

[![CI](https://github.com/lucianoon/techscout-ai/actions/workflows/ci.yml/badge.svg)](https://github.com/lucianoon/techscout-ai/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)

Um sistema de inteligência de mercado que trata **relações** como cidadãs de
primeira classe. Um LLM extrai triplas *sujeito–relação–objeto* de notícias e
as materializa em um grafo NetworkX; em paralelo, os textos vão para um índice
vetorial no ChromaDB. Uma consulta atinge as duas estruturas e a resposta é
sintetizada sobre as duas — com os fatos do grafo expostos literalmente, para
que se veja *por que* uma conexão foi afirmada.

## Por que um grafo, se já existe busca vetorial

Busca vetorial recupera trechos *parecidos* com a pergunta. Ela vai bem em
"o que se diz sobre otimização de LLMs" e mal em "quem conecta a Nebula AI à
OldTech" — porque a resposta não está em nenhum trecho isolado: ela emerge de
duas frases em documentos diferentes.

O grafo resolve exatamente isso. `Pedro Santos --[ex_funcionario_de]--> OldTech`
e `Pedro Santos --[consultor_de]--> Nebula AI` vêm de notícias distintas; a
ligação só existe depois que ambas viram arestas. A expansão de vizinhança
percorre esses saltos; o índice vetorial cobre o resto.

## Evidências rápidas

| Evidência | O que demonstra |
|---|---|
| 126 testes offline | Grafo, persistência, parsing de LLM, ingestão e fontes de dados |
| 82% de branch coverage, gate ≥ 75% na CI | Cobertura medida e regressão bloqueada |
| Suíte roda sem `OPENAI_API_KEY` | Injeção de dependência + caminhos de degradação |
| `ruff` + `mypy` como gates | Lint e tipos verificados, não aspiracionais |
| Persistência em JSON, pickle recusado | Carregar grafo não executa código arbitrário |
| Degradação explícita sem chave | Busca semântica cai para textual em vez de falhar |

**O que não está medido:** este repositório **não** tem baseline de qualidade
de recuperação. Não há dataset rotulado, nem Recall@K, nem MRR — logo, não há
como afirmar que o grafo melhora as respostas em relação a busca vetorial
pura. O que os testes garantem é que o sistema se comporta como especificado,
não que as triplas extraídas estejam corretas. Ver
[limitações](#limitações-conhecidas).

## Arquitetura

```
notícias (RSS / NewsAPI / arquivo)
        │
        ├──► TripleExtractor ──► triplas validadas ──► GraphRAG (NetworkX)
        │      (LLM, vocabulário                          │  graph_data.json
        │       fechado de relações)                      │
        │                                                 ├─ search()          casamento textual + expansão
        │                                                 └─ semantic_search() embeddings dos nós
        │
        └──► VectorStore (ChromaDB) ──► similarity_search()
                        │
                        ▼
             síntese pelo LLM sobre os dois contextos
```

| Módulo | Responsabilidade |
|---|---|
| `triple_extractor.py` | Extrai e **valida** triplas; descarta JSON malformado |
| `graph_rag.py` | Grafo, busca textual e semântica, persistência JSON |
| `vector_store.py` | ChromaDB, embeddings sob demanda |
| `ingestion.py` | Orquestra extração → grafo → índice → vetores |
| `data_sources.py` | Feeds RSS e NewsAPI, com rate limiting |
| `ui/` | Streamlit: sidebar, formulário, visualização pyvis |

## Instalação

```bash
git clone https://github.com/lucianoon/techscout-ai.git
cd techscout-ai
python -m venv .venv
source .venv/bin/activate      # Windows: .venv\Scripts\activate
pip install -e ".[dev]"

cp .env.example .env           # preencha OPENAI_API_KEY
```

## Uso

```bash
# 1. Ingestão a partir do corpus de exemplo (4 notícias fictícias)
python scripts/ingest.py

# ou de feeds RSS reais
python scripts/ingest_online.py

# 2. Interface
streamlit run streamlit_app.py
```

Perguntas que exercitam o grafo, não só o índice vetorial:

- *Quem é a Ana Souza e em que ela está envolvida?*
- *Qual a ligação entre a Nebula AI e a OldTech?*
- *Que investidores aparecem conectados a fundadores técnicos?*

### Docker

```bash
docker compose up --build     # http://localhost:8501
```

## Configuração

Todas as variáveis estão documentadas em [`.env.example`](.env.example). As
que mais alteram o comportamento:

| Variável | Padrão | Efeito |
|---|---|---|
| `OPENAI_API_KEY` | — | Obrigatória. Sem ela a busca semântica degrada para textual |
| `OPENAI_MODEL` | `gpt-3.5-turbo` | Modelo de extração e síntese |
| `VECTOR_SEARCH_K` | `3` | Documentos retornados por consulta |
| `GRAPH_EXPANSION_DEPTH` | `1` | Graus de separação percorridos no grafo |
| `ALLOW_PICKLE_GRAPH_LOAD` | `0` | Ver [Segurança](#segurança) antes de ligar |

## Desenvolvimento

```bash
make check     # lint + typecheck + test — o mesmo que a CI roda
make test      # pytest com cobertura de branch e piso de 75%
```

Testes não podem depender de chave de API nem de rede. `TripleExtractor` e
`VectorStore` aceitam clientes injetados; a fixture `no_api_key` cobre o
caminho degradado. Detalhes em [CONTRIBUTING.md](CONTRIBUTING.md).

## Limitações conhecidas

Em ordem de importância para quem for avaliar o projeto:

1. **Sem baseline de recuperação.** Não há dataset rotulado nem métrica de
   qualidade. A hipótese de que o grafo melhora respostas relacionais é
   plausível e não verificada aqui.
2. **A qualidade das triplas é a qualidade do LLM.** A extração usa um
   vocabulário fechado (`fundou`, `investiu_em`, `adquiriu`, …) e temperatura
   0, o que dá consistência, não correção. Triplas erradas viram arestas
   erradas, e o grafo não sabe distingui-las.
3. **O grafo é simples e não-direcionado.** Duas relações entre o mesmo par de
   entidades não coexistem: a segunda sobrescreve a primeira. `Ana --[fundou]--
   Acme` seguido de `Ana --[vendeu]-- Acme` deixa apenas `vendeu`. Um
   `MultiDiGraph` resolveria, ao custo de reescrever a busca.
4. **Reindexação integral.** Quando a contagem de nós diverge do índice
   vetorial, ele é reconstruído por inteiro — aceitável em milhares de nós,
   não em centenas de milhares.
5. **Corpus de exemplo mínimo.** São 4 notícias fictícias, suficientes para
   demonstrar o mecanismo e insuficientes para qualquer conclusão sobre
   escala.

## Segurança

Versões antigas persistiam o grafo em `pickle`. Desserializar pickle **executa
código** contido no arquivo, então esse caminho é desabilitado por padrão e só
roda com `ALLOW_PICKLE_GRAPH_LOAD=1`. O formato atual é JSON. Prefira
reexecutar a ingestão a habilitar a flag.

Como o sistema ingere texto externo e o entrega a um LLM, **prompt injection
via documento** é um vetor real. Ver [SECURITY.md](SECURITY.md).

## Documentação

- [Arquitetura detalhada](docs/ARCHITECTURE.md)
- [Fontes de dados e ingestão online](docs/DATA_SOURCES.md)
- [Uso da interface](docs/USAGE.md)
- [Troubleshooting](docs/TROUBLESHOOTING.md)

## Licença

MIT — ver [LICENSE](LICENSE).
