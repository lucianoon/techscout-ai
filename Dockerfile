FROM python:3.11-slim

WORKDIR /app

# gcc é necessário para compilar dependências nativas do chromadb.
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Copia primeiro os metadados do pacote: enquanto pyproject.toml não mudar,
# a camada de dependências é reaproveitada entre builds.
COPY pyproject.toml README.md LICENSE ./
COPY src/ ./src/
RUN pip install --no-cache-dir .

COPY streamlit_app.py ./
COPY scripts/ ./scripts/
COPY .streamlit/ ./.streamlit/

RUN mkdir -p data logs

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
