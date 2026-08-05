"""Testes da avaliação de extração.

Nada aqui chama a API: a extração real fica cacheada em `data/eval/` e os
testes exercitam a normalização, as métricas e a leitura do cache.
"""

import json

import pytest

from techscout.extraction_eval import (
    caminho_cache,
    canonizar,
    como_par,
    comparar,
    conformidade,
    custo_na_recuperacao,
    extrair_corpus,
    gabarito_por_documento,
    grafo_extraido,
    normalizar_entidade,
    normalizar_relacao,
)
from techscout.triple_extractor import VOCABULARIO_RELACOES


class TestNormalizacaoDeEntidade:
    @pytest.mark.parametrize(
        ("entrada", "esperado"),
        [
            ("Nebula AI", "nebula ai"),
            ("a Nebula AI", "nebula ai"),
            ("A Nebula AI", "nebula ai"),
            ("da OldTech", "oldtech"),
            ("  Órbita Bio  ", "orbita bio"),
            ("Nebula AI.", "nebula ai"),
            ('"Nebula AI"', "nebula ai"),
        ],
    )
    def test_forma_canonica(self, entrada: str, esperado: str) -> None:
        assert normalizar_entidade(entrada) == esperado

    def test_remove_prefixos_encadeados(self) -> None:
        assert normalizar_entidade("a  da  Nebula") == "nebula"

    def test_colapsa_espacos_internos(self) -> None:
        assert normalizar_entidade("Nebula    AI") == "nebula ai"


class TestNormalizacaoDeRelacao:
    def test_espaco_vira_underscore(self) -> None:
        assert normalizar_relacao("ex funcionario de") == "ex_funcionario_de"

    def test_remove_acento(self) -> None:
        assert normalizar_relacao("é sócio") == "e_socio"


class TestCanonizacao:
    def test_tripla_completa(self) -> None:
        assert canonizar(
            {"sujeito": "a Nebula AI", "relacao": "Adquiriu", "objeto": "DataPonte"}
        ) == ("nebula ai", "adquiriu", "dataponte")

    def test_par_ignora_direcao(self) -> None:
        ida = canonizar({"sujeito": "Ana", "relacao": "fundou", "objeto": "Acme"})
        volta = canonizar({"sujeito": "Acme", "relacao": "fundada_por", "objeto": "Ana"})
        assert como_par(ida) == como_par(volta)


class TestComparar:
    def test_acerto_total(self) -> None:
        conjunto = {("a", "r", "b")}
        m = comparar(conjunto, conjunto, "estrito")
        assert (m.precisao, m.revocacao, m.f1) == (1.0, 1.0, 1.0)

    def test_metade_correta(self) -> None:
        m = comparar({("a", "r", "b"), ("x", "r", "y")}, {("a", "r", "b")}, "estrito")
        assert m.precisao == 0.5
        assert m.revocacao == 1.0
        assert m.f1 == pytest.approx(2 / 3)

    def test_nenhum_acerto(self) -> None:
        m = comparar({("x", "r", "y")}, {("a", "r", "b")}, "estrito")
        assert (m.precisao, m.revocacao, m.f1) == (0.0, 0.0, 0.0)

    def test_extracao_vazia(self) -> None:
        m = comparar(set(), {("a", "r", "b")}, "estrito")
        assert m.precisao == 0.0
        assert m.esperados == 1

    def test_gabarito_vazio(self) -> None:
        assert comparar({("a", "r", "b")}, set(), "estrito").revocacao == 0.0

    def test_f1_nao_divide_por_zero(self) -> None:
        assert comparar(set(), set(), "estrito").f1 == 0.0


class TestConformidade:
    def test_saida_perfeita(self) -> None:
        c = conformidade({("ana", "fundou", "acme")})
        assert c["relacao_no_vocabulario"] == 1.0
        assert c["objeto_e_entidade"] == 1.0
        assert c["relacoes_inventadas"] == 0

    def test_relacao_fora_do_vocabulario(self) -> None:
        c = conformidade({("ana", "inventou_isso", "acme")})
        assert c["relacao_no_vocabulario"] == 0.0
        assert c["relacoes_inventadas"] == 1

    def test_objeto_que_e_sintagma(self) -> None:
        c = conformidade({("ana", "liderou", "a construcao da nova plataforma")})
        assert c["objeto_e_entidade"] == 0.0

    def test_conjunto_vazio(self) -> None:
        assert conformidade(set())["n"] == 0

    def test_conta_rotulos_distintos_nao_ocorrencias(self) -> None:
        c = conformidade(
            {("a", "xpto", "b"), ("c", "xpto", "d"), ("e", "outro", "f")}
        )
        assert c["relacoes_inventadas"] == 2


class TestGabarito:
    def test_agrupa_por_documento(self) -> None:
        gabarito = gabarito_por_documento()
        assert gabarito["d01"] == [("ana souza", "fundou", "nebula ai")]

    def test_cobre_todos_os_documentos_citados(self) -> None:
        assert len(gabarito_por_documento()) == 15

    def test_gabarito_usa_apenas_o_vocabulario_fechado(self) -> None:
        # Se o gabarito usasse um rótulo fora do vocabulário, cobraria do
        # modelo algo que o prompt nunca pediu.
        for triplas in gabarito_por_documento().values():
            for _, relacao, _ in triplas:
                assert relacao in VOCABULARIO_RELACOES, relacao


class TestCacheDeExtracao:
    def test_cache_versionado_existe(self) -> None:
        assert caminho_cache("gpt-3.5-turbo").exists()

    def test_cache_cobre_o_corpus(self) -> None:
        por_documento = extrair_corpus("gpt-3.5-turbo")
        assert len(por_documento) == 15

    def test_cache_tem_formato_de_tripla(self) -> None:
        for triplas in extrair_corpus("gpt-3.5-turbo").values():
            for t in triplas:
                assert {"sujeito", "relacao", "objeto"} <= set(t)

    def test_leitura_do_cache_nao_chama_api(self, monkeypatch) -> None:
        # Instanciar o extractor sem chave levantaria ValueError; o teste
        # passar prova que o caminho de cache não o constrói.
        from techscout import extraction_eval as modulo

        def explodir(*args, **kwargs):
            raise AssertionError("o cache não deveria chamar a API")

        monkeypatch.setattr(modulo, "TripleExtractor", explodir)
        assert extrair_corpus("gpt-3.5-turbo")

    def test_modelo_sem_cache_e_reportado(self, tmp_path) -> None:
        assert not caminho_cache("modelo-inexistente-xyz").exists()


class TestGrafoExtraido:
    def test_monta_grafo_com_proveniencia(self) -> None:
        grafo = grafo_extraido(
            {"d1": [{"sujeito": "Ana", "relacao": "fundou", "objeto": "Acme"}]}
        )
        assert grafo.graph["Ana"]["Acme"]["sources"] == ["d1"]

    def test_ignora_triplas_invalidas(self) -> None:
        grafo = grafo_extraido(
            {"d1": [{"sujeito": "", "relacao": "fundou", "objeto": "Acme"}]}
        )
        assert grafo.get_stats()["edges"] == 0

    def test_grafo_do_cache_tem_arestas(self) -> None:
        grafo = grafo_extraido(extrair_corpus("gpt-3.5-turbo"))
        assert grafo.get_stats()["edges"] > 0


class TestCustoNaRecuperacao:
    def test_compara_curado_e_extraido(self) -> None:
        linhas = custo_na_recuperacao(extrair_corpus("gpt-3.5-turbo"), k=5)
        assert {linha["grafo"] for linha in linhas} == {"curado", "extraido"}

    def test_metricas_no_intervalo(self) -> None:
        for linha in custo_na_recuperacao(extrair_corpus("gpt-3.5-turbo"), k=5):
            assert 0.0 <= linha["recall"] <= 1.0
            assert 0.0 <= linha["mrr"] <= 1.0

    def test_reprodutivel(self) -> None:
        extraidas = extrair_corpus("gpt-3.5-turbo")
        assert custo_na_recuperacao(extraidas, k=5) == custo_na_recuperacao(
            extraidas, k=5
        )


class TestPromptRespeitaOVocabulario:
    def test_prompt_lista_todas_as_relacoes(self) -> None:
        from techscout.triple_extractor import TripleExtractor

        prompt = TripleExtractor()._build_prompt("texto qualquer")
        for relacao in VOCABULARIO_RELACOES:
            assert relacao in prompt, relacao

    def test_prompt_nao_convida_a_inventar(self) -> None:
        # A versão anterior pedia relações "curtas e descritivas", instrução
        # que contradizia o vocabulário fechado e rendeu 15 rótulos
        # inventados. A palavra "descritivas" ainda aparece — agora dentro de
        # uma proibição —, então o teste mira a instrução, não o termo.
        from techscout.triple_extractor import TripleExtractor

        prompt = TripleExtractor()._build_prompt("texto").lower()
        assert "relações curtas e descritivas" not in prompt
        assert "descarte" in prompt
        assert "não invente" in prompt


class TestSnapshotDoPromptAnterior:
    """O cache do prompt v1 é mantido como evidência do A/B documentado."""

    def test_snapshot_preservado(self) -> None:
        anterior = caminho_cache("gpt-3.5-turbo_promptv1")
        assert anterior.exists()
        dados = json.loads(anterior.read_text(encoding="utf-8"))
        assert len(dados["por_documento"]) == 15
