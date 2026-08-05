"""Testes das fontes de dados externas.

Nenhuma requisição de rede é feita: `requests` e `feedparser` são
substituídos por duplos. `time.sleep` também é neutralizado — o coletor
dorme 1s por feed para respeitar rate limit, o que tornaria a suíte lenta.
"""

import pytest

from techscout import data_sources
from techscout.data_sources import (
    NewsAPIClient,
    RSSFeedReader,
    TechNewsCollector,
    format_article_text,
)


@pytest.fixture(autouse=True)
def sem_espera(monkeypatch):
    """Remove o rate limiting das chamadas em teste."""
    monkeypatch.setattr(data_sources.time, "sleep", lambda _s: None)


class FakeResponse:
    def __init__(self, payload: dict, erro: Exception | None = None) -> None:
        self._payload = payload
        self._erro = erro

    def raise_for_status(self) -> None:
        if self._erro is not None:
            raise self._erro

    def json(self) -> dict:
        return self._payload


class TestNewsAPIClient:
    def test_sem_chave_retorna_vazio(self) -> None:
        # Ausência de chave é configuração esperada (o projeto roda só com
        # RSS), não erro: deve degradar em silêncio.
        assert NewsAPIClient().search_articles("startup") == []

    def test_busca_bem_sucedida(self, monkeypatch) -> None:
        capturado = {}

        def fake_get(url, params=None, timeout=None):
            capturado["url"] = url
            capturado["params"] = params
            return FakeResponse({"articles": [{"title": "A"}, {"title": "B"}]})

        monkeypatch.setattr(data_sources.requests, "get", fake_get)

        artigos = NewsAPIClient("chave-teste").search_articles("startup")
        assert len(artigos) == 2
        assert capturado["params"]["q"] == "startup"
        assert capturado["params"]["apiKey"] == "chave-teste"

    def test_page_size_limitado_a_cem(self, monkeypatch) -> None:
        # A NewsAPI rejeita pageSize > 100; o cliente precisa truncar.
        capturado = {}

        def fake_get(url, params=None, timeout=None):
            capturado.update(params)
            return FakeResponse({"articles": []})

        monkeypatch.setattr(data_sources.requests, "get", fake_get)
        NewsAPIClient("k").search_articles("x", page_size=500)
        assert capturado["pageSize"] == 100

    def test_erro_de_rede_retorna_vazio(self, monkeypatch) -> None:
        def fake_get(url, params=None, timeout=None):
            raise data_sources.requests.exceptions.RequestException("timeout")

        monkeypatch.setattr(data_sources.requests, "get", fake_get)
        assert NewsAPIClient("k").search_articles("startup") == []

    def test_headlines_sem_chave(self) -> None:
        assert NewsAPIClient().get_top_headlines() == []

    def test_headlines_com_chave(self, monkeypatch) -> None:
        monkeypatch.setattr(
            data_sources.requests,
            "get",
            lambda *a, **k: FakeResponse({"articles": [{"title": "T"}]}),
        )
        assert len(NewsAPIClient("k").get_top_headlines()) == 1

    def test_resposta_sem_campo_articles(self, monkeypatch) -> None:
        monkeypatch.setattr(
            data_sources.requests, "get", lambda *a, **k: FakeResponse({})
        )
        assert NewsAPIClient("k").search_articles("x") == []


class FakeFeed:
    def __init__(self, entries: list[dict]) -> None:
        self.entries = entries


class TestRSSFeedReader:
    def test_le_entradas(self, monkeypatch) -> None:
        monkeypatch.setattr(
            data_sources.feedparser,
            "parse",
            lambda url: FakeFeed(
                [{"title": "T1", "description": "D1", "link": "L1"}]
            ),
        )
        itens = RSSFeedReader().fetch_feed("http://exemplo/feed")
        assert itens[0]["title"] == "T1"
        assert itens[0]["link"] == "L1"

    def test_respeita_max_items(self, monkeypatch) -> None:
        entradas = [{"title": f"T{i}"} for i in range(50)]
        monkeypatch.setattr(
            data_sources.feedparser, "parse", lambda url: FakeFeed(entradas)
        )
        assert len(RSSFeedReader().fetch_feed("http://x", max_items=5)) == 5

    def test_content_cai_para_description(self, monkeypatch) -> None:
        monkeypatch.setattr(
            data_sources.feedparser,
            "parse",
            lambda url: FakeFeed([{"title": "T", "description": "corpo"}]),
        )
        assert RSSFeedReader().fetch_feed("http://x")[0]["content"] == "corpo"

    def test_feed_quebrado_retorna_vazio(self, monkeypatch) -> None:
        def explode(url):
            raise ValueError("feed inválido")

        monkeypatch.setattr(data_sources.feedparser, "parse", explode)
        assert RSSFeedReader().fetch_feed("http://x") == []


class TestTechNewsCollector:
    def test_sem_chave_nao_cria_cliente_newsapi(self) -> None:
        assert TechNewsCollector().newsapi is None

    def test_com_chave_cria_cliente(self) -> None:
        assert TechNewsCollector("k").newsapi is not None

    def test_coleta_rss_concatena_titulo_e_corpo(self, monkeypatch) -> None:
        coletor = TechNewsCollector()
        monkeypatch.setattr(
            coletor.rss_reader,
            "fetch_feed",
            lambda url, n: [{"title": "Título", "content": "Corpo"}],
        )
        textos = coletor.collect_from_rss()
        assert all("Título" in t and "Corpo" in t for t in textos)

    def test_feed_com_falha_nao_aborta_os_demais(self, monkeypatch) -> None:
        coletor = TechNewsCollector()
        chamadas = {"n": 0}

        def fetch(url, n):
            chamadas["n"] += 1
            if chamadas["n"] == 1:
                raise RuntimeError("feed fora do ar")
            return [{"title": f"T{chamadas['n']}", "content": "c"}]

        monkeypatch.setattr(coletor.rss_reader, "fetch_feed", fetch)
        textos = coletor.collect_from_rss()
        # Um feed falhou, os outros três produziram texto.
        assert len(textos) == 3

    def test_newsapi_sem_cliente_retorna_vazio(self) -> None:
        assert TechNewsCollector().collect_from_newsapi() == []

    def test_collect_all_remove_duplicatas_por_titulo(self, monkeypatch) -> None:
        coletor = TechNewsCollector()
        # Todos os feeds devolvem o mesmo item: deve sobrar um só.
        monkeypatch.setattr(
            coletor.rss_reader,
            "fetch_feed",
            lambda url, n: [{"title": "Mesma manchete", "content": "c"}],
        )
        assert len(coletor.collect_all(use_newsapi=False)) == 1

    def test_collect_all_respeita_max_items(self, monkeypatch) -> None:
        coletor = TechNewsCollector()
        contador = {"n": 0}

        def fetch(url, n):
            contador["n"] += 1
            return [
                {"title": f"Manchete {contador['n']}-{i}", "content": "c"}
                for i in range(10)
            ]

        monkeypatch.setattr(coletor.rss_reader, "fetch_feed", fetch)
        assert len(coletor.collect_all(use_newsapi=False, max_items=5)) == 5

    def test_collect_all_sem_fontes(self) -> None:
        assert TechNewsCollector().collect_all(use_newsapi=False, use_rss=False) == []


class TestFormatArticleText:
    def test_junta_campos_presentes(self) -> None:
        texto = format_article_text(
            {"title": "T", "description": "D", "content": "C"}
        )
        assert texto == "T\n\nD\n\nC"

    def test_ignora_campos_ausentes(self) -> None:
        assert format_article_text({"title": "Só título"}) == "Só título"

    def test_dicionario_vazio(self) -> None:
        assert format_article_text({}) == ""

    def test_remove_tags_html(self) -> None:
        texto = format_article_text(
            {"content": "<p>Parágrafo <b>forte</b></p>"}
        )
        assert "<" not in texto
        assert "Parágrafo" in texto
