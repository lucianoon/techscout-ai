"""
Configurações centralizadas do TechScout AI.
Suporta variáveis de ambiente e arquivo .env
"""
import os
from pathlib import Path

from dotenv import load_dotenv

os.environ.setdefault("ANONYMIZED_TELEMETRY", "False")

load_dotenv()

BASE_DIR = Path(os.getenv("TECHSCOUT_BASE_DIR", Path.cwd()))
DATA_DIR = Path(os.getenv("TECHSCOUT_DATA_DIR", str(BASE_DIR / "data")))
LOGS_DIR = Path(os.getenv("TECHSCOUT_LOGS_DIR", str(BASE_DIR / "logs")))

CHROMA_DB_DIR = DATA_DIR / "chroma_db"
GRAPH_NODE_CHROMA_DB_DIR = DATA_DIR / "chroma_graph_nodes"
GRAPH_DATA_PATH = DATA_DIR / "graph_data.json"
GRAPH_DATA_LEGACY_PKL_PATH = DATA_DIR / "graph_data.pkl"

DATA_DIR.mkdir(exist_ok=True)
LOGS_DIR.mkdir(exist_ok=True)


class Settings:
    OPENAI_API_KEY: str | None = os.getenv("OPENAI_API_KEY")
    OPENAI_MODEL: str = os.getenv("OPENAI_MODEL", "gpt-3.5-turbo")
    OPENAI_TEMPERATURE: float = float(os.getenv("OPENAI_TEMPERATURE", "0"))
    OPENAI_TIMEOUT_SECONDS: int = int(os.getenv("OPENAI_TIMEOUT_SECONDS", "60"))
    OPENAI_MAX_RETRIES: int = int(os.getenv("OPENAI_MAX_RETRIES", "2"))

    NEWSAPI_KEY: str | None = os.getenv("NEWSAPI_KEY")

    CHROMA_COLLECTION_NAME: str = os.getenv("CHROMA_COLLECTION_NAME", "tech_news")
    CHROMA_PERSIST_DIR: str = os.getenv("CHROMA_PERSIST_DIR", str(CHROMA_DB_DIR))

    GRAPH_NODE_COLLECTION_NAME: str = os.getenv(
        "GRAPH_NODE_COLLECTION_NAME", "graph_nodes"
    )
    GRAPH_NODE_CHROMA_PERSIST_DIR: str = os.getenv(
        "GRAPH_NODE_CHROMA_PERSIST_DIR", str(GRAPH_NODE_CHROMA_DB_DIR)
    )

    GRAPH_DATA_PATH: str = os.getenv("GRAPH_DATA_PATH", str(GRAPH_DATA_PATH))
    GRAPH_DATA_LEGACY_PKL_PATH: str = os.getenv(
        "GRAPH_DATA_LEGACY_PKL_PATH", str(GRAPH_DATA_LEGACY_PKL_PATH)
    )
    ALLOW_PICKLE_GRAPH_LOAD: bool = os.getenv("ALLOW_PICKLE_GRAPH_LOAD", "0") == "1"

    VECTOR_SEARCH_K: int = int(os.getenv("VECTOR_SEARCH_K", "3"))
    GRAPH_EXPANSION_DEPTH: int = int(os.getenv("GRAPH_EXPANSION_DEPTH", "1"))
    RESPONSE_CACHE_MAX_ENTRIES: int = int(os.getenv("RESPONSE_CACHE_MAX_ENTRIES", "128"))

    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")
    LOG_FILE: str = os.getenv("LOG_FILE", str(LOGS_DIR / "techscout.log"))

    STREAMLIT_PAGE_TITLE: str = os.getenv(
        "STREAMLIT_PAGE_TITLE", "TechScout AI: Market Intelligence"
    )
    STREAMLIT_PAGE_ICON: str = os.getenv("STREAMLIT_PAGE_ICON", "🕵️")

    @classmethod
    def validate(cls) -> bool:
        if not cls.OPENAI_API_KEY:
            raise ValueError(
                "OPENAI_API_KEY não configurada. "
                "Defina a variável de ambiente ou crie um arquivo .env"
            )
        return True

    @classmethod
    def get_available_models(cls) -> list[str]:
        return [
            "gpt-4o",
            "gpt-3.5-turbo",
            "gpt-4",
            "gpt-4-turbo-preview"
        ]


settings = Settings()
