# Changelog

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
