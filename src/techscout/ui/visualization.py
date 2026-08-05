"""
Módulo de visualização de grafos
"""
import contextlib
import os
import tempfile

import streamlit.components.v1 as components

from techscout.logger import logger


def render_graph_interactive(grafo_nx):
    """
    Renderiza grafo usando PyVis e retorna HTML
    
    Args:
        grafo_nx: Grafo NetworkX
        
    Returns:
        HTML content como string
    """
    try:
        from pyvis.network import Network
        net = Network(
            height="400px",
            width="100%",
            bgcolor="#0E1117",
            font_color="white"
        )
        net.from_nx(grafo_nx)
        net.toggle_physics(True)
        
        # Usa tempfile para compatibilidade multiplataforma
        with tempfile.NamedTemporaryFile(
            mode='w',
            suffix='.html',
            delete=False,
            encoding='utf-8'
        ) as f:
            path = f.name
        
        net.save_graph(path)
        with open(path, encoding='utf-8') as f:
            html_content = f.read()
        
        # O arquivo temporário já foi lido; falhar ao removê-lo (lock no
        # Windows) não deve impedir a renderização.
        with contextlib.suppress(OSError):
            os.unlink(path)


        return html_content
    except Exception as e:
        logger.error(f"Erro ao renderizar grafo: {e}")
        return "<p>Erro ao renderizar grafo</p>"


def display_graph(grafo_nx, height: int = 410):
    """
    Exibe o grafo na interface Streamlit
    
    Args:
        grafo_nx: Grafo NetworkX
        height: Altura do componente em pixels
    """
    html_grafo = render_graph_interactive(grafo_nx)
    components.html(html_grafo, height=height, scrolling=False)

