"""Testes dos caminhos que dependem de embeddings e do ChromaDB.

O ChromaDB real não sobe na CI (exigiria chave de API e rede). O que se cobre
aqui são as duas pontas: a degradação quando não há chave, e a orquestração da
busca semântica com um índice de nós substituído por um duplo.
"""

import pytest

from techscout.graph_rag import GraphRAG
from techscout.vector_store import VectorStore


class FakeDoc:
    def __init__(self, page_content: str) -> None:
        self.page_content = page_content


class FakeCollection:
    def __init__(self, count: int) -> None:
        self._count = count

    def count(self) -> int:
        return self._count


class FakeNodeIndex:
    """Índice de nós que devolve documentos roteirizados."""

    def __init__(self, docs: list[FakeDoc], count: int | None = None) -> None:
        self._docs = docs
        self._collection = FakeCollection(count if count is not None else len(docs))
        self.consultas: list[str] = []

    def similarity_search(self, query: str, k: int = 5) -> list[FakeDoc]:
        self.consultas.append(query)
        return self._docs[:k]


class TestSemDependencias:
    def test_embeddings_none_sem_chave(self, sample_graph, no_api_key) -> None:
        assert sample_graph._get_embeddings() is None

    def test_node_index_none_sem_chave(self, sample_graph, no_api_key) -> None:
        assert sample_graph._get_node_index() is None

    def test_build_node_index_falha_sem_chave(self, sample_graph, no_api_key) -> None:
        assert sample_graph.build_node_index() is False

    def test_build_node_index_falha_em_grafo_vazio(
        self, empty_graph, monkeypatch, tmp_path
    ) -> None:
        from techscout import graph_rag as modulo

        # Com chave presente mas grafo vazio, não há o que indexar.
        monkeypatch.setattr(modulo.settings, "OPENAI_API_KEY", "sk-teste")
        monkeypatch.setattr(
            modulo.settings, "GRAPH_NODE_CHROMA_PERSIST_DIR", str(tmp_path / "nodes")
        )
        monkeypatch.setattr(
            GraphRAG, "_get_embeddings", lambda self: object()
        )
        assert empty_graph.build_node_index() is False


class TestSemanticSearchComIndice:
    def test_usa_nos_retornados_pelo_indice(self, sample_graph) -> None:
        indice = FakeNodeIndex(
            [FakeDoc("Nuvem Labs")], count=sample_graph.graph.number_of_nodes()
        )
        sample_graph._get_node_index = lambda: indice

        fatos = sample_graph.semantic_search("quem investiu na nuvem?")
        assert indice.consultas == ["quem investiu na nuvem?"]
        assert any("Nuvem Labs" in f for f in fatos)

    def test_expande_vizinhanca_a_partir_do_no_semantico(self, sample_graph) -> None:
        indice = FakeNodeIndex(
            [FakeDoc("Ana Torres")], count=sample_graph.graph.number_of_nodes()
        )
        sample_graph._get_node_index = lambda: indice

        fatos = sample_graph.semantic_search("fundadora", expansion_depth=1)
        # Ana → Nuvem Labs → DataPonte
        assert any("DataPonte" in f for f in fatos)

    def test_ignora_nos_ausentes_do_grafo(self, sample_graph) -> None:
        # O índice pode estar defasado e devolver nós já removidos; nesse caso
        # a busca cai para a textual em vez de retornar vazio.
        indice = FakeNodeIndex(
            [FakeDoc("Entidade Fantasma")],
            count=sample_graph.graph.number_of_nodes(),
        )
        sample_graph._get_node_index = lambda: indice

        assert sample_graph.semantic_search("Nuvem") == sample_graph.search("Nuvem")

    def test_indice_vazio_cai_para_busca_textual(self, sample_graph) -> None:
        indice = FakeNodeIndex([], count=sample_graph.graph.number_of_nodes())
        sample_graph._get_node_index = lambda: indice
        assert sample_graph.semantic_search("Nuvem") == sample_graph.search("Nuvem")

    def test_excecao_no_indice_cai_para_busca_textual(self, sample_graph) -> None:
        def explode():
            raise RuntimeError("chroma fora do ar")

        sample_graph._get_node_index = explode
        assert sample_graph.semantic_search("Nuvem") == sample_graph.search("Nuvem")

    def test_reindexa_quando_contagem_diverge(self, sample_graph) -> None:
        # Contagem do índice diferente do número de nós indica índice obsoleto:
        # o grafo deve tentar reconstruí-lo antes de consultar.
        indice = FakeNodeIndex([FakeDoc("Nuvem Labs")], count=999)
        sample_graph._get_node_index = lambda: indice
        reconstruido = {"n": 0}

        def rebuild(clear_existing=False):
            reconstruido["n"] += 1
            return True

        sample_graph.build_node_index = rebuild
        sample_graph.semantic_search("Nuvem")
        assert reconstruido["n"] == 1


class FakeChroma:
    def __init__(self, resultados=None, erro: Exception | None = None) -> None:
        self._resultados = resultados or []
        self._erro = erro
        self.textos_adicionados: list[str] = []

    def similarity_search(self, query: str, k: int = 3) -> list[FakeDoc]:
        if self._erro is not None:
            raise self._erro
        return self._resultados[:k]

    def add_texts(self, texts: list[str], metadatas=None) -> None:
        if self._erro is not None:
            raise self._erro
        self.textos_adicionados.extend(texts)


class TestVectorStoreComBanco:
    @pytest.fixture
    def store(self, no_api_key) -> VectorStore:
        s = VectorStore(embeddings=object())
        s._db = FakeChroma([FakeDoc("doc A"), FakeDoc("doc B")])
        return s

    def test_busca_retorna_documentos(self, store: VectorStore) -> None:
        assert len(store.search("consulta")) == 2

    def test_respeita_k(self, store: VectorStore) -> None:
        assert len(store.search("consulta", k=1)) == 1

    def test_erro_na_busca_retorna_vazio(self, no_api_key) -> None:
        store = VectorStore(embeddings=object())
        store._db = FakeChroma(erro=RuntimeError("conexão perdida"))
        assert store.search("consulta") == []

    def test_add_documents_envia_conteudo(self, store: VectorStore) -> None:
        from langchain_core.documents import Document

        assert store.add_documents([Document(page_content="texto novo")]) is True
        assert store._db.textos_adicionados == ["texto novo"]

    def test_add_documents_ignora_vazios_no_lote(self, store: VectorStore) -> None:
        from langchain_core.documents import Document

        store.add_documents(
            [Document(page_content="válido"), Document(page_content="")]
        )
        assert store._db.textos_adicionados == ["válido"]

    def test_erro_ao_adicionar_retorna_false(self, no_api_key) -> None:
        from langchain_core.documents import Document

        store = VectorStore(embeddings=object())
        store._db = FakeChroma(erro=RuntimeError("disco cheio"))
        assert store.add_documents([Document(page_content="x")]) is False

    def test_db_exposto_pela_propriedade(self, store: VectorStore) -> None:
        assert store.db is store._db
