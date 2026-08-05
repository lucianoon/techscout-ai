"""
Script de teste para verificar se tudo está configurado corretamente
"""
import os
import sys
from pathlib import Path

print("=" * 60)
print("TechScout AI - Verificação de Setup")
print("=" * 60)

errors = []
warnings = []

# 1. Verificar Python
print("\n1. Verificando Python...")
try:
    version = sys.version_info
    if version.major >= 3 and version.minor >= 8:
        print(f"   ✅ Python {version.major}.{version.minor}.{version.micro}")
    else:
        errors.append(f"Python {version.major}.{version.minor} - requer 3.8+")
except Exception as e:
    errors.append(f"Erro ao verificar Python: {e}")

# 2. Verificar estrutura de pastas
print("\n2. Verificando estrutura de pastas...")
required_dirs = [
    "src/techscout",
    "config",
    "data",
    "logs"
]
for dir_path in required_dirs:
    if Path(dir_path).exists():
        print(f"   ✅ {dir_path}/")
    else:
        warnings.append(f"Pasta {dir_path}/ não existe (será criada automaticamente)")

# 3. Verificar imports
print("\n3. Verificando imports...")
try:
    from techscout.settings import settings  # noqa: F401
    print("   ✅ techscout.settings")
except ImportError as e:
    errors.append(f"Erro ao importar config: {e}")

try:
    from techscout.logger import logger  # noqa: F401
    print("   ✅ techscout.logger")
except ImportError as e:
    errors.append(f"Erro ao importar logger: {e}")

try:
    from techscout.graph_rag import GraphRAG  # noqa: F401
    print("   ✅ techscout.graph_rag")
except ImportError as e:
    errors.append(f"Erro ao importar GraphRAG: {e}")

try:
    from techscout.vector_store import VectorStore  # noqa: F401
    print("   ✅ techscout.vector_store")
except ImportError as e:
    errors.append(f"Erro ao importar VectorStore: {e}")

# 4. Verificar dependências
print("\n4. Verificando dependências principais...")
dependencies = {
    "streamlit": "streamlit",
    "langchain": "langchain",
    "networkx": "networkx",
    "chromadb": "chromadb",
    "openai": "langchain-openai",
    "dotenv": "python-dotenv"
}

for module, package in dependencies.items():
    try:
        __import__(module)
        print(f"   ✅ {package}")
    except ImportError:
        errors.append(f"{package} não instalado - execute: pip install {package}")

# 5. Verificar API Key
print("\n5. Verificando configuração...")
api_key = os.getenv("OPENAI_API_KEY")
if api_key:
    if api_key.startswith("sk-"):
        print("   ✅ OPENAI_API_KEY configurada")
    else:
        warnings.append("OPENAI_API_KEY não parece ser válida (deve começar com 'sk-')")
else:
    # Verifica arquivo .env
    env_file = Path(".env")
    if env_file.exists():
        with open(env_file) as f:
            content = f.read()
            if "OPENAI_API_KEY" in content:
                print("   ⚠️  OPENAI_API_KEY encontrada em .env (mas não carregada)")
                warnings.append("Certifique-se de que python-dotenv está instalado")
            else:
                errors.append("OPENAI_API_KEY não encontrada em .env")
    else:
        errors.append("OPENAI_API_KEY não configurada (variável de ambiente ou .env)")

# 6. Verificar dados
print("\n6. Verificando dados...")
if Path("data/samples/noticias_exemplo.py").exists():
    print("   ✅ dados de exemplo encontrados")
else:
    warnings.append("data/samples/noticias_exemplo.py não encontrado")

if Path("data/graph_data.json").exists():
    print("   ✅ Dados processados encontrados (graph_data.json)")
elif Path("data/graph_data.pkl").exists():
    print("   ⚠️  Dados processados encontrados (graph_data.pkl legado)")
    warnings.append("Grafo em formato legado (pickle). Recomendado reexecutar a ingestão.")
else:
    warnings.append("Dados ainda não processados - execute: python scripts/ingest.py")

# Resumo
print("\n" + "=" * 60)
print("RESUMO")
print("=" * 60)

if errors:
    print(f"\n❌ ERROS ENCONTRADOS ({len(errors)}):")
    for error in errors:
        print(f"   - {error}")
    print("\nCorrija os erros antes de continuar.")
else:
    print("\n✅ Nenhum erro encontrado!")

if warnings:
    print(f"\n⚠️  AVISOS ({len(warnings)}):")
    for warning in warnings:
        print(f"   - {warning}")

if not errors:
    print("\n✅ Setup verificado com sucesso!")
    print("\nPróximos passos:")
    print("1. Configure OPENAI_API_KEY se ainda não fez")
    print("2. Execute: python scripts/ingest.py")
    print("3. Execute: streamlit run streamlit_app.py")
else:
    print("\n❌ Corrija os erros acima antes de continuar")
    sys.exit(1)

