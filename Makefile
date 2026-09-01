.PHONY: help install lint typecheck test cov check eval run ingest docker clean

help:
	@echo "install    uv sync --extra dev --locked (mesmas versões do CI e da imagem)"
	@echo "lint       ruff check"
	@echo "typecheck  mypy"
	@echo "test       pytest com cobertura de branch e piso de 75%"
	@echo "check      lint + typecheck + test (o que a CI roda)"
	@echo "eval       Recall@K e MRR do grafo, do BM25 e da fusão"
	@echo "eval-extraction  extração por LLM vs grafo curado (usa cache)"
	@echo "run        sobe a interface Streamlit"
	@echo "ingest     executa a ingestão de dados"
	@echo "docker     constrói a imagem"
	@echo "clean      remove caches e artefatos de cobertura"

install:
	uv sync --extra dev --locked

lint:
	uv run ruff check .

typecheck:
	uv run mypy

test:
	uv run coverage run -m pytest -q
	uv run coverage report --show-missing --skip-covered --fail-under=75

cov: test
	uv run coverage html
	@echo "relatório em htmlcov/index.html"

check: lint typecheck test

eval:
	uv run python -m techscout.evaluation -k 5

eval-extraction:
	uv run python -m techscout.extraction_eval --model gpt-3.5-turbo -k 5

# Reextrai chamando a API — consome créditos e reescreve o cache versionado.
eval-extraction-refresh:
	uv run python -m techscout.extraction_eval --model gpt-3.5-turbo -k 5 --refresh

run:
	uv run streamlit run streamlit_app.py

ingest:
	uv run python scripts/ingest.py

docker:
	docker build --tag techscout-ai:local .

clean:
	rm -rf .pytest_cache .mypy_cache .ruff_cache htmlcov .coverage coverage.json
	find . -type d -name __pycache__ -not -path "./.venv/*" -exec rm -rf {} + 2>/dev/null || true
