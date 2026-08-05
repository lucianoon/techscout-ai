"""
Pipeline de ingestão de dados para TechScout AI
"""
import shutil
from pathlib import Path

from langchain_core.documents import Document

from techscout.graph_rag import GraphRAG
from techscout.logger import logger
from techscout.settings import settings
from techscout.triple_extractor import TripleExtractor
from techscout.vector_store import VectorStore


class IngestionPipeline:
    """Pipeline completo de ingestão de dados"""
    
    def __init__(self, model: str = "gpt-3.5-turbo"):
        """
        Inicializa o pipeline de ingestão
        
        Args:
            model: Modelo OpenAI para extração de triplas
        """
        self.graph_rag = GraphRAG()
        self.vector_store = VectorStore()
        self.triple_extractor = TripleExtractor(model=model)
        self.logger = logger
    
    def process(self, texts: list[str], clear_existing: bool = True) -> bool:
        """
        Processa uma lista de textos
        
        Args:
            texts: Lista de textos para processar
            clear_existing: Se True, limpa dados existentes antes de processar
            
        Returns:
            True se processado com sucesso
        """
        try:
            if clear_existing:
                self._clear_existing_data()
            
            self.logger.info(f"Iniciando ingestão de {len(texts)} textos")
            
            docs_para_vetor = []
            triplas_totais = 0
            
            for i, texto in enumerate(texts, 1):
                if not texto or not texto.strip():
                    self.logger.warning(f"Texto {i} está vazio, pulando...")
                    continue
                
                self.logger.info(f"Processando texto {i}/{len(texts)}...")
                
                # Extração de triplas
                triplas = self.triple_extractor.extract(texto)
                count = self.graph_rag.add_triples(triplas)
                triplas_totais += count
                
                # Preparação para vector store
                docs_para_vetor.append(Document(page_content=texto))
            
            # Salva grafo
            if not self.graph_rag.save():
                self.logger.error("Falha ao salvar grafo")
                return False

            try:
                self.graph_rag.build_node_index(clear_existing=True)
            except Exception as e:
                self.logger.warning(f"Falha ao construir índice vetorial de nós: {e}")
            
            # Salva vector store
            if not self.vector_store.add_documents(docs_para_vetor):
                self.logger.error("Falha ao adicionar documentos ao vector store")
                return False
            
            stats = self.graph_rag.get_stats()
            self.logger.info(
                f"Ingestão concluída: {len(docs_para_vetor)} documentos, "
                f"{triplas_totais} triplas, {stats['nodes']} nós, {stats['edges']} arestas"
            )
            
            return True
            
        except Exception as e:
            self.logger.error(f"Erro no pipeline de ingestão: {e}", exc_info=True)
            return False
    
    def _clear_existing_data(self):
        """Limpa dados existentes"""
        try:
            # Limpa ChromaDB
            chroma_path = Path(settings.CHROMA_PERSIST_DIR)
            if chroma_path.exists():
                try:
                    shutil.rmtree(chroma_path)
                    self.logger.info("ChromaDB existente removido")
                except Exception as e:
                    self.logger.warning(f"Erro ao remover ChromaDB existente: {e}")

            node_chroma_path = Path(getattr(settings, "GRAPH_NODE_CHROMA_PERSIST_DIR", ""))
            if node_chroma_path and node_chroma_path.exists():
                try:
                    shutil.rmtree(node_chroma_path)
                    self.logger.info("Índice vetorial de nós existente removido")
                except Exception as e:
                    self.logger.warning(f"Erro ao remover índice vetorial de nós: {e}")
            
            # Limpa grafo
            graph_path = Path(settings.GRAPH_DATA_PATH)
            if graph_path.exists():
                graph_path.unlink()
                self.logger.info("Grafo existente removido")

            legacy_graph_path = Path(getattr(settings, "GRAPH_DATA_LEGACY_PKL_PATH", ""))
            if legacy_graph_path and legacy_graph_path.exists():
                legacy_graph_path.unlink()
                self.logger.info("Grafo legado existente removido")
                
        except Exception as e:
            self.logger.warning(f"Erro ao limpar dados existentes: {e}")

