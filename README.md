# 🎓 Radar da Educação Municipal

[![CI](https://github.com/luanfreitas5/radar-educacao-municipal/actions/workflows/ci.yml/badge.svg)](https://github.com/luanfreitas5/radar-educacao-municipal/actions/workflows/ci.yml)
[![Tests](https://github.com/luanfreitas5/radar-educacao-municipal/actions/workflows/tests.yml/badge.svg)](https://github.com/luanfreitas5/radar-educacao-municipal/actions/workflows/tests.yml)
[![codecov](https://codecov.io/gh/luanfreitas5/radar-educacao-municipal/branch/main/graph/badge.svg)](https://codecov.io/gh/luanfreitas5/radar-educacao-municipal)
[![Docs](https://github.com/luanfreitas5/radar-educacao-municipal/actions/workflows/docs.yml/badge.svg)](https://luanfreitas5.github.io/radar-educacao-municipal/)
![Python](https://img.shields.io/badge/python-3.10%2B-blue)
[![License: MIT](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)

Integra **Censo Escolar**, **IDEB** e dados do **IBGE** por município e identifica
**tipologias de municípios** com **análise espacial** (I de Moran e LISA).

## 🧭 Problema

Os 5.570 municípios brasileiros diferem muito em infraestrutura escolar, porte e renda,
e as políticas educacionais costumam tratá-los como um bloco homogêneo (ou apenas por UF).
Falta uma visão integrada que mostre **quais perfis de município existem**, **como o IDEB
se distribui entre eles** e **se esses perfis ocupam o território de forma agrupada**.

## ❓ Pergunta

1. Que tipologias de município emergem de infraestrutura escolar e contexto socioeconômico?
2. O IDEB — que **não** entra na clusterização — difere entre as tipologias (e com que magnitude)?
3. O IDEB e as tipologias apresentam **autocorrelação espacial**? Onde estão os aglomerados
   Alto-Alto e Baixo-Baixo?

## 📦 Dados

| Fonte | Conteúdo | Chave |
|---|---|---|
| [Censo Escolar (INEP)](https://www.gov.br/inep/pt-br/acesso-a-informacao/dados-abertos/microdados/censo-escolar) | infraestrutura, matrículas e docentes (escola → município) | `CO_MUNICIPIO` |
| [IDEB (INEP)](https://www.gov.br/inep/pt-br/areas-de-atuacao/pesquisas-estatisticas-e-indicadores/ideb) | nota observada, anos iniciais e finais, rede pública | `CO_MUNICIPIO` |
| [SIDRA (IBGE)](https://sidra.ibge.gov.br/) | população, área (tab. 4714) e PIB (tab. 5938) | código do município |
| [geobr](https://github.com/ipeaGIT/geobr) | malha municipal e UF | `code_muni` |

Chave de junção: **código IBGE de 7 dígitos** (`code_muni`), validado por contrato de dados.
Detalhes e cuidados em [docs/data_sources.md](docs/data_sources.md) e no
[datasheet](reports/datasheets/datasheet_base_municipal.md). **Os dados brutos não são
versionados no Git**: `make ingest` os baixa para `data/bronze/` com cache e hash.

## 🔬 Método

```
ingestão ► bronze ► silver (agregado + contrato) ► gold (junção + integridade)
        ► KMeans + UMAP + perfil ► Queen + Moran + LISA ► relatório
```

1. **Ingestão idempotente** com cache local e `manifest.json` (URL, SHA-256, data).
2. **Agregação por município** e junção à esquerda sobre a malha do IBGE, com testes de
   integridade (cobertura mínima por fonte, duplicatas, chaves órfãs e fração de nulos).
3. **Clusterização:** `log1p` nas variáveis assimétricas → padronização → k por silhouette
   → KMeans → estabilidade por subamostragem (ARI) → UMAP *apenas* para visualização →
   perfil por cluster com IC 95% bootstrap do IDEB e teste de Kruskal-Wallis (com ε²).
4. **Análise espacial:** vizinhança Queen (ilhas removidas), I de Moran global, LISA com
   permutações e correção FDR (Benjamini-Hochberg), mapa de clusters LISA e coesão
   territorial das tipologias.
5. **Relatório** automático em `reports/relatorio.md`.

## 🚀 Como reproduzir

Requisitos: [uv](https://docs.astral.sh/uv/), Python 3.10+ e ~2 GB livres em disco.

```bash
git clone https://github.com/luanfreitas5/radar-educacao-municipal.git
cd radar-educacao-municipal
make init          # uv sync + hooks do pre-commit
make reproduce     # ingest → silver → gold → cluster → spatial → report
```

Etapas individuais: `make ingest`, `make silver`, `make gold`, `make cluster`,
`make spatial`, `make report`. Qualidade e testes: `make check` (espelha o CI).
Anos de referência, URLs e hiperparâmetros ficam em [`configs/`](configs/), validados com
Pydantic na inicialização.

> ⚠️ O INEP reorganiza os caminhos de download com frequência. Se `make ingest` retornar 404,
> atualize a URL em `configs/data_sources.yaml`. Os nomes das colunas do Censo Escolar
> seguem o dicionário de dados do ano de referência; mudanças são detectadas com erro
> explicativo.

## 📊 Resultados

Os números dependem da execução do pipeline com os dados reais e **são gerados
automaticamente** em [`reports/relatorio.md`](reports/relatorio.md), com figuras em
`reports/figures/` (PNG 300 dpi + SVG). Esta seção será preenchida com os achados após a
primeira execução completa (`make reproduce`): tipologias encontradas, estabilidade (ARI),
diferenças de IDEB entre clusters com IC 95%, I de Moran e mapa LISA.

## ⚠️ Limitações

- Análise **municipal**: não se aplica diretamente a escolas ou estudantes (falácia ecológica).
- **Associação, não causalidade**: o IDEB difere entre tipologias, mas nada aqui estima efeitos.
- Anos de referência diferentes entre fontes (ex.: PIB 2021 dividido pela população 2022).
- IDEB ausente em municípios pequenos pode enviesar a comparação do desfecho.
- KMeans supõe grupos esféricos; o k por silhouette favorece poucos grupos. O UMAP é só ilustrativo.
- Queen e ilhas removidas: o tamanho irregular dos municípios afeta a vizinhança (MAUP).
- LISA aponta associação espacial local, não a causa dos aglomerados.

Lista completa e discussão no relatório gerado.

## 🗂️ Estrutura

```
configs/        YAML validados (config, paths, logging, data_sources, model_params)
data/           bronze (imutável) · silver · gold — fora do Git
src/            config · ingestion · preprocessing · schemas · validation ·
                modeling · spatial · visualization · reporting · pipelines · main.py
tests/          unitários, propriedades (hypothesis), comportamentais e integração
notebooks/      exploração e apresentação (sem lógica de produção)
reports/        relatório, figuras, datasheet
docs/           MkDocs Material + API gerada das docstrings
```

## 🛠️ Convenções

Python 3.10+ com `uv` · Polars no lugar de pandas (pandas só onde geopandas/esda exigem) ·
identificadores em inglês, docstrings NumPy em pt-BR · `ruff`, `basedpyright`, `pytest`
(≥ 80% de cobertura) e `pre-commit` · Conventional Commits.

## 📄 Licença

[MIT](LICENSE) © Luan Freitas
