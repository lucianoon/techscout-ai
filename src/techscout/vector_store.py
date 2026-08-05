"""
Módulo Vector Store - Gerenciamento do ChromaDB
"""
import os
from pathlib import Path

import chromadb
from langchain_chroma import Chroma
from langchain_core.documents import Document
from langchain_core.embeddings import Embeddings
from langchain_openai import OpenAIEmbeddings
from pydantic import SecretStr

from techscout.logger import logger
from techscout.settings import settings

os.environ.setdefault("ANONYMIZED_TELEMETRY", "False")

class VectorStore:
    """Gerencia o armazenamento vetorial de documentos"""
    
    def __init__(self, embeddings: Embeddings | None = None):
        """
        Inicializa o VectorStore.

        Os embeddings são construídos sob demanda (ver ``self.embeddings``),
        para que instanciar esta classe não exija ``OPENAI_API_KEY``.

        Args:
            embeddings: Instância de embeddings; injetada em testes
        """
        self._embeddings = embeddings
        self._db: Chroma | None = None
        self.logger = logger

    @property
    def embeddings(self) -> Embeddings:
        """Embeddings, construídos na primeira utilização."""
        if self._embeddings is None:
            if not settings.OPENAI_API_KEY:
                raise ValueError(
                    "OPENAI_API_KEY não configurada. "
                    "Defina a variável de ambiente ou crie um arquivo .env"
                )
            self._embeddings = OpenAIEmbeddings(
                api_key=SecretStr(settings.OPENAI_API_KEY),
                timeout=settings.OPENAI_TIMEOUT_SECONDS,
                max_retries=settings.OPENAI_MAX_RETRIES,
            )
        return self._embeddings


    def initialize(self) -> bool:
        """
        Inicializa ou carrega o banco vetorial
        
        Returns:
            True se inicializado com sucesso
        """
        try:
            persist_dir = settings.CHROMA_PERSIST_DIR
            client_settings = chromadb.config.Settings(anonymized_telemetry=False)
            try:
                client = chromadb.PersistentClient(path=persist_dir, settings=client_settings)
                self._db = Chroma(
                    client=client,
                    embedding_function=self.embeddings,
                    collection_name=settings.CHROMA_COLLECTION_NAME
                )
            except KeyError as e:
                if str(e) != "'_type'":
                    raise
                fallback_dir = str(Path(persist_dir).with_name(Path(persist_dir).name + "_v2"))
                settings.CHROMA_PERSIST_DIR = fallback_dir
                client = chromadb.PersistentClient(path=fallback_dir, settings=client_settings)
                self._db = Chroma(
                    client=client,
                    embedding_function=self.embeddings,
                    collection_name=settings.CHROMA_COLLECTION_NAME
                )
            self.logger.info("Vector store inicializado com sucesso")
            return True
        except Exception as e:
            self.logger.error(f"Erro ao inicializar vector store: {e}")
            return False
    
    def add_documents(self, documents: list[Document]) -> bool:
        """
        Adiciona documentos ao banco vetorial
        
        Args:
            documents: Lista de documentos LangChain
            
        Returns:
            True se adicionado com sucesso
        """
        try:
            if not documents:
                self.logger.warning("Lista de documentos vazia")
                return False

            texts = []
            metadatas = []
            for d in documents:
                page_content = getattr(d, "page_content", None)
                if page_content:
                    texts.append(page_content)
                    metadatas.append(getattr(d, "metadata", {}) or {})

            if not texts:
                self.logger.warning("Nenhum documento com conteúdo válido")
                return False

            if self._db is None and not self.initialize():
                return False
            if self._db is None:  # pragma: no cover - initialize garante o db
                return False

            self._db.add_texts(texts=texts, metadatas=metadatas)
            
            self.logger.info(f"{len(documents)} documentos adicionados ao vector store")
            return True
        except Exception as e:
            self.logger.error(f"Erro ao adicionar documentos: {e}")
            return False
    
    def search(self, query: str, k: int | None = None) -> list[Document]:
        """
        Busca documentos similares
        
        Args:
            query: Texto da consulta
            k: Número de resultados (usa config padrão se None)
            
        Returns:
            Lista de documentos encontrados
        """
        try:
            if self._db is None:
                self.logger.error("Vector store não inicializado")
                return []
            
            k = k or settings.VECTOR_SEARCH_K
            results = self._db.similarity_search(query, k=k)
            self.logger.info(f"Encontrados {len(results)} documentos para query: {query[:50]}")
            return results
        except Exception as e:
            self.logger.error(f"Erro na busca vetorial: {e}")
            return []
    
    @property
    def db(self) -> Chroma | None:
        """Retorna a instância do ChromaDB"""
        return self._db

