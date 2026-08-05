#!/usr/bin/env python3
"""
Script para ingestão de dados da internet
Busca notícias reais de feeds RSS e NewsAPI
"""
import os
import sys

try:
    from techscout.data_sources import TechNewsCollector
    from techscout.ingestion import IngestionPipeline
    from techscout.logger import logger
    from techscout.settings import settings
except ImportError as e:
    print(f"ERRO de importação: {e}")
    print("Certifique-se de estar na raiz do projeto")
    print("E de ter instalado o pacote: pip install -e .")
    sys.exit(1)

def main():
    """Função principal"""
    print("=" * 60)
    print("TechScout AI - Ingestão de Dados Online")
    print("=" * 60)
    print()
    
    # Verifica API Key
    try:
        settings.validate()
    except ValueError as e:
        print(f"❌ {e}")
        print("\nConfigure OPENAI_API_KEY no arquivo .env")
        return 1
    
    # Verifica NewsAPI key (opcional)
    newsapi_key = os.getenv("NEWSAPI_KEY")
    if not newsapi_key:
        print("⚠️  NEWSAPI_KEY não configurada")
        print("   Usando apenas feeds RSS (NewsAPI é opcional)")
        print("   Obtenha em: https://newsapi.org/")
        print()
    
    # Pergunta ao usuário
    print("Escolha a fonte de dados:")
    print("1. Feeds RSS apenas (gratuito, sem API key)")
    print("2. NewsAPI + RSS (requer NEWSAPI_KEY)")
    print("3. Ambos (se NewsAPI_KEY estiver configurada)")
    print()
    
    escolha = input("Escolha (1/2/3) [padrão: 1]: ").strip() or "1"
    
    use_newsapi = escolha in ["2", "3"] and newsapi_key
    use_rss = escolha in ["1", "3"]
    
    if not use_rss and not use_newsapi:
        print("❌ Nenhuma fonte selecionada")
        return 1
    
    # Pergunta quantidade
    try:
        max_items = int(input("Quantos artigos coletar? [padrão: 30]: ").strip() or "30")
    except ValueError:
        max_items = 30
    
    print()
    print("=" * 60)
    print("Coletando dados...")
    print("=" * 60)
    print()
    
    # Coleta dados
    collector = TechNewsCollector(newsapi_key=newsapi_key)
    
    try:
        texts = collector.collect_all(
            use_newsapi=use_newsapi,
            use_rss=use_rss,
            max_items=max_items
        )
        
        if not texts:
            print("❌ Nenhum texto coletado")
            return 1
        
        print(f"\n✅ Coletados {len(texts)} textos")
        print()
        print("=" * 60)
        print("Processando dados (extração de triplas)...")
        print("=" * 60)
        print()
        
        # Processa dados
        pipeline = IngestionPipeline(model="gpt-3.5-turbo")
        success = pipeline.process(texts, clear_existing=True)
        
        if success:
            print()
            print("=" * 60)
            print("✅ Ingestão concluída com sucesso!")
            print("=" * 60)
            print()
            print("Agora você pode executar:")
            print("  streamlit run streamlit_app.py")
            return 0
        else:
            print("❌ Falha na ingestão")
            return 1
            
    except KeyboardInterrupt:
        print("\n\nOperação cancelada pelo usuário")
        return 1
    except Exception as e:
        logger.error(f"Erro inesperado: {e}", exc_info=True)
        print(f"\n❌ Erro: {e}")
        return 1

if __name__ == "__main__":
    sys.exit(main())

