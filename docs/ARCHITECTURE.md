# 📊 Visão Geral do Codebase - TechScout AI

## 🏗️ Arquitetura do Projeto

O TechScout AI é um sistema de Market Intelligence que combina **GraphRAG** (análise relacional) com **busca vetorial semântica** para responder perguntas complexas sobre o ecossistema de startups, investimentos e relações empresariais.

### Arquitetura Híbrida
- **Grafo de Conhecimento (NetworkX)**: Armazena relações estruturadas entre entidades
- **Busca Vetorial (ChromaDB)**: Indexa notícias e documentos para busca semântica
- **LLM (OpenAI GPT-4/3.5)**: Sintetiza respostas combinando informações do grafo e notícias
- **Interface Streamlit**: Dashboard interativo com visualização de grafos

---

## 📁 Estrutura de Diretórios

```
TechScout AI/
├── src/techscout/              # Módulo principal
│   ├── __init__.py            # Versão e exports
│   ├── app_streamlit.py       # App Streamlit principal (refatorado)
│   ├── graph_rag.py           # Gerenciamento do grafo de conhecimento
│   ├── vector_store.py        # Gerenciamento do ChromaDB
│   ├── triple_extractor.py    # Extração de triplas com LLM
│   ├── ingestion.py           # Pipeline de ingestão de dados
│   ├── data_sources.py        # Fontes de dados online (NewsAPI, RSS)
│   ├── logger.py              # Sistema de logging
│   └── ui/                    # Módulos de UI (decompostos)
│       ├── __init__.py
│       ├── setup.py           # Configuração inicial do Streamlit
│       ├── components.py      # Componentes de UI reutilizáveis
│       ├── visualization.py   # Visualização de grafos
│       └── business_logic.py  # Lógica de negócio (busca, processamento)
│
├── scripts/                   # Scripts utilitários
│   ├── ingest.py             # Ingestão a partir de arquivo
│   ├── ingest_online.py      # Ingestão de feeds RSS / NewsAPI
│   ├── ingest_quick.py       # Ingestão rápida (RSS)
│   └── check_setup.py        # Diagnóstico de ambiente
│
├── tests/                     # Suíte pytest (roda sem chave de API)
│   ├── conftest.py           # Fixtures e duplos de LLM
│   ├── test_graph_rag.py     # Grafo, busca e persistência
│   ├── test_graph_index.py   # Caminhos de embeddings e Chroma
│   ├── test_triple_extractor.py
│   ├── test_ingestion.py
│   ├── test_data_sources.py
│   ├── test_vector_store.py
│   └── test_settings.py
│
├── data/                      # Dados gerados (gitignored)
│   ├── samples/              # Corpus de exemplo (versionado)
│   ├── chroma_db/            # Banco vetorial ChromaDB
│   └── graph_data.json       # Grafo serializado em JSON
│
├── logs/                      # Logs da aplicação (gitignored)
│   └── techscout.log
│
├── docs/                      # Documentação
├── streamlit_app.py          # Entry point Streamlit
├── pyproject.toml            # Dependências, ruff, mypy, pytest, coverage
├── Makefile                  # make check / test / lint / run
├── Dockerfile                # Container Docker
└── docker-compose.yml        # Orquestração Docker
```

> As configurações ficam em `src/techscout/settings.py`. O pacote `config/`
> existia apenas como reexportação e foi removido.

---

## 🔧 Módulos Principais

### 1. **Core Modules** (`src/techscout/`)

#### `graph_rag.py` - Gerenciamento do Grafo
- **Classe**: `GraphRAG`
- **Responsabilidades**:
  - Gerenciar grafo NetworkX
  - Adicionar triplas (sujeito-relação-objeto)
  - Buscar fatos relacionados a uma query
  - Salvar/carregar grafo serializado
  - Calcular estatísticas do grafo

#### `vector_store.py` - Armazenamento Vetorial
- **Classe**: `VectorStore`
- **Responsabilidades**:
  - Gerenciar ChromaDB
  - Adicionar documentos com embeddings
  - Busca semântica por similaridade
  - Persistência de dados

#### `triple_extractor.py` - Extração de Triplas
- **Classe**: `TripleExtractor`
- **Responsabilidades**:
  - Extrair triplas de conhecimento usando LLM
  - Parsear respostas do LLM em formato estruturado
  - Validar triplas extraídas

#### `ingestion.py` - Pipeline de Ingestão
- **Classe**: `IngestionPipeline`
- **Responsabilidades**:
  - Orquestrar processo completo de ingestão
  - Processar documentos e extrair triplas
  - Adicionar ao grafo e vector store
  - Salvar dados processados

#### `data_sources.py` - Fontes de Dados
- **Classes**: `NewsAPIClient`, `RSSClient`, `WebScraper`
- **Responsabilidades**:
  - Buscar notícias da NewsAPI
  - Processar feeds RSS
  - Scraping básico de páginas web

#### `logger.py` - Sistema de Logging
- **Funções**: Configuração de logger com rotação
- **Responsabilidades**:
  - Logging estruturado
  - Rotação de arquivos
  - Diferentes níveis de log

---

### 2. **UI Modules** (`src/techscout/ui/`)

#### `setup.py` - Configuração Inicial
- **Função**: `setup_streamlit_environment()`
- **Responsabilidades**:
  - Suprimir warnings do Streamlit
  - Configurar paths do projeto
  - Correção SQLite para Streamlit Cloud

#### `components.py` - Componentes de UI
- **Funções**:
  - `render_sidebar()` - Barra lateral com configurações
  - `render_search_form()` - Formulário de busca
  - `render_stats()` - Estatísticas do grafo
  - `render_examples()` - Exemplos de perguntas
  - `render_context_debug()` - Debug do contexto recuperado

#### `visualization.py` - Visualização
- **Funções**:
  - `render_graph_interactive()` - Renderiza grafo PyVis
  - `display_graph()` - Exibe grafo no Streamlit

#### `business_logic.py` - Lógica de Negócio
- **Funções**:
  - `load_data()` - Carrega grafo e vector store (com cache)
  - `get_api_key()` - Obtém API key do Streamlit secrets ou .env
  - `process_query()` - Processa queries e retorna respostas sintetizadas

---

### 3. **Configuration** (`config/`)

#### `config.py` - Configurações Centralizadas
- **Classe**: `Settings`
- **Configurações**:
  - OpenAI (API key, modelo, temperatura)
  - ChromaDB (collection, persist dir)
  - GraphRAG (caminho do grafo)
  - Busca (K resultados, profundidade de expansão)
  - Logging (nível, arquivo)
  - Streamlit (título, ícone)

---

### 4. **Scripts** (`scripts/`)

#### `ingest.py` - Ingestão Completa
- Script CLI para ingestão completa de dados
- Suporta múltiplas fontes de dados

#### `ingest_online.py` - Ingestão Online
- Busca dados de fontes online (NewsAPI, RSS)
- Processa e adiciona ao sistema

#### `ingest_quick.py` - Ingestão Rápida
- Ingestão rápida via RSS feeds
- Ideal para testes e desenvolvimento

---

## 🔗 Dependências entre Módulos

### Diagrama de Dependências

```
streamlit_app.py
    ↓
app_streamlit.py
    ├──→ ui/setup.py (configuração inicial)
    ├──→ ui/components.py
    │       └──→ config.settings
    ├──→ ui/visualization.py
    │       └──→ logger
    └──→ ui/business_logic.py
            ├──→ graph_rag.py
            │       └──→ config.settings
            ├──→ vector_store.py
            │       └──→ config.settings
            └──→ logger

ingestion.py
    ├──→ graph_rag.py
    ├──→ vector_store.py
    └──→ triple_extractor.py
            └──→ config.settings

scripts/ingest_*.py
    ├──→ ingestion.py
    ├──→ data_sources.py
    │       └──→ logger
    └──→ config.settings
```

### Hierarquia de Dependências

1. **Nível Base** (sem dependências internas):
   - `config/config.py` - Configurações
   - `logger.py` - Sistema de logging

2. **Nível Core** (dependem apenas do nível base):
   - `graph_rag.py` - Usa `config`, `logger`
   - `vector_store.py` - Usa `config`, `logger`
   - `triple_extractor.py` - Usa `config`, `logger`
   - `data_sources.py` - Usa `logger`

3. **Nível Orquestração** (dependem do nível core):
   - `ingestion.py` - Usa `graph_rag`, `vector_store`, `triple_extractor`

4. **Nível UI** (dependem do nível core):
   - `ui/setup.py` - Independente
   - `ui/components.py` - Usa `config`
   - `ui/visualization.py` - Usa `logger`
   - `ui/business_logic.py` - Usa `graph_rag`, `vector_store`, `logger`

5. **Nível Aplicação** (dependem de todos os níveis):
   - `app_streamlit.py` - Usa todos os módulos UI
   - `scripts/ingest_*.py` - Usam `ingestion`, `data_sources`

---

## 🔄 Fluxo de Dados

### 1. **Ingestão**
```
Fontes de Dados (NewsAPI, RSS, Web)
    ↓
IngestionPipeline
    ↓
┌─────────────────┬─────────────────┐
│ TripleExtractor │ VectorStore     │
│ (Extrai triplas)│ (Embeddings)    │
└─────────────────┴─────────────────┘
    ↓                    ↓
GraphRAG            ChromaDB
(Grafo NetworkX)    (Busca Vetorial)
```

### 2. **Consulta**
```
Query do Usuário
    ↓
┌─────────────────┬─────────────────┐
│ VectorStore     │ GraphRAG        │
│ (Busca Semântica│ (Busca Estrutural)
└─────────────────┴─────────────────┘
    ↓                    ↓
Contexto Texto      Contexto Grafo
    ↓                    ↓
    └────────┬───────────┘
             ↓
         LLM (Sintetização)
             ↓
      Resposta Final
```

---

## 📦 Dependências Principais

### Core
- `networkx` - Grafos de conhecimento
- `langchain-openai` - Integração com OpenAI
- `langchain-community` - ChromaDB integration
- `chromadb` - Banco vetorial

### UI
- `streamlit` - Interface web
- `pyvis` - Visualização de grafos interativos

### Data Sources
- `requests` - HTTP requests
- `feedparser` - RSS feeds
- `beautifulsoup4` - Web scraping

### Utilities
- `python-dotenv` - Gerenciamento de .env
- `json` - Serialização de grafos

---

## 🎯 Pontos de Entrada

### 1. **Streamlit App**
```bash
streamlit run streamlit_app.py
```
- Entry point: `streamlit_app.py`
- App principal: `src/techscout/app_streamlit.py`

### 2. **Ingestão de Dados**
```bash
python scripts/ingest_quick.py    # Rápida (RSS)
python scripts/ingest_online.py   # Completa (NewsAPI + RSS)
python scripts/ingest.py          # Completa com opções
```

### 3. **Verificação de Setup**
```bash
python test_setup.py
```

---

## 🔍 Padrões de Código

### 1. **Estrutura de Módulos**
- Cada módulo tem responsabilidade única
- Imports com tratamento de erros
- Path setup consistente em todos os módulos

### 2. **Tratamento de Erros**
- Try/except para imports opcionais
- Logging estruturado
- Mensagens de erro claras

### 3. **Configuração**
- Centralizada em `config/config.py`
- Suporte a variáveis de ambiente e .env
- Validação de configurações essenciais

### 4. **Cache**
- `@st.cache_resource` para dados pesados
- Cache de grafo e vector store no Streamlit

---

## 📝 Documentação

### Guias Disponíveis
- `README.md` - Documentação principal
- `QUICKSTART.md` - Início rápido
- `COMO_USAR.md` - Guia de uso detalhado
- `COMO_BUSCAR_DADOS.md` - Guia de busca de dados
- `GUIA_ENV.md` - Configuração de ambiente
- `TROUBLESHOOTING.md` - Solução de problemas
- `ESTRUTURA_PROJETO.md` - Estrutura do projeto

---

## 🚀 Melhorias Recentes

### Decomposição do App Streamlit
- ✅ Módulo `ui/setup.py` - Configuração inicial
- ✅ Módulo `ui/components.py` - Componentes reutilizáveis
- ✅ Módulo `ui/visualization.py` - Visualização
- ✅ Módulo `ui/business_logic.py` - Lógica de negócio
- ✅ `app_streamlit.py` refatorado (269 → ~100 linhas)

### Benefícios
- Código mais modular e reutilizável
- Mais fácil de testar e manter
- Separação clara de responsabilidades
- Componentes reutilizáveis

---

## 🔐 Segurança

- ✅ `.env` no `.gitignore`
- ✅ `.streamlit/secrets.toml` no `.gitignore`
- ✅ Validação de API keys
- ✅ Tratamento seguro de secrets do Streamlit

---

## 📊 Estatísticas do Codebase

- **Módulos Core**: 7
- **Módulos UI**: 4
- **Scripts**: 3
- **Linhas de código**: ~2000+ (estimado)
- **Documentação**: 13 arquivos MD

---

## 🎓 Conceitos-Chave

1. **GraphRAG**: Retrieval-Augmented Generation usando grafos de conhecimento
2. **Vector Search**: Busca semântica usando embeddings
3. **Hybrid Search**: Combinação de busca estrutural (grafo) + semântica (vetores)
4. **Triple Extraction**: Extração de conhecimento estruturado (sujeito-relação-objeto)
5. **Knowledge Graph**: Grafo de conhecimento representando relações entre entidades

---

*Última atualização: Após decomposição do app_streamlit.py*

