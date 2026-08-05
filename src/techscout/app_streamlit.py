"""Aplicação Streamlit do TechScout AI.

Toda a interface vive dentro de ``main()``. Importar este módulo não deve
desenhar nada — é o que permite ao ``streamlit_app.py`` importar a aplicação
sem `import *` e o que torna o módulo analisável por ferramentas estáticas.
"""

# O ambiente precisa ser configurado antes de importar o Streamlit, para que
# os filtros de warning já estejam ativos quando ele carregar.
from techscout.ui.setup import setup_streamlit_environment

setup_streamlit_environment()

import networkx as nx  # noqa: E402
import streamlit as st  # noqa: E402

from techscout.logger import logger  # noqa: E402
from techscout.settings import settings  # noqa: E402
from techscout.ui.business_logic import (  # noqa: E402
    get_api_key,
    load_data,
    process_query,
)
from techscout.ui.components import (  # noqa: E402
    render_context_debug,
    render_examples,
    render_search_form,
    render_sidebar,
    render_stats,
)
from techscout.ui.visualization import display_graph  # noqa: E402

_CONFIG_HINT = (
    "💡 Defina OPENAI_API_KEY no ambiente ou copie .env.example para .env"
)

# Limites de renderização do grafo: acima disso o pyvis trava o navegador.
_MAX_NODES = 60
_MAX_EDGES = 120


def _parse_graph_facts(contexto_grafo: str) -> tuple[set[str], list[tuple[str, str, str]]]:
    """Converte as linhas "GRAFO: a --[rel]--> b" em nós e arestas."""
    nodes: set[str] = set()
    edges: list[tuple[str, str, str]] = []

    for line in (contexto_grafo or "").splitlines():
        if not line.startswith("GRAFO: "):
            continue
        payload = line[len("GRAFO: ") :]
        if "--[" not in payload or "]-->" not in payload:
            continue
        left, right = payload.split("--[", 1)
        relacao, direito = right.split("]-->", 1)
        origem, destino, relacao = left.strip(), direito.strip(), relacao.strip()
        if origem and destino:
            nodes.update((origem, destino))
            edges.append((origem, destino, relacao))

    return nodes, edges


def _render_graph(contexto_grafo: str) -> None:
    nodes, edges = _parse_graph_facts(contexto_grafo)
    if not nodes:
        st.info("Sem relações do grafo para visualizar nesta consulta.")
        return

    visiveis = set(list(nodes)[:_MAX_NODES])
    subgrafo = nx.Graph()
    for origem, destino, relacao in edges[:_MAX_EDGES]:
        if origem in visiveis and destino in visiveis:
            subgrafo.add_edge(origem, destino, relation=relacao)

    with st.spinner("Renderizando grafo..."):
        display_graph(subgrafo)


def main() -> None:
    """Desenha a aplicação. Chamado pelo ``streamlit_app.py``."""
    st.set_page_config(
        page_title=settings.STREAMLIT_PAGE_TITLE,
        layout="wide",
        page_icon=settings.STREAMLIT_PAGE_ICON,
    )

    st.title(f"{settings.STREAMLIT_PAGE_ICON} {settings.STREAMLIT_PAGE_TITLE}")
    st.markdown(
        "**Arquitetura híbrida:** GraphRAG (relacional) + busca vetorial "
        "(semântica).\n\n"
        "*O sistema simula um analista lendo notícias e conectando fatos.*"
    )

    try:
        settings.validate()
    except ValueError as exc:
        st.error(f"🔑 {exc}")
        st.info(_CONFIG_HINT)
        st.stop()

    api_key = get_api_key()
    if not api_key:
        st.error("🔑 API Key da OpenAI não encontrada.")
        st.info(_CONFIG_HINT)
        st.stop()

    graph_rag, vector_store = load_data()
    if not graph_rag or not vector_store:
        st.warning(
            "⚠️ Dados não encontrados. "
            "Execute `python scripts/ingest.py` para processar os dados."
        )
        st.info("📁 Esperado em: data/graph_data.json e data/chroma_db/")
        st.stop()

    modelo_selecionado, k_results, llm = render_sidebar(api_key)
    modo_chat = st.sidebar.checkbox(
        "Modo rápido (sem recarregar a cada tecla)", value=True
    )

    col1, col2 = st.columns([1, 2])
    query: str | None = None
    buscar = False

    with col1:
        if modo_chat:
            st.session_state.setdefault(
                "last_query", "Quem é a Ana Souza e em que ela está envolvida?"
            )
            st.subheader("🔍 Configuração de Busca")
            st.write(st.session_state["last_query"])
        else:
            query, buscar = render_search_form()
        render_stats(graph_rag)

    if modo_chat:
        chat_query = st.chat_input("Pergunta do investidor:")
        if chat_query:
            st.session_state["last_query"] = chat_query
            query, buscar = chat_query, True

    if not buscar or query is None:
        with col2:
            render_examples()
        return

    try:
        resposta, contexto_grafo, _contexto_texto, docs = process_query(
            query, graph_rag, vector_store, llm, k_results, modelo_selecionado
        )
    except Exception as exc:
        logger.error(f"Erro ao processar consulta: {exc}", exc_info=True)
        st.error(f"❌ Erro ao processar consulta: {exc}")
        return

    with col2:
        st.success("✅ Análise concluída")
        st.markdown("### 📋 Resposta")
        st.markdown(resposta)

        st.divider()
        st.subheader("🕸️ Visualização da ontologia")
        if st.checkbox("Mostrar visualização do grafo", value=False):
            _render_graph(contexto_grafo)

    with col1:
        render_context_debug(contexto_grafo, docs)
