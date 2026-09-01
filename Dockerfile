FROM python:3.11-slim

COPY --from=ghcr.io/astral-sh/uv:0.9.7 /uv /usr/local/bin/uv

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PROJECT_ENVIRONMENT=/usr/local

WORKDIR /app

# gcc é necessário para compilar dependências nativas do chromadb quando não há wheel.
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Camada de dependências: só invalida quando o lockfile muda. As versões são
# exatamente as que o CI testou (`uv sync --locked`).
COPY pyproject.toml uv.lock README.md LICENSE ./
RUN uv sync --locked --no-dev --no-install-project

COPY src/ ./src/
RUN uv sync --locked --no-dev --no-editable

COPY streamlit_app.py ./
COPY scripts/ ./scripts/
COPY .streamlit/ ./.streamlit/

# Artefatos do corpus de exemplo pré-processados (grafo + ChromaDB): a demo
# já nasce consultável, sem exigir ingestão no primeiro acesso.
COPY data/graph_data.json ./data/graph_data.json
COPY data/chroma_db ./data/chroma_db
COPY data/chroma_graph_nodes ./data/chroma_graph_nodes

RUN mkdir -p logs

# Processo sem root. O usuário precisa de HOME gravável porque o Streamlit
# escreve ~/.streamlit; data/ e logs/ ficam dele para o ChromaDB e os logs.
RUN useradd --create-home --uid 1000 app && chown -R app:app /app
USER app

ENV PYTHONUNBUFFERED=1 \
    LOG_LEVEL=INFO \
    STREAMLIT_PORT=8501

EXPOSE 8501

# Consulta o endpoint de saúde do próprio Streamlit, não apenas o import do
# pacote: o objetivo é saber se a aplicação atende, não se ela instalou.
HEALTHCHECK --interval=30s --timeout=10s --start-period=20s --retries=3 \
    CMD python -c "import urllib.request,sys; sys.exit(0 if urllib.request.urlopen('http://localhost:8501/_stcore/health', timeout=5).status==200 else 1)" || exit 1

CMD ["streamlit", "run", "streamlit_app.py", \
     "--server.port=8501", "--server.address=0.0.0.0", \
     "--server.headless=true"]
