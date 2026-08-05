"""Testes do grafo de conhecimento.

Todas as operações cobertas aqui são puramente estruturais: não exigem chave
de API nem rede. A busca semântica por embeddings é coberta apenas no caminho
de degradação (sem chave), que é o que a CI consegue exercitar.
"""

import json

import networkx as nx
import pytest

from techscout.graph_rag import GraphRAG


class TestAddTriple:
    def test_adiciona_tripla_valida(self, empty_graph: GraphRAG) -> None:
        assert empty_graph.add_triple("Ana", "fundou", "Acme") is True
        assert empty_graph.graph.number_of_edges() == 1
        assert empty_graph.graph["Ana"]["Acme"]["relation"] == "fundou"

    @pytest.mark.parametrize(
        ("sujeito", "relacao", "objeto"),
        [
            ("", "fundou", "Acme"),
            ("Ana", "", "Acme"),
            ("Ana", "fundou", ""),
            ("   ", "fundou", "Acme"),
            ("Ana", "   ", "Acme"),
        ],
    )
    def test_rejeita_componente_vazio(
        self, empty_graph: GraphRAG, sujeito: str, relacao: str, objeto: str
    ) -> None:
        assert empty_graph.add_triple(sujeito, relacao, objeto) is False
        assert empty_graph.graph.number_of_edges() == 0

    def test_relacao_mais_recente_sobrescreve(self, empty_graph: GraphRAG) -> None:
        # O grafo é simples (não-multigrafo): a segunda aresta substitui a
        # primeira em vez de coexistir. Documentar isso evita a suposição de
        # que múltiplas relações entre o mesmo par são preservadas.
        empty_graph.add_triple("Ana", "fundou", "Acme")
        empty_graph.add_triple("Ana", "vendeu", "Acme")
        assert empty_graph.graph.number_of_edges() == 1
        assert empty_graph.graph["Ana"]["Acme"]["relation"] == "vendeu"


class TestAddTriples:
    def test_conta_apenas_as_validas(self, empty_graph: GraphRAG) -> None:
        triplas = [
            {"sujeito": "Ana", "relacao": "fundou", "objeto": "Acme"},
            {"sujeito": "", "relacao": "fundou", "objeto": "Acme"},
            {"sujeito": "Bruno", "relacao": "investiu_em", "objeto": "Acme"},
        ]
        assert empty_graph.add_triples(triplas) == 2

    def test_tolera_chaves_ausentes(self, empty_graph: GraphRAG) -> None:
        assert empty_graph.add_triples([{"sujeito": "Ana"}]) == 0

    def test_lista_vazia(self, empty_graph: GraphRAG) -> None:
        assert empty_graph.add_triples([]) == 0


class TestSearch:
    def test_encontra_por_termo_parcial(self, sample_graph: GraphRAG) -> None:
        fatos = sample_graph.search("Nuvem")
        assert any("Nuvem Labs" in f for f in fatos)
        assert all(f.startswith("GRAFO:") for f in fatos)

    def test_busca_insensivel_a_caixa(self, sample_graph: GraphRAG) -> None:
        assert sample_graph.search("nuvem") == sample_graph.search("NUVEM")

    def test_ignora_termos_curtos(self, sample_graph: GraphRAG) -> None:
        # Termos com até 2 caracteres são descartados; sobrando nenhum, a
        # busca deve avisar em vez de varrer o grafo inteiro.
        fatos = sample_graph.search("de a o")
        assert fatos == ["Nenhum termo significativo encontrado na pergunta."]

    def test_query_vazia(self, sample_graph: GraphRAG) -> None:
        assert sample_graph.search("") == [
            "Nenhum termo significativo encontrado na pergunta."
        ]

    def test_sem_correspondencia(self, sample_graph: GraphRAG) -> None:
        assert sample_graph.search("Petrobras") == [
            "Nenhuma conexão encontrada no grafo para os termos pesquisados."
        ]

    def test_expansao_alcanca_vizinhos_indiretos(self, sample_graph: GraphRAG) -> None:
        # "Ana Torres" conecta a "Nuvem Labs", que conecta a "DataPonte".
        # Com profundidade 1 a partir de Ana, DataPonte deve aparecer.
        fatos = sample_graph.search("Torres", expansion_depth=1)
        assert any("DataPonte" in f for f in fatos)

    def test_profundidade_zero_restringe_ao_no_encontrado(
        self, sample_graph: GraphRAG
    ) -> None:
        fatos = sample_graph.search("Torres", expansion_depth=0)
        assert any("Ana Torres" in f for f in fatos)
        assert not any("Bruno Lima" in f for f in fatos)

    def test_nao_repete_fatos(self, sample_graph: GraphRAG) -> None:
        fatos = sample_graph.search("Nuvem", expansion_depth=2)
        assert len(fatos) == len(set(fatos))

    def test_grafo_vazio(self, empty_graph: GraphRAG) -> None:
        assert empty_graph.search("qualquer coisa") == [
            "Nenhuma conexão encontrada no grafo para os termos pesquisados."
        ]


class TestSemanticSearchFallback:
    def test_degrada_para_busca_textual_sem_chave(
        self, sample_graph: GraphRAG, no_api_key
    ) -> None:
        # Sem OPENAI_API_KEY não há índice de nós; o método deve cair na busca
        # textual em vez de falhar.
        assert sample_graph.semantic_search("Nuvem") == sample_graph.search("Nuvem")

    def test_grafo_vazio_sem_chave(self, empty_graph: GraphRAG, no_api_key) -> None:
        assert empty_graph.semantic_search("Nuvem") == [
            "Nenhuma conexão encontrada no grafo para os termos pesquisados."
        ]


class TestStats:
    def test_estatisticas(self, sample_graph: GraphRAG) -> None:
        stats = sample_graph.get_stats()
        assert stats["nodes"] == 6
        assert stats["edges"] == 4
        assert 0 < stats["density"] <= 1

    def test_densidade_zero_em_grafo_vazio(self, empty_graph: GraphRAG) -> None:
        stats = empty_graph.get_stats()
        assert stats == {"nodes": 0, "edges": 0, "density": 0}


class TestPersistence:
    def test_roundtrip_preserva_nos_arestas_e_relacoes(
        self, sample_graph: GraphRAG, tmp_path
    ) -> None:
        destino = tmp_path / "graph.json"
        assert sample_graph.save(str(destino)) is True

        carregado = GraphRAG.load(str(destino))
        assert carregado is not None
        assert carregado.get_stats() == sample_graph.get_stats()
        assert carregado.graph["Ana Torres"]["Nuvem Labs"]["relation"] == "fundou"

    def test_salva_em_json_e_nao_pickle(self, sample_graph: GraphRAG, tmp_path) -> None:
        # O formato precisa ser JSON legível: carregar grafo via pickle é
        # execução arbitrária de código a partir de um arquivo de dados.
        destino = tmp_path / "graph.json"
        sample_graph.save(str(destino))
        conteudo = json.loads(destino.read_text(encoding="utf-8"))
        assert "nodes" in conteudo
        assert "links" in conteudo

    def test_preserva_acentuacao(self, empty_graph: GraphRAG, tmp_path) -> None:
        empty_graph.add_triple("João Conceição", "fundou", "Inovação S.A.")
        destino = tmp_path / "graph.json"
        empty_graph.save(str(destino))

        carregado = GraphRAG.load(str(destino))
        assert carregado is not None
        assert "João Conceição" in carregado.graph

    def test_cria_diretorio_pai(self, sample_graph: GraphRAG, tmp_path) -> None:
        destino = tmp_path / "novo" / "sub" / "graph.json"
        assert sample_graph.save(str(destino)) is True
        assert destino.exists()

    def test_arquivo_inexistente_retorna_none(self, tmp_path) -> None:
        assert GraphRAG.load(str(tmp_path / "nao-existe.json")) is None

    def test_json_corrompido_retorna_none(self, tmp_path) -> None:
        destino = tmp_path / "corrompido.json"
        destino.write_text("{ isso não é json", encoding="utf-8")
        assert GraphRAG.load(str(destino)) is None

    def test_recusa_pickle_legado_por_padrao(self, tmp_path, monkeypatch) -> None:
        # Desserializar pickle de origem não confiável executa código. O
        # carregamento só pode ocorrer com opt-in explícito.
        import pickle

        from techscout import graph_rag as graph_rag_module

        legado = tmp_path / "graph.pkl"
        with open(legado, "wb") as handle:
            pickle.dump(nx.Graph(), handle)

        monkeypatch.setattr(
            graph_rag_module.settings, "GRAPH_DATA_LEGACY_PKL_PATH", str(legado)
        )
        monkeypatch.setattr(
            graph_rag_module.settings, "ALLOW_PICKLE_GRAPH_LOAD", False
        )

        assert GraphRAG.load(str(tmp_path / "ausente.json")) is None

    def test_carrega_pickle_legado_com_optin(self, tmp_path, monkeypatch) -> None:
        import pickle

        from techscout import graph_rag as graph_rag_module

        origem = nx.Graph()
        origem.add_edge("Ana", "Acme", relation="fundou")
        legado = tmp_path / "graph.pkl"
        with open(legado, "wb") as handle:
            pickle.dump(origem, handle)

        destino = tmp_path / "migrado.json"
        monkeypatch.setattr(
            graph_rag_module.settings, "GRAPH_DATA_LEGACY_PKL_PATH", str(legado)
        )
        monkeypatch.setattr(graph_rag_module.settings, "ALLOW_PICKLE_GRAPH_LOAD", True)

        carregado = GraphRAG.load(str(destino))
        assert carregado is not None
        assert carregado.graph.number_of_edges() == 1
        # A migração precisa gravar o JSON, para não repetir o caminho pickle.
        assert destino.exists()
