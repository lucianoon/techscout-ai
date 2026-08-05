"""Testes da avaliação de recuperação.

Duas frentes: a aritmética das métricas, que precisa estar certa para que
qualquer número publicado signifique algo, e a integridade do dataset — um
rótulo apontando para documento inexistente inflaria as métricas em silêncio.
"""

import pytest

from techscout.evaluation import (
    BM25Retriever,
    Documento,
    GraphRetriever,
    HybridRetriever,
    avaliar,
    carregar_casos,
    carregar_corpus,
    carregar_grafo,
    executar,
    normalizar,
    recall_at_k,
    reciprocal_rank,
    tokenizar,
)
from techscout.graph_rag import GraphRAG


class TestRecallAtK:
    def test_todos_relevantes_no_topo(self) -> None:
        assert recall_at_k(["a", "b", "c"], {"a", "b"}, 3) == 1.0

    def test_metade_recuperada(self) -> None:
        assert recall_at_k(["a", "x"], {"a", "b"}, 2) == 0.5

    def test_nenhum_relevante(self) -> None:
        assert recall_at_k(["x", "y"], {"a"}, 2) == 0.0

    def test_corte_em_k_e_respeitado(self) -> None:
        # O relevante está na 3ª posição; com k=2 não conta.
        assert recall_at_k(["x", "y", "a"], {"a"}, 2) == 0.0
        assert recall_at_k(["x", "y", "a"], {"a"}, 3) == 1.0

    def test_sem_relevantes_definidos(self) -> None:
        assert recall_at_k(["a"], set(), 5) == 0.0

    def test_lista_vazia(self) -> None:
        assert recall_at_k([], {"a"}, 5) == 0.0

    def test_denominador_e_o_total_de_relevantes(self) -> None:
        # Responder um de três relevantes vale um terço, não ponto cheio.
        assert recall_at_k(["a"], {"a", "b", "c"}, 5) == pytest.approx(1 / 3)


class TestReciprocalRank:
    @pytest.mark.parametrize(
        ("ranking", "esperado"),
        [
            (["a", "x", "y"], 1.0),
            (["x", "a", "y"], 0.5),
            (["x", "y", "a"], pytest.approx(1 / 3)),
            (["x", "y", "z"], 0.0),
            ([], 0.0),
        ],
    )
    def test_posicao_do_primeiro_relevante(self, ranking, esperado) -> None:
        assert reciprocal_rank(ranking, {"a"}) == esperado

    def test_considera_apenas_o_primeiro(self) -> None:
        # Dois relevantes; vale a posição do primeiro.
        assert reciprocal_rank(["x", "a", "b"], {"a", "b"}) == 0.5


class TestTokenizacao:
    def test_remove_acentos(self) -> None:
        assert normalizar("Órbita Investimentós") == "orbita investimentos"

    def test_descarta_tokens_curtos(self) -> None:
        assert "de" not in tokenizar("de investimento")

    def test_descarta_stopwords(self) -> None:
        assert tokenizar("qual fundo") == ["fundo"]

    def test_acento_nao_impede_casamento(self) -> None:
        assert tokenizar("Órbita") == tokenizar("orbita")


@pytest.fixture
def corpus_min() -> list[Documento]:
    return [
        Documento("d1", "Nebula AI", "A Nebula AI otimiza modelos de linguagem."),
        Documento("d2", "DataPonte", "Rafael Duarte fundou a DataPonte."),
        Documento("d3", "Irrelevante", "Previsao do tempo para o fim de semana."),
    ]


class TestBM25:
    def test_prioriza_documento_com_o_termo(self, corpus_min) -> None:
        assert BM25Retriever(corpus_min).retrieve("DataPonte", 3)[0] == "d2"

    def test_ignora_documentos_sem_nenhum_termo(self, corpus_min) -> None:
        # d3 não compartilha termo com a consulta e não deve aparecer.
        assert "d3" not in BM25Retriever(corpus_min).retrieve("Nebula", 3)

    def test_consulta_sem_termos_uteis(self, corpus_min) -> None:
        assert BM25Retriever(corpus_min).retrieve("de a", 3) == []

    def test_respeita_k(self, corpus_min) -> None:
        assert len(BM25Retriever(corpus_min).retrieve("a fundou modelos", 1)) <= 1

    def test_ranking_deterministico(self, corpus_min) -> None:
        r = BM25Retriever(corpus_min)
        assert r.retrieve("Nebula DataPonte", 3) == r.retrieve("Nebula DataPonte", 3)


class TestGraphRetriever:
    @pytest.fixture
    def grafo(self) -> GraphRAG:
        g = GraphRAG()
        g.add_triple("Ana", "fundou", "Nebula", fonte="d1")
        g.add_triple("Nebula", "adquiriu", "DataPonte", fonte="d2")
        g.add_triple("Rafael", "fundou", "DataPonte", fonte="d3")
        g.add_triple("Zeta", "fundou", "Omega", fonte="d4")
        return g

    def test_aresta_ponte_vence_aresta_periferica(self, grafo: GraphRAG) -> None:
        # A pergunta cita Nebula e DataPonte: a aresta entre as duas (d2) tem
        # as duas pontas ancoradas e deve liderar.
        assert grafo.retrieve_documents("Nebula DataPonte", k=3)[0] == "d2"

    def test_componente_desconectado_nao_aparece(self, grafo: GraphRAG) -> None:
        assert "d4" not in grafo.retrieve_documents("Nebula DataPonte", k=5)

    def test_sem_no_correspondente_retorna_vazio(self, grafo: GraphRAG) -> None:
        assert grafo.retrieve_documents("Petrobras", k=5) == []

    def test_consulta_sem_termos_uteis(self, grafo: GraphRAG) -> None:
        assert grafo.retrieve_documents("de a o", k=5) == []

    def test_respeita_k(self, grafo: GraphRAG) -> None:
        assert len(grafo.retrieve_documents("Nebula", k=1)) == 1

    def test_wrapper_delega(self, grafo: GraphRAG) -> None:
        direto = grafo.retrieve_documents("Nebula DataPonte", k=3)
        assert GraphRetriever(grafo).retrieve("Nebula DataPonte", 3) == direto


class TestProveniencia:
    def test_fontes_acumulam_na_mesma_aresta(self) -> None:
        # Dois artigos afirmando o mesmo fato: ambos devem ficar registrados.
        g = GraphRAG()
        g.add_triple("Ana", "fundou", "Acme", fonte="d1")
        g.add_triple("Ana", "fundou", "Acme", fonte="d2")
        assert g.graph["Ana"]["Acme"]["sources"] == ["d1", "d2"]

    def test_fonte_nao_duplica(self) -> None:
        g = GraphRAG()
        g.add_triple("Ana", "fundou", "Acme", fonte="d1")
        g.add_triple("Ana", "fundou", "Acme", fonte="d1")
        assert g.graph["Ana"]["Acme"]["sources"] == ["d1"]

    def test_tripla_sem_fonte(self) -> None:
        g = GraphRAG()
        g.add_triple("Ana", "fundou", "Acme")
        assert g.graph["Ana"]["Acme"]["sources"] == []

    def test_proveniencia_sobrevive_ao_roundtrip(self, tmp_path) -> None:
        g = GraphRAG()
        g.add_triple("Ana", "fundou", "Acme", fonte="d1")
        destino = tmp_path / "g.json"
        g.save(str(destino))

        carregado = GraphRAG.load(str(destino))
        assert carregado is not None
        assert carregado.graph["Ana"]["Acme"]["sources"] == ["d1"]


class TestHybrid:
    def test_funde_as_duas_listas(self, corpus_min) -> None:
        g = GraphRAG()
        g.add_triple("Nebula", "adquiriu", "DataPonte", fonte="d2")
        hibrido = HybridRetriever(GraphRetriever(g), BM25Retriever(corpus_min))
        assert "d2" in hibrido.retrieve("Nebula DataPonte", 3)

    def test_documento_exclusivo_de_um_lado_sobrevive(self, corpus_min) -> None:
        # d1 só existe no corpus lexical; a fusão não pode descartá-lo.
        g = GraphRAG()
        g.add_triple("Nebula", "adquiriu", "DataPonte", fonte="d2")
        hibrido = HybridRetriever(GraphRetriever(g), BM25Retriever(corpus_min))
        assert "d1" in hibrido.retrieve("Nebula linguagem", 3)


class TestIntegridadeDoDataset:
    """Sem isso, um rótulo quebrado inflaria as métricas sem alarme."""

    def test_corpus_com_ids_unicos(self) -> None:
        ids = [d.id for d in carregar_corpus()]
        assert len(ids) == len(set(ids))

    def test_toda_fonte_de_tripla_existe_no_corpus(self) -> None:
        conhecidos = {d.id for d in carregar_corpus()}
        grafo = carregar_grafo()
        for _, _, dados in grafo.graph.edges(data=True):
            for fonte in dados.get("sources", []):
                assert fonte in conhecidos, f"fonte desconhecida: {fonte}"

    def test_todo_documento_relevante_existe_no_corpus(self) -> None:
        conhecidos = {d.id for d in carregar_corpus()}
        for caso in carregar_casos():
            desconhecidos = set(caso.documentos_relevantes) - conhecidos
            assert not desconhecidos, f"{caso.id} aponta para {desconhecidos}"

    def test_casos_tem_id_unico(self) -> None:
        ids = [c.id for c in carregar_casos()]
        assert len(ids) == len(set(ids))

    def test_perguntas_relacionais_exigem_multiplos_documentos(self) -> None:
        # É o que distingue o grupo relacional do factual; se um caso
        # relacional couber em um só documento, o dataset perde o sentido.
        for caso in carregar_casos():
            if caso.tipo.startswith("relacional"):
                assert len(caso.documentos_relevantes) >= 2, caso.id

    def test_casos_factuais_sao_de_documento_unico(self) -> None:
        for caso in carregar_casos():
            if caso.tipo == "factual":
                assert len(caso.documentos_relevantes) == 1, caso.id

    def test_todo_documento_do_corpus_e_citado_por_alguma_tripla(self) -> None:
        # Documento sem tripla é invisível para o grafo: ou vira ruído
        # deliberado, ou é um esquecimento na curadoria.
        citados = set()
        for _, _, dados in carregar_grafo().graph.edges(data=True):
            citados.update(dados.get("sources", []))
        assert {d.id for d in carregar_corpus()} == citados


class TestExecucao:
    def test_metricas_entre_zero_e_um(self) -> None:
        for resultado in executar(k=5):
            assert 0.0 <= resultado.recall_at_k <= 1.0
            assert 0.0 <= resultado.mrr <= 1.0

    def test_cobre_os_tres_recuperadores(self) -> None:
        nomes = {r.retriever for r in executar(k=5)}
        assert nomes == {"bm25", "grafo", "hibrido"}

    def test_reprodutivel(self) -> None:
        primeira = [(r.retriever, r.tipo, r.recall_at_k) for r in executar(k=5)]
        segunda = [(r.retriever, r.tipo, r.recall_at_k) for r in executar(k=5)]
        assert primeira == segunda

    def test_grupo_vazio(self) -> None:
        corpus = carregar_corpus()
        assert avaliar(BM25Retriever(corpus), [], k=5).n_casos == 0
