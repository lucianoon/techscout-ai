"""Configuração compartilhada dos testes.

Os diretórios de dados e logs são redirecionados para um temporário *antes* de
qualquer import de ``techscout``, porque ``techscout.settings`` resolve e cria
esses caminhos no momento da importação. Sem isso, rodar a suíte sujaria o
diretório de trabalho.
"""

import os
import tempfile
from pathlib import Path

_TMP_ROOT = Path(tempfile.mkdtemp(prefix="techscout-tests-"))
os.environ["TECHSCOUT_BASE_DIR"] = str(_TMP_ROOT)
os.environ["TECHSCOUT_DATA_DIR"] = str(_TMP_ROOT / "data")
os.environ["TECHSCOUT_LOGS_DIR"] = str(_TMP_ROOT / "logs")

import networkx as nx  # noqa: E402
import pytest  # noqa: E402

from techscout.graph_rag import GraphRAG  # noqa: E402


class FakeResponse:
    """Resposta mínima no formato que ``ChatOpenAI.invoke`` devolve."""

    def __init__(self, content: str) -> None:
        self.content = content


class FakeChatModel:
    """LLM de teste: devolve respostas roteirizadas, sem tocar a rede.

    ``responses`` é consumida em ordem; a última é repetida se houver mais
    chamadas do que respostas. Passar uma exceção faz ``invoke`` levantá-la.
    """

    def __init__(self, *responses: object) -> None:
        self.responses = list(responses) or [""]
        self.calls: list[str] = []

    def invoke(self, prompt: str) -> FakeResponse:
        self.calls.append(prompt)
        index = min(len(self.calls) - 1, len(self.responses) - 1)
        result = self.responses[index]
        if isinstance(result, Exception):
            raise result
        return FakeResponse(str(result))


@pytest.fixture
def fake_llm():
    """Fábrica de LLMs falsos."""
    return FakeChatModel


@pytest.fixture
def sample_graph() -> GraphRAG:
    """Grafo pequeno com um componente conectado e um isolado."""
    graph = GraphRAG()
    graph.add_triple("Ana Torres", "fundou", "Nuvem Labs")
    graph.add_triple("Nuvem Labs", "adquiriu", "DataPonte")
    graph.add_triple("Bruno Lima", "investiu_em", "Nuvem Labs")
    graph.add_triple("Carla Reis", "fundou", "Orbita Bio")
    return graph


@pytest.fixture
def empty_graph() -> GraphRAG:
    return GraphRAG()


@pytest.fixture
def no_api_key(monkeypatch):
    """Garante ausência de chave, independentemente do .env do desenvolvedor."""
    from techscout import settings as settings_module

    monkeypatch.setattr(settings_module.settings, "OPENAI_API_KEY", None)
    return settings_module.settings


@pytest.fixture
def disconnected_graph() -> nx.Graph:
    graph = nx.Graph()
    graph.add_node("Sozinho")
    return graph
