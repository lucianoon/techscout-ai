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
| Baseline medido: Recall@K e MRR | Grafo, BM25 e a fusão dos dois, sobre dataset rotulado |
| 171 testes offline | Grafo, persistência, parsing de LLM, ingestão, fontes e métricas |
| 82% de branch coverage, gate ≥ 75% na CI | Cobertura medida e regressão bloqueada |
| Suíte e baseline rodam sem `OPENAI_API_KEY` | Injeção de dependência + recuperadores determinísticos |
| Baseline reexecutado a cada push | Mudança de ranqueamento aparece no log da CI |
| `ruff` + `mypy` como gates | Lint e tipos verificados, não aspiracionais |
| Persistência em JSON, pickle recusado | Carregar grafo não executa código arbitrário |

## Baseline de recuperação

Os dois lados devolvem uma lista ordenada de documentos e são medidos pelo
mesmo rótulo. Corpus de 15 documentos, 15 perguntas rotuladas, grafo curado à
mão — para separar a qualidade da *recuperação* da qualidade da *extração*.

**Perguntas relacionais** (n=10), k=5:

| Recuperador | Recall@5 | MRR |
|---|---:|---:|
| BM25 | 0,750 | 0,767 |
| Grafo | **0,800** | 0,708 |
| Híbrido (RRF) | **0,800** | **0,850** |

```bash
python -m techscout.evaluation -k 5   # reproduz, sem chave de API
```

**O que os números dizem — e o que não dizem.** O grafo alcança mais
documentos relevantes que o BM25, mas os *ordena pior*: encontra o que importa
e falha em pôr em primeiro. E essa vantagem de recall **não é estável**: o
grafo ganha em k=2 e k=5 e perde em k=3. Com 15 perguntas, isso é ruído — não
dá para afirmar que o grafo supera o BM25 em recall.

O achado que se sustenta é outro: **o híbrido é igual ou melhor que ambos em
todos os cortes de k e nas duas métricas**. É o que justifica manter as duas
estruturas em vez de escolher uma. Nas perguntas factuais de controle o BM25
acerta tudo, como esperado — se o grafo tivesse vencido ali, o dataset estaria
enviesado.

Metodologia, procedência e limitações em
[docs/BENCHMARK_RESULTS.md](docs/BENCHMARK_RESULTS.md). Ainda **não** medido:
acurácia da extração de triplas por LLM e fidelidade da resposta final.

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
make eval      # Recall@K e MRR do grafo, do BM25 e da fusão
```

Testes não podem depender de chave de API nem de rede. `TripleExtractor` e
`VectorStore` aceitam clientes injetados; a fixture `no_api_key` cobre o
caminho degradado. Detalhes em [CONTRIBUTING.md](CONTRIBUTING.md).

## Limitações conhecidas

Em ordem de importância para quem for avaliar o projeto:

1. **O baseline é pequeno demais para ser conclusivo.** 15 perguntas e 15
   documentos: uma pergunta a mais ou a menos move o Recall em ~0,07. Trate
   diferenças abaixo de ~0,10 como indistinguíveis, e veja a
   [inversão em k=3](docs/BENCHMARK_RESULTS.md#leitura-honesta) antes de citar
   qualquer número.
2. **O grafo do benchmark é curado, não extraído.** Isso é proposital — isola
   recuperação de extração — mas significa que o erro de extração por LLM
   *não* está contabilizado nos números publicados.
3. **A qualidade das triplas é a qualidade do LLM.** A extração usa um
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

- [Resultados do baseline de recuperação](docs/BENCHMARK_RESULTS.md)
- [Arquitetura detalhada](docs/ARCHITECTURE.md)
- [Fontes de dados e ingestão online](docs/DATA_SOURCES.md)
- [Uso da interface](docs/USAGE.md)
- [Troubleshooting](docs/TROUBLESHOOTING.md)

## Licença

MIT — ver [LICENSE](LICENSE).
