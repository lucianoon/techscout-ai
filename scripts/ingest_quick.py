#!/usr/bin/env python3
"""
Script rápido para ingestão - coleta dados online automaticamente
"""
import sys

from techscout.data_sources import TechNewsCollector
from techscout.ingestion import IngestionPipeline
from techscout.settings import settings


def main():
    """Ingestão rápida e automática"""
    # Configura encoding para Windows
    import sys
    if sys.platform == 'win32':
        import io
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
        sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')
    
    print("TechScout AI - Ingestao Rapida")
    print("=" * 60)
    
    # Valida API Key
    try:
        settings.validate()
    except ValueError as e:
        print(f"❌ {e}")
        return 1
    
    # Coleta dados (RSS apenas, não precisa de API key)
    print("\n📰 Coletando notícias de feeds RSS...")
    collector = TechNewsCollector()
    texts = collector.collect_from_rss(max_items_per_feed=5)
    
    if not texts:
        print("❌ Nenhum texto coletado")
        return 1
    
    print(f"✅ {len(texts)} textos coletados")
    
    # Processa
    print("\n⚙️  Processando dados...")
    pipeline = IngestionPipeline(model="gpt-3.5-turbo")
    success = pipeline.process(texts, clear_existing=True)
    
    if success:
        print("\n✅ Pronto! Execute: streamlit run streamlit_app.py")
        return 0
    else:
        print("\n❌ Falha na ingestão")
        return 1

if __name__ == "__main__":
    sys.exit(main())

