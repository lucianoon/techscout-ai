"""
Módulo GraphRAG - Gerenciamento do grafo de conhecimento
"""
import contextlib
import json
import shutil
from pathlib import Path
from typing import Optional

import chromadb
import networkx as nx
from langchain_chroma import Chroma
from langchain_openai import OpenAIEmbeddings
from networkx.readwrite import json_graph
from pydantic import SecretStr

from techscout.logger import logger
from techscout.settings import settings


class GraphRAG:
    """Gerencia o grafo de conhecimento e operações relacionadas"""
    
    def __init__(self, graph: nx.Graph | None = None):
        """
        Inicializa o GraphRAG
        
        Args:
            graph: Grafo NetworkX existente ou None para criar novo
        """
        self.graph = graph if graph is not None else nx.Graph()
        self.logger = logger
        self._embeddings: OpenAIEmbeddings | None = None
        self._node_index: Chroma | None = None

    def _get_embeddings(self) -> OpenAIEmbeddings | None:
        """Embeddings dos nós, ou None quando não há chave configurada.

        Retornar None é o sinal usado pelo restante da classe para degradar
        para a busca textual em vez de falhar.
        """
        if not settings.OPENAI_API_KEY:
            return None
        if self._embeddings is None:
            self._embeddings = OpenAIEmbeddings(
                api_key=SecretStr(settings.OPENAI_API_KEY),
                timeout=settings.OPENAI_TIMEOUT_SECONDS,
                max_retries=settings.OPENAI_MAX_RETRIES,
            )
        return self._embeddings

    def _get_node_index(self) -> Chroma | None:
        embeddings = self._get_embeddings()
        if embeddings is None:
            return None
        if self._node_index is None:
            persist_dir = settings.GRAPH_NODE_CHROMA_PERSIST_DIR
            client_settings = chromadb.config.Settings(anonymized_telemetry=False)
            try:
                client = chromadb.PersistentClient(path=persist_dir, settings=client_settings)
                self._node_index = Chroma(
                    client=client,
                    embedding_function=embeddings,
                    collection_name=settings.GRAPH_NODE_COLLECTION_NAME
                )
            except KeyError as e:
                if str(e) != "'_type'":
                    raise
                fallback_dir = str(Path(persist_dir).with_name(Path(persist_dir).name + "_v2"))
                settings.GRAPH_NODE_CHROMA_PERSIST_DIR = fallback_dir
                client = chromadb.PersistentClient(path=fallback_dir, settings=client_settings)
                self._node_index = Chroma(
                    client=client,
                    embedding_function=embeddings,
                    collection_name=settings.GRAPH_NODE_COLLECTION_NAME
                )
        return self._node_index

    def build_node_index(self, clear_existing: bool = False) -> bool:
        try:
            embeddings = self._get_embeddings()
            if embeddings is None:
                return False

            persist_dir = Path(settings.GRAPH_NODE_CHROMA_PERSIST_DIR)
            persist_dir.mkdir(parents=True, exist_ok=True)
            if clear_existing and persist_dir.exists():
                # Diretório em uso por outro processo: seguir com o índice
                # existente é melhor que abortar a ingestão inteira.
                with contextlib.suppress(OSError):
                    shutil.rmtree(persist_dir)
                persist_dir.mkdir(parents=True, exist_ok=True)

            node_texts = [str(n) for n in self.graph.nodes]
            if not node_texts:
                return False

            client_settings = chromadb.config.Settings(anonymized_telemetry=False)
            client = chromadb.PersistentClient(
                path=settings.GRAPH_NODE_CHROMA_PERSIST_DIR,
                settings=client_settings,
            )
            node_index = Chroma(
                client=client,
                embedding_function=embeddings,
                collection_name=settings.GRAPH_NODE_COLLECTION_NAME,
            )
            node_index.add_texts(texts=node_texts)
            self._node_index = node_index
            return True
        except Exception as e:
            self.logger.error(f"Erro ao construir índice vetorial de nós: {e}")
            return False
    
    def add_triple(self, sujeito: str, relacao: str, objeto: str) -> bool:
        """
        Adiciona uma tripla ao grafo
        
        Args:
            sujeito: Entidade origem
            relacao: Tipo de relação
            objeto: Entidade destino
            
        Returns:
            True se adicionado com sucesso
        """
        try:
            if not all([sujeito.strip(), relacao.strip(), objeto.strip()]):
                self.logger.warning(
                    f"Tripla com valores vazios ignorada: "
                    f"{sujeito} - {relacao} - {objeto}"
                )
                return False
            
            self.graph.add_edge(sujeito, objeto, relation=relacao)
            self.logger.debug(f"Tripla adicionada: {sujeito} --[{relacao}]--> {objeto}")
            return True
        except Exception as e:
            self.logger.error(f"Erro ao adicionar tripla: {e}")
            return False
    
    def add_triples(self, triples: list[dict[str, str]]) -> int:
        """
        Adiciona múltiplas triplas ao grafo
        
        Args:
            triples: Lista de dicionários com chaves 'sujeito', 'relacao', 'objeto'
            
        Returns:
            Número de triplas adicionadas com sucesso
        """
        count = 0
        for triple in triples:
            if self.add_triple(
                triple.get('sujeito', ''),
                triple.get('relacao', ''),
                triple.get('objeto', '')
            ):
                count += 1
        return count
    
    def search(self, query: str, expansion_depth: int = 1) -> list[str]:
        """
        Busca no grafo por entidades mencionadas na query
        
        Args:
            query: Texto da consulta
            expansion_depth: Profundidade de expansão (graus de separação)
            
        Returns:
            Lista de fatos encontrados no formato "GRAFO: sujeito --[relacao]--> objeto"
        """
        fatos = []
        termos = [t.lower() for t in query.split() if len(t) > 2]
        
        if not termos:
            self.logger.warning("Nenhum termo significativo na query")
            return ["Nenhum termo significativo encontrado na pergunta."]
        
        nós_encontrados = set()
        
        # Busca direta
        for node in self.graph.nodes:
            node_lower = node.lower()
            if any(termo in node_lower for termo in termos):
                nós_encontrados.add(node)
        
        # Expansão
        nós_expandidos = set(nós_encontrados)
        for _ in range(expansion_depth):
            novos_nós = set()
            for node in nós_expandidos:
                novos_nós.update(self.graph.neighbors(node))
            nós_expandidos.update(novos_nós)
        
        # Coleta relações
        visto = set()
        for node in nós_expandidos:
            for vizinho, dados in self.graph[node].items():
                relacao = dados.get('relation', 'conectado_a')
                fato = f"GRAFO: {node} --[{relacao}]--> {vizinho}"
                if fato not in visto:
                    fatos.append(fato)
                    visto.add(fato)
        
        if not fatos:
            return ["Nenhuma conexão encontrada no grafo para os termos pesquisados."]
        
        self.logger.info(
            f"Encontradas {len(fatos)} relações no grafo para query: {query[:50]}"
        )
        return fatos

    def semantic_search(
        self, query: str, top_k_nodes: int = 5, expansion_depth: int = 1
    ) -> list[str]:
        """
        Busca semântica no grafo usando embeddings dos nós
        """
        try:
            node_index = self._get_node_index()
            if node_index is None:
                return self.search(query, expansion_depth=expansion_depth)
            if self.graph.number_of_nodes() == 0:
                return ["Nenhuma conexão encontrada no grafo para os termos pesquisados."]

            try:
                current_count = node_index._collection.count()
            except Exception:
                current_count = None
            if current_count is None or current_count != self.graph.number_of_nodes():
                self.build_node_index(clear_existing=True)
                node_index = self._get_node_index()
                if node_index is None:
                    return self.search(query, expansion_depth=expansion_depth)

            docs = node_index.similarity_search(query, k=max(1, top_k_nodes))
            top_nodes = []
            for d in docs:
                node = (d.page_content or "").strip()
                if node and node in self.graph:
                    top_nodes.append(node)
            if not top_nodes:
                return self.search(query, expansion_depth=expansion_depth)

            fatos = []
            vistos = set()
            nos_expandidos = set(top_nodes)
            for _ in range(expansion_depth):
                novos_nos = set()
                for node in nos_expandidos:
                    novos_nos.update(self.graph.neighbors(node))
                nos_expandidos.update(novos_nos)

            for node in nos_expandidos:
                for vizinho, dados in self.graph[node].items():
                    relacao = dados.get('relation', 'conectado_a')
                    fato = f"GRAFO: {node} --[{relacao}]--> {vizinho}"
                    if fato not in vistos:
                        fatos.append(fato)
                        vistos.add(fato)

            if not fatos:
                return ["Nenhuma conexão encontrada no grafo para os termos pesquisados."]

            self.logger.info(
                f"Busca semântica retornou {len(fatos)} relações "
                f"para query: {query[:50]}"
            )
            return fatos
        except Exception as e:
            self.logger.error(f"Erro na busca semântica do grafo: {e}")
            return self.search(query, expansion_depth=expansion_depth)
    
    def get_stats(self) -> dict:
        """Retorna estatísticas do grafo"""
        return {
            "nodes": self.graph.number_of_nodes(),
            "edges": self.graph.number_of_edges(),
            "density": nx.density(self.graph) if self.graph.number_of_nodes() > 0 else 0
        }
    
    def save(self, path: str | None = None) -> bool:
        """
        Salva o grafo em disco
        
        Args:
            path: Caminho do arquivo (usa config padrão se None)
            
        Returns:
            True se salvo com sucesso
        """
        try:
            save_path = Path(path or settings.GRAPH_DATA_PATH)
            save_path.parent.mkdir(parents=True, exist_ok=True)

            data = json_graph.node_link_data(self.graph, edges="links")
            with open(save_path, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False)
            
            stats = self.get_stats()
            self.logger.info(
                f"Grafo salvo: {stats['nodes']} nós, {stats['edges']} arestas"
            )
            return True
        except Exception as e:
            self.logger.error(f"Erro ao salvar grafo: {e}")
            return False
    
    @classmethod
    def load(cls, path: str | None = None) -> Optional['GraphRAG']:
        """
        Carrega grafo do disco
        
        Args:
            path: Caminho do arquivo (usa config padrão se None)
            
        Returns:
            Instância de GraphRAG ou None se erro
        """
        try:
            load_path = Path(path or settings.GRAPH_DATA_PATH)

            if load_path.exists():
                with open(load_path, encoding="utf-8") as f:
                    data = json.load(f)
                graph = json_graph.node_link_graph(
                    data, directed=False, multigraph=False, edges="links"
                )
            else:
                legacy_pkl_path = Path(
                    getattr(settings, "GRAPH_DATA_LEGACY_PKL_PATH", "")
                )
                if legacy_pkl_path and legacy_pkl_path.exists():
                    if not getattr(settings, "ALLOW_PICKLE_GRAPH_LOAD", False):
                        logger.warning(
                            f"Arquivo legado encontrado (pickle): {legacy_pkl_path}"
                        )
                        logger.warning(
                            "Carregar pickle executa código do arquivo. Para "
                            "prosseguir, defina ALLOW_PICKLE_GRAPH_LOAD=1 ou "
                            "reexecute a ingestão."
                        )
                        return None
                    import pickle
                    with open(legacy_pkl_path, "rb") as f:
                        graph = pickle.load(f)
                    instance = cls(graph)
                    instance.save(str(load_path))
                    graph = instance.graph
                else:
                    logger.warning(f"Arquivo de grafo não encontrado: {load_path}")
                    return None
            
            instance = cls(graph)
            stats = instance.get_stats()
            logger.info(
                f"Grafo carregado: {stats['nodes']} nós, {stats['edges']} arestas"
            )
            return instance
        except Exception as e:
            logger.error(f"Erro ao carregar grafo: {e}")
            return None

