# Changelog

## 0.3.0

Baseline de recuperação medido — a lacuna que o README da 0.2.0 declarava.

- Dataset rotulado versionado em `data/eval/`: 15 documentos, grafo de
  referência curado à mão e 15 perguntas com documentos relevantes anotados,
  separadas em relacionais, relacionais profundas e factuais (controle).
- `techscout.evaluation`: Recall@K e MRR sobre três recuperadores — BM25,
  grafo (por proveniência das arestas) e a fusão dos dois por reciprocal rank
  fusion. Todos determinísticos: rodam na CI sem chave de API.
- Proveniência nas arestas do grafo. `add_triple` passa a aceitar `fonte` e
  acumula os documentos que sustentam cada fato — é o que permite comparar
  grafo e busca por passagem na mesma escala, e completa a promessa do README
  de mostrar *por que* uma conexão foi afirmada.
- `GraphRAG.retrieve_documents`, que rankeia documentos por arestas-ponte
  entre os nós citados na pergunta. A primeira versão pontuava por volume de
  arestas e deixava nós-hub arrastarem documentos irrelevantes para o topo
  (MRR 0,524); a pontuação por produto das proximidades corrigiu isso
  (MRR 0,722).
- `make eval` e um passo na CI que reexecuta o baseline a cada push, para que
  uma mudança de ranqueamento apareça no log em vez de invalidar em silêncio
  os números publicados.
- 45 testes novos, incluindo integridade do dataset: toda fonte de tripla e
  todo documento rotulado precisam existir no corpus, e casos relacionais
  precisam exigir dois ou mais documentos.
- `docs/BENCHMARK_RESULTS.md` com procedência, resultados e a leitura honesta:
  a vantagem de recall do grafo **não é estável** (ganha em k=2 e k=5, perde
  em k=3, o que a n=15 é ruído). O achado que se sustenta é que a fusão supera
  ambos em todos os cortes.

## 0.2.0

Preparação do repositório para uso público. O comportamento em tempo de
execução não mudou; o que mudou foi o que é verificável.

- Suíte de testes criada do zero: **126 testes, 82% de branch coverage**,
  cobrindo operações do grafo, persistência JSON, recusa de pickle legado,
  parsing de resposta do LLM (cercas de markdown, prosa em volta do JSON,
  JSON malformado, triplas com chave ausente ou valor vazio), orquestração da
  ingestão e as fontes de dados externas. A suíte roda sem `OPENAI_API_KEY` e
  sem rede.
- CI no GitHub Actions com `ruff`, `mypy`, cobertura de branch com piso de
  75% e build da imagem Docker.
- Dependências corrigidas. `pyproject.toml` declarava `langchain-chroma==0.2.8`,
  versão que não existe no PyPI — `pip install -e .` falhava. `langchain` e
  `langchain-community` estavam declarados sem nenhum import correspondente.
  As versões passam a ser declaradas por limite inferior, e `requirements.txt`
  foi removido para eliminar a segunda fonte de verdade.
- 18 erros de tipagem corrigidos, entre eles `Optional` implícito, atributos
  anotados como `None` e depois reatribuídos, e `api_key` recebendo `str` onde
  o cliente espera `SecretStr`.
- `app_streamlit.py` reestruturado em torno de uma função `main()`. O módulo
  desenhava a interface no momento do import, o que obrigava o entry point a
  usar `from ... import *`.
- Removido o enxerto de `llm._model_name` no objeto do LLM: o nome do modelo
  já é devolvido por `render_sidebar` e repassado a `process_query`.
- `data/samples/` versionado com o corpus de exemplo, antes solto na raiz como
  `dados_mock.py`. `ingest_simple.py` era duplicata de `scripts/ingest.py` e
  foi removido.
- `TripleExtractor` e `VectorStore` passam a construir o cliente OpenAI sob
  demanda e aceitam injeção. Antes, instanciar qualquer um deles exigia uma
  chave de API, o que tornava impossível testar parsing e validação offline.
- Removidos **cinco** blocos duplicados de `try/except ImportError` em torno do
  import do próprio módulo de logging. A causa real era o `logger` falhar na
  importação quando o diretório de logs não era gravável; agora o handler de
  arquivo é omitido nesse caso e o console segue funcionando.
- Removida a cadeia de fallback de import de `Document` para versões de
  LangChain anteriores às fixadas em `pyproject.toml`.
- `.env.example` documentando cada variável, incluindo o motivo de
  `ALLOW_PICKLE_GRAPH_LOAD` permanecer desligado.
- `SECURITY.md` com escopo explícito de prompt injection e envenenamento de
  grafo, que são os vetores reais de um sistema que ingere texto externo.
- Documentação de processo consolidada: 15 arquivos de rascunho na raiz
  viraram quatro documentos em `docs/`.
- `langchain-chroma` declarado como dependência — era importado por
  `graph_rag.py` e `vector_store.py` sem constar em `pyproject.toml`.

## 0.1.0

- GraphRAG inicial: extração de triplas por LLM com vocabulário fechado de
  relações, grafo NetworkX persistido em JSON e busca vetorial em ChromaDB.
- Busca em duas modalidades: casamento textual sobre nós, com expansão por
  vizinhança configurável, e busca semântica sobre embeddings dos nós, com
  degradação automática para a textual quando não há chave de API.
- Ingestão a partir de feeds RSS e NewsAPI.
- Interface Streamlit com visualização do grafo.
- Empacotamento Docker e docker-compose.
