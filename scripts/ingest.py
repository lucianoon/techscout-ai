#!/usr/bin/env python3
"""
Script de ingestão de dados para TechScout AI
Uso: python scripts/ingest.py [--data-file data/samples/noticias_exemplo.py]
"""
import importlib.util
import sys

from techscout.ingestion import IngestionPipeline
from techscout.logger import logger
from techscout.settings import settings


def load_data_source(data_file: str = "data/samples/noticias_exemplo.py"):
    """
    Carrega dados de um arquivo Python
    
    Args:
        data_file: Caminho do arquivo com os dados
        
    Returns:
        Lista de textos
    """
    try:
        spec = importlib.util.spec_from_file_location("data_source", data_file)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        
        # Tenta diferentes nomes de variáveis comuns
        for var_name in ['noticias', 'texts', 'articles', 'data']:
            if hasattr(module, var_name):
                data = getattr(module, var_name)
                if isinstance(data, list):
                    return data
        
        raise ValueError(f"Nenhuma lista encontrada em {data_file}")
        
    except Exception as e:
        logger.error(f"Erro ao carregar fonte de dados: {e}")
        raise

def main():
    """Função principal"""
    try:
        # Valida configurações
        settings.validate()
        
        logger.info("=" * 60)
        logger.info("TechScout AI - Pipeline de Ingestão")
        logger.info("=" * 60)
        
        # Carrega dados
        data_file = sys.argv[1] if len(sys.argv) > 1 else "data/samples/noticias_exemplo.py"
        logger.info(f"Carregando dados de: {data_file}")
        texts = load_data_source(data_file)
        
        if not texts:
            logger.error("Nenhum texto encontrado para processar")
            return 1
        
        logger.info(f"Encontrados {len(texts)} textos para processar")
        
        # Inicializa pipeline
        pipeline = IngestionPipeline(model="gpt-3.5-turbo")
        
        # Processa dados
        success = pipeline.process(texts, clear_existing=True)
        
        if success:
            logger.info("✅ Ingestão concluída com sucesso!")
            return 0
        else:
            logger.error("❌ Falha na ingestão")
            return 1
            
    except ValueError as e:
        logger.error(f"Erro de configuração: {e}")
        return 1
    except Exception as e:
        logger.error(f"Erro inesperado: {e}", exc_info=True)
        return 1

if __name__ == "__main__":
    sys.exit(main())

