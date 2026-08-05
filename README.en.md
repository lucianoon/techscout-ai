# TechScout AI

*[Versão em português](README.md)*

[![CI](https://github.com/lucianoon/techscout-ai/actions/workflows/ci.yml/badge.svg)](https://github.com/lucianoon/techscout-ai/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)

A market-intelligence system that treats **relationships** as first-class
citizens. An LLM extracts *subject–relation–object* triples from news articles
and materialises them into a NetworkX graph; in parallel, the same texts go
into a ChromaDB vector index. A query hits both structures, and the answer is
synthesised over both — with the graph facts shown verbatim, so you can see
*why* a connection was asserted.

## Why a graph, when vector search already exists

Vector search retrieves passages *similar* to the question. It does well on
"what is being said about LLM optimisation" and poorly on "what connects
Nebula AI to OldTech" — because the answer lives in no single passage: it
emerges from two sentences in different documents.

That is exactly what the graph solves.
`Pedro Santos --[former_employee_of]--> OldTech` and
`Pedro Santos --[advisor_to]--> Nebula AI` come from separate articles; the
link only exists once both became edges. Neighbourhood expansion walks those
hops; the vector index covers everything else.

## Evidence at a glance

| Evidence | What it demonstrates |
|---|---|
| 126 offline tests | Graph, persistence, LLM parsing, ingestion and data sources |
| 82% branch coverage, ≥ 75% gate in CI | Coverage measured, regressions blocked |
| Suite runs without `OPENAI_API_KEY` | Dependency injection plus degradation paths |
| `ruff` + `mypy` as gates | Lint and types enforced, not aspirational |
| JSON persistence, pickle refused | Loading a graph does not execute arbitrary code |
| Explicit degradation without a key | Semantic search falls back to textual instead of failing |

**What is not measured:** this repository has **no** retrieval-quality
baseline. There is no labelled dataset, no Recall@K, no MRR — so there is no
basis to claim the graph improves answers over plain vector search. The tests
guarantee the system behaves as specified, not that the extracted triples are
factually correct. See [limitations](#known-limitations).

## Architecture

```
articles (RSS / NewsAPI / file)
        │
        ├──► TripleExtractor ──► validated triples ──► GraphRAG (NetworkX)
        │      (LLM, closed                              │  graph_data.json
        │       relation vocabulary)                     │
        │                                                ├─ search()          textual match + expansion
        │                                                └─ semantic_search() node embeddings
        │
        └──► VectorStore (ChromaDB) ──► similarity_search()
                        │
                        ▼
              LLM synthesis over both contexts
```

| Module | Responsibility |
|---|---|
| `triple_extractor.py` | Extracts and **validates** triples; drops malformed JSON |
| `graph_rag.py` | Graph, textual and semantic search, JSON persistence |
| `vector_store.py` | ChromaDB, lazily built embeddings |
| `ingestion.py` | Orchestrates extraction → graph → index → vectors |
| `data_sources.py` | RSS feeds and NewsAPI, with rate limiting |
| `ui/` | Streamlit: sidebar, form, pyvis visualisation |

## Installation

```bash
git clone https://github.com/lucianoon/techscout-ai.git
cd techscout-ai
python -m venv .venv
source .venv/bin/activate      # Windows: .venv\Scripts\activate
pip install -e ".[dev]"

cp .env.example .env           # fill in OPENAI_API_KEY
```

## Usage

```bash
# 1. Ingest the sample corpus (4 fictional articles)
python scripts/ingest.py

# or from real RSS feeds
python scripts/ingest_online.py

# 2. Interface
streamlit run streamlit_app.py
```

Questions that exercise the graph, not just the vector index:

- *Who is Ana Souza and what is she involved in?*
- *What links Nebula AI to OldTech?*
- *Which investors appear connected to technical founders?*

### Docker

```bash
docker compose up --build     # http://localhost:8501
```

## Configuration

Every variable is documented in [`.env.example`](.env.example). The ones that
most change behaviour:

| Variable | Default | Effect |
|---|---|---|
| `OPENAI_API_KEY` | — | Required. Without it semantic search degrades to textual |
| `OPENAI_MODEL` | `gpt-3.5-turbo` | Extraction and synthesis model |
| `VECTOR_SEARCH_K` | `3` | Documents returned per query |
| `GRAPH_EXPANSION_DEPTH` | `1` | Degrees of separation walked in the graph |
| `ALLOW_PICKLE_GRAPH_LOAD` | `0` | See [Security](#security) before enabling |

## Development

```bash
make check     # lint + typecheck + test — exactly what CI runs
make test      # pytest with branch coverage and a 75% floor
```

Tests must not depend on an API key or the network. `TripleExtractor` and
`VectorStore` accept injected clients; the `no_api_key` fixture covers the
degraded path. See [CONTRIBUTING.md](CONTRIBUTING.md).

## Known limitations

In order of importance to anyone evaluating this project:

1. **No retrieval baseline.** There is no labelled dataset and no quality
   metric. The hypothesis that the graph improves relational answers is
   plausible and unverified here.
2. **Triple quality is LLM quality.** Extraction uses a closed vocabulary
   (`founded`, `invested_in`, `acquired`, …) at temperature 0, which buys
   consistency, not correctness. Wrong triples become wrong edges, and the
   graph cannot tell them apart.
3. **The graph is simple and undirected.** Two relations between the same pair
   of entities do not coexist: the second overwrites the first. `Ana
   --[founded]-- Acme` followed by `Ana --[sold]-- Acme` leaves only `sold`. A
   `MultiDiGraph` would fix it, at the cost of rewriting search.
4. **Full reindexing.** When the node count diverges from the vector index,
   the index is rebuilt in full — fine at thousands of nodes, not at hundreds
   of thousands.
5. **Minimal sample corpus.** Four fictional articles: enough to demonstrate
   the mechanism, not enough for any conclusion about scale.

## Security

Older versions persisted the graph as `pickle`. Deserialising pickle
**executes code** contained in the file, so that path is disabled by default
and only runs with `ALLOW_PICKLE_GRAPH_LOAD=1`. The current format is JSON.
Prefer re-running ingestion over enabling the flag.

Because the system ingests external text and hands it to an LLM, **prompt
injection through an ingested document** is a real vector. See
[SECURITY.md](SECURITY.md).

## Documentation

- [Detailed architecture](docs/ARCHITECTURE.md)
- [Data sources and online ingestion](docs/DATA_SOURCES.md)
- [Interface usage](docs/USAGE.md)
- [Troubleshooting](docs/TROUBLESHOOTING.md)

## License

MIT — see [LICENSE](LICENSE).
