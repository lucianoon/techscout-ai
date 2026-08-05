"""Testes do armazenamento vetorial.

O ChromaDB real não é exercitado aqui: a CI roda sem chave de API, então o que
se cobre é o contrato de degradação — inicialização preguiçosa, validação de
entrada e o que acontece antes de o banco existir.
"""

import pytest
from langchain_core.documents import Document

from techscout.vector_store import VectorStore


class FakeEmbeddings:
    """Embeddings determinísticos, suficientes para satisfazer a interface."""

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        return [[float(len(t)), 0.0, 1.0] for t in texts]

    def embed_query(self, text: str) -> list[float]:
        return [float(len(text)), 0.0, 1.0]


class TestLazyEmbeddings:
    def test_nao_exige_chave_para_instanciar(self, no_api_key) -> None:
        assert VectorStore() is not None

    def test_erro_claro_ao_usar_sem_chave(self, no_api_key) -> None:
        with pytest.raises(ValueError, match="OPENAI_API_KEY"):
            _ = VectorStore().embeddings

    def test_embeddings_injetados_dispensam_chave(self, no_api_key) -> None:
        store = VectorStore(embeddings=FakeEmbeddings())
        assert isinstance(store.embeddings, FakeEmbeddings)


class TestSearchAntesDeInicializar:
    def test_busca_sem_banco_retorna_vazio(self, no_api_key) -> None:
        # Consultar antes de inicializar é erro de uso, mas não deve explodir
        # no meio de uma requisição da UI.
        assert VectorStore(embeddings=FakeEmbeddings()).search("qualquer") == []

    def test_db_comeca_none(self, no_api_key) -> None:
        assert VectorStore(embeddings=FakeEmbeddings()).db is None


class TestAddDocuments:
    def test_lista_vazia_e_rejeitada(self, no_api_key) -> None:
        assert VectorStore(embeddings=FakeEmbeddings()).add_documents([]) is False

    def test_documentos_sem_conteudo_sao_rejeitados(self, no_api_key) -> None:
        docs = [Document(page_content=""), Document(page_content="")]
        assert VectorStore(embeddings=FakeEmbeddings()).add_documents(docs) is False
