"""
Componentes de UI reutilizáveis para Streamlit
"""
import streamlit as st
from langchain_openai import ChatOpenAI
from pydantic import SecretStr

from techscout.settings import settings


@st.cache_resource
def _get_llm(
    model: str, temperature: float, api_key: str, timeout: int, max_retries: int
) -> ChatOpenAI:
    return ChatOpenAI(
        model=model,
        temperature=temperature,
        api_key=SecretStr(api_key),
        timeout=timeout,
        max_retries=max_retries,
    )


def render_sidebar(api_key: str):
    """
    Renderiza a barra lateral com configurações
    
    Args:
        api_key: Chave da API OpenAI
        
    Returns:
        Tupla (modelo_selecionado, k_results, llm)
    """
    st.sidebar.header("⚙️ Configurações")
    
    models = settings.get_available_models()
    default_model = getattr(settings, "OPENAI_MODEL", None)
    default_index = models.index(default_model) if default_model in models else 0
    modelo_selecionado = st.sidebar.selectbox(
        "Modelo LLM:",
        models,
        index=default_index,
        help="Escolha o modelo OpenAI. GPT-4 é mais preciso mas mais caro."
    )
    
    k_results = st.sidebar.slider(
        "Número de resultados vetoriais:",
        min_value=1,
        max_value=10,
        value=settings.VECTOR_SEARCH_K,
        help="Quantos documentos similares buscar no vector store"
    )
    
    llm = _get_llm(
        model=modelo_selecionado,
        temperature=settings.OPENAI_TEMPERATURE,
        api_key=api_key,
        timeout=settings.OPENAI_TIMEOUT_SECONDS,
        max_retries=settings.OPENAI_MAX_RETRIES,
    )
    # O nome do modelo é devolvido junto e repassado a process_query; não é
    # enxertado no objeto do LLM.
    return modelo_selecionado, k_results, llm


def render_search_form(default_query: str = "Quem é a Ana Souza e em que ela está envolvida?"):
    """
    Renderiza o formulário de busca
    
    Args:
        default_query: Query padrão para o campo de texto
        
    Returns:
        Tupla (query, buscar_button)
    """
    st.subheader("🔍 Configuração de Busca")
    if "query_input" not in st.session_state:
        st.session_state["query_input"] = default_query

    with st.form("search_form", clear_on_submit=False):
        query = st.text_area(
            "Pergunta do Investidor:",
            height=100,
            key="query_input"
        )
        buscar = st.form_submit_button(
            "🔍 Investigar Mercado", type="primary", use_container_width=True
        )
    
    return query, buscar


def render_stats(graph_rag):
    """
    Renderiza estatísticas do grafo
    
    Args:
        graph_rag: Instância do GraphRAG
    """
    with st.expander("📊 Estatísticas do Grafo"):
        stats = graph_rag.get_stats()
        st.metric("Nós", stats['nodes'])
        st.metric("Arestas", stats['edges'])
        st.metric("Densidade", f"{stats['density']:.3f}")


def render_examples():
    """
    Renderiza exemplos de perguntas
    """
    st.info("👆 Digite uma pergunta e clique em 'Investigar Mercado' para começar a análise.")
    
    st.markdown("### 💡 Exemplos de Perguntas")
    exemplos = [
        "Quem são os principais investidores no setor de IA?",
        "Quais startups foram fundadas por ex-funcionários do Google?",
        "Quem trabalhou na empresa X e agora está em Y?",
        "Quais são as relações entre as empresas mencionadas?"
    ]
    for ex in exemplos:
        st.markdown(f"- {ex}")


def render_context_debug(contexto_grafo: str, docs):
    """
    Renderiza informações de debug sobre o contexto recuperado
    
    Args:
        contexto_grafo: Contexto recuperado do grafo
        docs: Documentos recuperados do vector store
    """
    with st.expander("🔍 Ver Contexto Recuperado"):
        st.write("**Do Grafo:**")
        st.code(contexto_grafo[:500] + "..." if len(contexto_grafo) > 500 else contexto_grafo)
        st.write("**Do Vector Store:**")
        if docs:
            trecho = docs[0].page_content
            st.text(trecho[:300] + "..." if len(trecho) > 300 else trecho)
        else:
            st.warning("Nenhum documento encontrado.")

