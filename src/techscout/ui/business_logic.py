"""
Lógica de negócio para busca e processamento
"""
import contextlib
import os
from collections import OrderedDict

import streamlit as st
from langchain_openai import ChatOpenAI

from techscout.graph_rag import GraphRAG
from techscout.logger import logger
from techscout.settings import settings
from techscout.vector_store import VectorStore


@st.cache_resource
def load_data():
    """
    Carrega grafo e vector store com cache

    Returns:
        Tupla (graph_rag, vector_store) ou (None, None) em caso de erro
    """
    try:
        # Carrega grafo
        graph_rag = GraphRAG.load()
        if not graph_rag:
            return None, None

        # Inicializa vector store
        vector_store = VectorStore()
        if not vector_store.initialize():
            return None, None

        return graph_rag, vector_store
    except Exception as e:
        logger.error(f"Erro ao carregar dados: {e}", exc_info=True)
        if os.getenv("LOG_LEVEL", "").upper() == "DEBUG":
            st.error(f"🧨 load_data falhou: {type(e).__name__}: {e}")
        return None, None


def get_api_key():
    """
    Obtém a API key do Streamlit secrets ou configurações
    
    Returns:
        API key ou None
    """
    api_key = settings.OPENAI_API_KEY
    try:
        # Tenta acessar secrets do Streamlit
        streamlit_key = st.secrets.get("OPENAI_API_KEY", None)
        if streamlit_key:
            api_key = streamlit_key
    except Exception as e:
        # Secrets não configurado ou não disponível, usa apenas variável de ambiente/.env
        logger.debug(f"Secrets do Streamlit não disponíveis: {type(e).__name__}")
        pass
    
    return api_key


def _get_response_cache():
    if "response_cache" not in st.session_state:
        st.session_state["response_cache"] = OrderedDict()
    return st.session_state["response_cache"]


def _make_cache_key(query: str, k_results: int, modelo_nome: str | None) -> str:
    normalized = " ".join((query or "").split())
    return f"{normalized}|{k_results}|{modelo_nome or ''}"


def _truncate_text(text: str, max_chars: int) -> str:
    if not text:
        return ""
    if max_chars <= 0:
        return ""
    if len(text) <= max_chars:
        return text
    return text[:max_chars]


def process_query(
    query: str,
    graph_rag: GraphRAG,
    vector_store: VectorStore,
    llm: ChatOpenAI,
    k_results: int,
    modelo_nome: str | None = None,
):
    """
    Processa uma query e retorna a resposta sintetizada
    
    Args:
        query: Pergunta do usuário
        graph_rag: Instância do GraphRAG
        vector_store: Instância do VectorStore
        llm: Instância do LLM
        k_results: Número de resultados vetoriais
        modelo_nome: Nome do modelo LLM (opcional, tenta obter automaticamente se None)
        
    Returns:
        Tupla (resposta, contexto_grafo, contexto_texto, docs)
    """
    if not modelo_nome:
        # O atributo que carrega o nome do modelo variou entre versões do
        # LangChain; tenta os três e cai para um rótulo genérico.
        modelo_nome = (
            getattr(llm, "_model_name", None)
            or getattr(llm, "model_name", None)
            or getattr(llm, "model", None)
            or "LLM"
        )

    cache = _get_response_cache()
    cache_key = _make_cache_key(query, k_results, modelo_nome)

    if cache_key in cache:
        resposta, contexto_grafo, contexto_texto, docs = cache[cache_key]
        # Marca como usado recentemente para a política LRU.
        with contextlib.suppress(KeyError):
            cache.move_to_end(cache_key)
        return resposta, contexto_grafo, contexto_texto, docs

    with st.spinner("1. Consultando Vector Store (Semântica)..."):
        docs = vector_store.search(query, k=k_results)
        contexto_texto = (
            "\n".join([d.page_content for d in docs])
            if docs
            else "Nenhuma notícia relevante encontrada."
        )
        contexto_texto = _truncate_text(contexto_texto, 12000)
        
    with st.spinner("2. Consultando Grafo (Estrutura)..."):
        fatos_grafo = graph_rag.semantic_search(
            query,
            top_k_nodes=k_results,
            expansion_depth=settings.GRAPH_EXPANSION_DEPTH
        )
        contexto_grafo = "\n".join(fatos_grafo)
        contexto_grafo = _truncate_text(contexto_grafo, 8000)
        
    with st.spinner(f"3. Sintetizando resposta com {modelo_nome}..."):
        prompt_final = f"""
Você é um Analista de VC Sênior especializado em Market Intelligence.
Combine os contextos abaixo para responder à pergunta de forma precisa e estruturada.

[FATOS DO GRAFO DE CONHECIMENTO]
{contexto_grafo}

[NOTÍCIAS E DOCUMENTOS RECENTES]
{contexto_texto}

PERGUNTA: {query}

INSTRUÇÕES:
- Responda em markdown formatado
- Cite a fonte (Grafo ou Notícia) quando relevante
- Seja específico e baseie-se apenas nos fatos fornecidos
- Se não houver informação suficiente, indique claramente
"""
        try:
            resposta = llm.invoke(prompt_final).content
        except Exception as e:
            logger.error(f"Falha ao chamar LLM: {e}", exc_info=True)
            resposta = (
                "Não consegui gerar a resposta agora (erro na chamada ao modelo). "
                "Tente novamente com um modelo diferente ou reduza o número de resultados."
            )
    
    cache[cache_key] = (resposta, contexto_grafo, contexto_texto, docs)
    with contextlib.suppress(KeyError):
        cache.move_to_end(cache_key)

    # Descarta as entradas menos usadas até caber no limite configurado.
    max_entries = settings.RESPONSE_CACHE_MAX_ENTRIES
    while max_entries > 0 and len(cache) > max_entries:
        cache.popitem(last=False)


    return resposta, contexto_grafo, contexto_texto, docs

