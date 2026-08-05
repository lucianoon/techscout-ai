"""Testes de configuração."""

import pytest

from techscout.settings import Settings, settings


class TestValidate:
    def test_falha_sem_chave(self, monkeypatch) -> None:
        monkeypatch.setattr(Settings, "OPENAI_API_KEY", None)
        with pytest.raises(ValueError, match="OPENAI_API_KEY"):
            Settings.validate()

    def test_passa_com_chave(self, monkeypatch) -> None:
        monkeypatch.setattr(Settings, "OPENAI_API_KEY", "sk-teste")
        assert Settings.validate() is True


class TestDefaults:
    def test_modelos_disponiveis_nao_vazio(self) -> None:
        modelos = Settings.get_available_models()
        assert modelos
        assert settings.OPENAI_MODEL in modelos

    def test_temperatura_zero_por_padrao(self) -> None:
        # Extração de triplas precisa ser reprodutível.
        assert settings.OPENAI_TEMPERATURE == 0

    def test_pickle_desabilitado_por_padrao(self) -> None:
        assert settings.ALLOW_PICKLE_GRAPH_LOAD is False

    def test_diretorios_isolados_nos_testes(self) -> None:
        # Confirma que o conftest redirecionou os caminhos: se falhar, a suíte
        # está escrevendo no diretório de trabalho do desenvolvedor.
        assert "techscout-tests-" in settings.CHROMA_PERSIST_DIR
