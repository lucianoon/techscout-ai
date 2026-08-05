"""Testes do pipeline de ingestão.

O pipeline é orquestração: extrai triplas, alimenta o grafo, persiste e
indexa. Aqui os três colaboradores são substituídos por duplos, de modo que o
que se verifica é a coordenação — inclusive o que acontece quando uma etapa
falha no meio do lote.
"""

import pytest

from techscout.graph_rag import GraphRAG
from techscout.ingestion import IngestionPipeline


class FakeTripleExtractor:
    """Devolve uma tripla por texto, derivada do próprio texto."""

    def __init__(self, resultado=None, erro: Exception | None = None) -> None:
        self._resultado = resultado
        self._erro = erro
        self.textos: list[str] = []

    def extract(self, texto: str) -> list[dict]:
        self.textos.append(texto)
        if self._erro is not None:
            raise self._erro
        if self._resultado is not None:
            return self._resultado
        return [{"sujeito": texto.strip()[:20], "relacao": "cita", "objeto": "Acme"}]


class FakeVectorStore:
    def __init__(self, sucesso: bool = True) -> None:
        self.sucesso = sucesso
        self.documentos: list = []

    def add_documents(self, documentos: list) -> bool:
        self.documentos = documentos
        return self.sucesso


@pytest.fixture
def pipeline(tmp_path, monkeypatch) -> IngestionPipeline:
    """Pipeline com colaboradores falsos e persistência isolada."""
    from techscout import graph_rag as graph_rag_module

    monkeypatch.setattr(
        graph_rag_module.settings, "GRAPH_DATA_PATH", str(tmp_path / "graph.json")
    )

    p = IngestionPipeline()
    p.triple_extractor = FakeTripleExtractor()
    p.vector_store = FakeVectorStore()
    p.graph_rag = GraphRAG()
    # Índice vetorial de nós exige chave de API; irrelevante para orquestração.
    p.graph_rag.build_node_index = lambda clear_existing=False: False
    p._clear_existing_data = lambda: None
    return p


class TestProcess:
    def test_lote_valido(self, pipeline: IngestionPipeline) -> None:
        assert pipeline.process(["Ana fundou a Acme.", "Bruno investiu."]) is True
        assert pipeline.graph_rag.get_stats()["edges"] == 2
        assert len(pipeline.vector_store.documentos) == 2

    def test_lista_vazia(self, pipeline: IngestionPipeline) -> None:
        # Sem documentos, o vector store rejeita e o pipeline reporta falha.
        pipeline.vector_store = FakeVectorStore(sucesso=False)
        assert pipeline.process([]) is False

    @pytest.mark.parametrize("vazio", ["", "   ", "\n\t"])
    def test_pula_textos_vazios(self, pipeline: IngestionPipeline, vazio: str) -> None:
        pipeline.process(["Ana fundou a Acme.", vazio])
        # O texto em branco não chega ao extrator nem vira documento.
        assert len(pipeline.triple_extractor.textos) == 1
        assert len(pipeline.vector_store.documentos) == 1

    def test_texto_vira_documento_integral(self, pipeline: IngestionPipeline) -> None:
        pipeline.process(["Conteúdo íntegro com acentuação."])
        assert (
            pipeline.vector_store.documentos[0].page_content
            == "Conteúdo íntegro com acentuação."
        )

    def test_falha_do_vector_store_propaga(self, pipeline: IngestionPipeline) -> None:
        pipeline.vector_store = FakeVectorStore(sucesso=False)
        assert pipeline.process(["Ana fundou a Acme."]) is False

    def test_erro_do_extrator_nao_derruba_o_processo(
        self, pipeline: IngestionPipeline
    ) -> None:
        # A exceção é capturada pelo try/except do process e vira retorno False,
        # em vez de propagar para quem chamou o script de ingestão.
        pipeline.triple_extractor = FakeTripleExtractor(erro=RuntimeError("429"))
        assert pipeline.process(["Ana fundou a Acme."]) is False

    def test_triplas_invalidas_sao_descartadas(
        self, pipeline: IngestionPipeline
    ) -> None:
        pipeline.triple_extractor = FakeTripleExtractor(
            resultado=[{"sujeito": "", "relacao": "x", "objeto": "y"}]
        )
        assert pipeline.process(["texto"]) is True
        assert pipeline.graph_rag.get_stats()["edges"] == 0

    def test_falha_ao_salvar_grafo_aborta(
        self, pipeline: IngestionPipeline
    ) -> None:
        pipeline.graph_rag.save = lambda path=None: False
        assert pipeline.process(["Ana fundou a Acme."]) is False

    def test_grafo_persistido_em_disco(
        self, pipeline: IngestionPipeline, tmp_path
    ) -> None:
        pipeline.process(["Ana fundou a Acme."])
        assert (tmp_path / "graph.json").exists()

    def test_falha_no_indice_de_nos_nao_aborta(
        self, pipeline: IngestionPipeline
    ) -> None:
        # O índice vetorial de nós é otimização: sua falha não pode invalidar
        # uma ingestão que já gravou grafo e documentos.
        def explode(clear_existing=False):
            raise RuntimeError("chroma indisponível")

        pipeline.graph_rag.build_node_index = explode
        assert pipeline.process(["Ana fundou a Acme."]) is True


class TestClearExistingData:
    def test_remove_grafo_anterior(self, tmp_path, monkeypatch) -> None:
        from techscout import ingestion as ingestion_module

        grafo = tmp_path / "graph.json"
        grafo.write_text("{}", encoding="utf-8")
        chroma = tmp_path / "chroma"
        chroma.mkdir()

        monkeypatch.setattr(
            ingestion_module.settings, "GRAPH_DATA_PATH", str(grafo)
        )
        monkeypatch.setattr(
            ingestion_module.settings, "CHROMA_PERSIST_DIR", str(chroma)
        )
        monkeypatch.setattr(
            ingestion_module.settings,
            "GRAPH_NODE_CHROMA_PERSIST_DIR",
            str(tmp_path / "nodes"),
        )
        monkeypatch.setattr(
            ingestion_module.settings,
            "GRAPH_DATA_LEGACY_PKL_PATH",
            str(tmp_path / "graph.pkl"),
        )

        IngestionPipeline()._clear_existing_data()
        assert not grafo.exists()
        assert not chroma.exists()

    def test_tolera_ausencia_dos_caminhos(self, tmp_path, monkeypatch) -> None:
        from techscout import ingestion as ingestion_module

        for atributo in (
            "GRAPH_DATA_PATH",
            "CHROMA_PERSIST_DIR",
            "GRAPH_NODE_CHROMA_PERSIST_DIR",
            "GRAPH_DATA_LEGACY_PKL_PATH",
        ):
            monkeypatch.setattr(
                ingestion_module.settings, atributo, str(tmp_path / "ausente")
            )

        # Primeira execução, nada a limpar: não deve levantar.
        IngestionPipeline()._clear_existing_data()
