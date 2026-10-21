# --- Configuração ----------------------------------------------------------
PIPELINE := uv run python src/main.py

# PYTHONHASHSEED precisa ser exportado ANTES do interpretador iniciar: definido
# dentro do processo, não afeta a ordem de iteração de conjuntos já criada.
export PYTHONHASHSEED := 42

.DEFAULT_GOAL := help
.PHONY: help init install update lock export \
	lint format-check typecheck security deadcode complexity docstrings modernize quality check \
	test smoke test-all coverage hooks pre-commit update-hooks release \
	ingest silver gold cluster spatial report reproduce \
	docs docs-serve docs-deploy profile clean clean-outputs jupyter

help:  ## Lista os alvos disponíveis
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | \
		awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-14s\033[0m %s\n", $$1, $$2}'

# --- Ambiente --------------------------------------------------------------
init:  ## Instala dependências e hooks do pre-commit
	$(MAKE) install
	$(MAKE) hooks

install:  ## Instala dependências (runtime + dev)
	uv sync --dev

update:  ## Atualiza todas as dependências e sincroniza
	uv lock --upgrade
	uv sync --all-groups

lock:  ## Gera/atualiza o uv.lock
	uv lock

export:  ## Exporta requirements.txt (para quem usa pip)
	uv export --no-hashes -o requirements.txt

# --- Qualidade -------------------------------------------------------------
lint:  ## Formata e aplica lint com ruff (corrige o que for possível)
	uv run ruff format .
	uv run ruff check --fix .

format-check:  ## Verifica formatação e lint sem alterar arquivos (usado no CI)
	uv run ruff format --check .
	uv run ruff check .

typecheck:  ## Type checking estático (basedPyright)
	uv run basedpyright

security:  ## Análise de segurança (bandit + pip-audit)
	uv run bandit -r src -c pyproject.toml
	uv run pip-audit

deadcode:  ## Detecta código morto (vulture)
	uv run vulture src

complexity:  ## Limites de complexidade (xenon)
	uv run xenon --max-absolute B --max-modules A --max-average A src

docstrings:  ## Cobertura de docstrings (interrogate)
	uv run interrogate -v src

modernize:  ## Detecta código redundante (refurb)
	uv run refurb src

quality: format-check typecheck security deadcode complexity docstrings modernize  ## Suíte de qualidade completa (espelha o CI)

check: quality test  ## Roda tudo o que o CI roda (qualidade + testes)

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

hooks:  ## Instala os hooks do pre-commit e gera o baseline do detect-secrets
	uv run pre-commit install
	uv run pre-commit install --hook-type commit-msg
	uv run detect-secrets scan > .secrets.baseline

pre-commit:  ## Roda todos os hooks do pre-commit em todos os arquivos
	uv run pre-commit run --all-files

update-hooks:  ## Atualiza as versões dos hooks do pre-commit
	uv run pre-commit autoupdate

release:  ## Cria uma nova release (versão + changelog + tag)
	uv run cz bump --changelog

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
