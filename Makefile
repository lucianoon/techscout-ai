.PHONY: help install lint typecheck test cov check run ingest docker clean

help:
	@echo "install    instala o pacote com dependências de desenvolvimento"
	@echo "lint       ruff check"
	@echo "typecheck  mypy"
	@echo "test       pytest com cobertura de branch e piso de 75%"
	@echo "check      lint + typecheck + test (o que a CI roda)"
	@echo "run        sobe a interface Streamlit"
	@echo "ingest     executa a ingestão de dados"
	@echo "docker     constrói a imagem"
	@echo "clean      remove caches e artefatos de cobertura"

install:
	pip install -e ".[dev]"

lint:
	ruff check .

typecheck:
	mypy

test:
	coverage run -m pytest -q
	coverage report --show-missing --skip-covered --fail-under=75

cov: test
	coverage html
	@echo "relatório em htmlcov/index.html"

check: lint typecheck test

run:
	streamlit run streamlit_app.py

ingest:
	python scripts/ingest.py

docker:
	docker build --tag techscout-ai:local .

clean:
	rm -rf .pytest_cache .mypy_cache .ruff_cache htmlcov .coverage coverage.json
	find . -type d -name __pycache__ -not -path "./.venv/*" -exec rm -rf {} + 2>/dev/null || true
