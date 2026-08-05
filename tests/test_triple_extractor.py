"""Testes da extração de triplas.

O parsing é a parte frágil do módulo: a saída de um LLM é texto livre que só
*deveria* ser JSON. Estes testes fixam o comportamento diante das formas
malformadas que aparecem na prática.
"""

import pytest

from techscout.triple_extractor import TripleExtractor

TRIPLA_VALIDA = '[{"sujeito": "Ana", "relacao": "fundou", "objeto": "Acme"}]'


@pytest.fixture
def extractor() -> TripleExtractor:
    """Extrator sem LLM: exercita apenas parsing e validação."""
    return TripleExtractor()


class TestParseResponse:
    def test_json_limpo(self, extractor: TripleExtractor) -> None:
        assert extractor._parse_response(TRIPLA_VALIDA) == [
            {"sujeito": "Ana", "relacao": "fundou", "objeto": "Acme"}
        ]

    def test_remove_cerca_de_markdown(self, extractor: TripleExtractor) -> None:
        # LLMs frequentemente embrulham JSON em ```json ... ```
        conteudo = f"```json\n{TRIPLA_VALIDA}\n```"
        assert len(extractor._parse_response(conteudo)) == 1

    def test_extrai_json_cercado_de_prosa(self, extractor: TripleExtractor) -> None:
        conteudo = f"Claro! Aqui estão as relações:\n{TRIPLA_VALIDA}\nEspero ter ajudado."
        assert len(extractor._parse_response(conteudo)) == 1

    def test_normaliza_espacos_em_branco(self, extractor: TripleExtractor) -> None:
        conteudo = '[{"sujeito": "  Ana  ", "relacao": " fundou ", "objeto": " Acme "}]'
        assert extractor._parse_response(conteudo) == [
            {"sujeito": "Ana", "relacao": "fundou", "objeto": "Acme"}
        ]

    def test_multiplas_triplas(self, extractor: TripleExtractor) -> None:
        conteudo = (
            '[{"sujeito": "Ana", "relacao": "fundou", "objeto": "Acme"},'
            ' {"sujeito": "Bruno", "relacao": "investiu_em", "objeto": "Acme"}]'
        )
        assert len(extractor._parse_response(conteudo)) == 2

    def test_array_vazio(self, extractor: TripleExtractor) -> None:
        assert extractor._parse_response("[]") == []

    @pytest.mark.parametrize(
        "conteudo",
        [
            "isso não é json",
            "",
            "   ",
            "[{quebrado}]",
            '[{"sujeito": "Ana",]',
        ],
    )
    def test_entrada_malformada_retorna_lista_vazia(
        self, extractor: TripleExtractor, conteudo: str
    ) -> None:
        # Falha de parsing não pode derrubar a ingestão de um lote inteiro.
        assert extractor._parse_response(conteudo) == []

    def test_objeto_json_em_vez_de_lista(self, extractor: TripleExtractor) -> None:
        assert extractor._parse_response('{"sujeito": "Ana"}') == []

    @pytest.mark.parametrize(
        "tripla",
        [
            '{"sujeito": "Ana", "relacao": "fundou"}',
            '{"sujeito": "Ana", "objeto": "Acme"}',
            '{"sujeito": "", "relacao": "fundou", "objeto": "Acme"}',
            '{"sujeito": "   ", "relacao": "fundou", "objeto": "Acme"}',
            '{"sujeito": null, "relacao": "fundou", "objeto": "Acme"}',
            '{"sujeito": 42, "relacao": "fundou", "objeto": "Acme"}',
        ],
    )
    def test_descarta_tripla_invalida(
        self, extractor: TripleExtractor, tripla: str
    ) -> None:
        assert extractor._parse_response(f"[{tripla}]") == []

    def test_mantem_validas_e_descarta_invalidas_no_mesmo_lote(
        self, extractor: TripleExtractor
    ) -> None:
        conteudo = (
            '[{"sujeito": "Ana", "relacao": "fundou", "objeto": "Acme"},'
            ' {"sujeito": "", "relacao": "x", "objeto": "y"},'
            ' "isso nem é objeto"]'
        )
        assert extractor._parse_response(conteudo) == [
            {"sujeito": "Ana", "relacao": "fundou", "objeto": "Acme"}
        ]


class TestExtract:
    def test_usa_llm_injetado(self, fake_llm) -> None:
        extractor = TripleExtractor(llm=fake_llm(TRIPLA_VALIDA))
        assert extractor.extract("Ana fundou a Acme em 2020.") == [
            {"sujeito": "Ana", "relacao": "fundou", "objeto": "Acme"}
        ]

    def test_texto_vai_no_prompt(self, fake_llm) -> None:
        llm = fake_llm(TRIPLA_VALIDA)
        TripleExtractor(llm=llm).extract("Ana fundou a Acme.")
        assert "Ana fundou a Acme." in llm.calls[0]

    @pytest.mark.parametrize("texto", ["", "   ", "\n\t"])
    def test_texto_vazio_nao_chama_llm(self, fake_llm, texto: str) -> None:
        llm = fake_llm(TRIPLA_VALIDA)
        assert TripleExtractor(llm=llm).extract(texto) == []
        assert llm.calls == []

    def test_erro_do_llm_nao_propaga(self, fake_llm) -> None:
        # Uma falha de API em um documento não pode abortar o lote inteiro.
        extractor = TripleExtractor(llm=fake_llm(RuntimeError("429 rate limit")))
        assert extractor.extract("Ana fundou a Acme.") == []


class TestLazyClient:
    def test_nao_exige_chave_para_instanciar(self, no_api_key) -> None:
        # Construir o extrator não pode tocar em credenciais: isso é o que
        # mantém parsing e validação testáveis offline.
        assert TripleExtractor() is not None

    def test_erro_claro_ao_usar_sem_chave(self, no_api_key) -> None:
        with pytest.raises(ValueError, match="OPENAI_API_KEY"):
            _ = TripleExtractor().llm

    def test_llm_injetado_dispensa_chave(self, fake_llm, no_api_key) -> None:
        extractor = TripleExtractor(llm=fake_llm(TRIPLA_VALIDA))
        assert extractor.llm is not None
