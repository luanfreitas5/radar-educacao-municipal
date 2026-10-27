# --- Configuração ----------------------------------------------------------
PIPELINE := uv run python src/main.py

# PYTHONHASHSEED precisa ser exportado ANTES do interpretador iniciar: definido
# dentro do processo, não afeta a ordem de iteração de conjuntos já criada.
export PYTHONHASHSEED := 42

.DEFAULT_GOAL := help
.PHONY: help install update hooks lock export \
	lint format typecheck security quality check pre-commit update-hooks release \
	test smoke test-all coverage \
	ingest silver gold cluster spatial report reproduce \
	docs docs-serve docs-deploy profile clean clean-outputs jupyter

help:  ## Lista os alvos disponíveis
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | \
		awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-14s\033[0m %s\n", $$1, $$2}'

# --- Ambiente --------------------------------------------------------------
install:  ## Instala todas as dependências e os hooks do pre-commit
	uv sync --all-groups
	uv run pre-commit install --hook-type pre-commit --hook-type commit-msg

update:  ## Atualiza todas as dependências e sincroniza
	uv lock --upgrade
	uv sync --all-groups

hooks:  ## Instala os hooks do pre-commit (para quem já tem o ambiente)
	uv run detect-secrets scan > .secrets.baseline

lock:  ## Gera/atualiza o uv.lock
	uv lock

export:  ## Exporta requirements.txt (para quem usa pip)
	uv export --no-hashes -o requirements.txt

# --- Qualidade -------------------------------------------------------------
lint:  ## Verifica lint e formatação sem alterar arquivos (usado no CI)
	uv run ruff check src tests
	uv run ruff format --check src tests

format:  ## Corrige lint e formata o código com ruff
	uv run ruff check --fix src tests
	uv run ruff format src tests

typecheck:  ## Type checking estático (basedPyright)
	uv run basedpyright

security:  ## Análise de segurança (bandit + pip-audit)
	uv run bandit -c pyproject.toml -r src
	uv run pip-audit

quality:  ## Código morto, modernização, complexidade e docstrings
	uv run vulture
	uv run refurb src
	uv run xenon --max-absolute B --max-modules A --max-average A src
	uv run interrogate src

check: lint typecheck security quality test  ## Roda tudo o que o CI roda (espelha o CI)

pre-commit:  ## Roda todos os hooks do pre-commit em todos os arquivos
	uv run pre-commit run --all-files

update-hooks:  ## Atualiza as versões dos hooks do pre-commit
	uv run pre-commit autoupdate

release:  ## Cria uma nova release (versão + changelog + tag)
	uv run cz bump --changelog

# --- Testes ----------------------------------------------------------------
test:  ## Roda os testes com cobertura
	uv run pytest -m "not slow"

smoke:  ## Roda apenas os smoke tests
	uv run pytest -m smoke -q --no-cov

test-all:  ## Roda a suíte completa, inclusive os testes lentos
	uv run pytest

coverage:  ## Gera o relatório de cobertura em HTML
	uv run pytest -m "not slow" --cov-report=html
	@echo "Relatório disponível em htmlcov/index.html"

# --- Pipeline (bronze -> silver -> gold -> análises -> relatório) -----------
ingest:  ## Etapa 1: baixa as fontes para data/bronze (idempotente, com cache)
	$(PIPELINE) ingest

silver:  ## Etapa 2a: limpa, agrega por município e valida (data/silver)
	$(PIPELINE) silver

gold:  ## Etapa 2b: junta pelo código de 7 dígitos e roda os testes de integridade (data/gold)
	$(PIPELINE) gold

cluster:  ## Etapa 3: padronização, KMeans, UMAP e perfil dos clusters
	$(PIPELINE) cluster

spatial:  ## Etapa 4: vizinhança Queen, I de Moran e mapa LISA
	$(PIPELINE) spatial

report:  ## Etapa 5: gera reports/relatorio.md
	$(PIPELINE) report

reproduce:  ## Executa o pipeline completo, do download ao relatório
	$(PIPELINE) all

# --- Documentação ----------------------------------------------------------
docs:  ## Constrói a documentação (modo estrito)
	uv run mkdocs build --strict

docs-serve:  ## Servidor local da documentação
	uv run mkdocs serve

docs-deploy:  ## Publica a documentação no GitHub Pages
	uv run mkdocs gh-deploy --force

# --- Utilitários -----------------------------------------------------------
profile:  ## Profiling com scalene (ajuste o alvo conforme a etapa)
	uv run scalene src/main.py silver

jupyter:  ## Abre o JupyterLab
	uv run jupyter lab

clean:  ## Remove caches e artefatos temporários
	rm -rf .pytest_cache .ruff_cache .hypothesis htmlcov coverage.xml site
	find . -type d -name __pycache__ -not -path "./.venv/*" -exec rm -rf {} +

clean-outputs:  ## Remove saídas derivadas (silver, gold, relatórios); bronze nunca é apagado
	rm -rf data/silver/* data/gold/* reports/relatorio.md reports/results.json reports/figures/*
