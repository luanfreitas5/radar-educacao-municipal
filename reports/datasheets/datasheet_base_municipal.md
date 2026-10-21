# Datasheet — base municipal `data/gold/municipios.parquet`

## Motivação
Integrar indicadores de infraestrutura escolar, desempenho (IDEB) e contexto socioeconômico
por município para identificar tipologias e padrões espaciais. Projeto de portfólio/pesquisa;
não foi criado para decisões individuais nem para ranquear escolas.

## Composição
Uma linha por município da malha do IBGE (~5.570). Colunas: identificação (`code_muni`,
`name_muni`, `abbrev_state`, `region`), agregados do Censo Escolar (escolas em atividade),
IDEB (rede pública, anos iniciais e finais) e indicadores do IBGE (população, área,
densidade, PIB per capita). Dicionário completo: `src/constants/columns.py` e
`src/schemas/`.

## Coleta
Download automatizado e idempotente (`make ingest`) de fontes públicas. Cada arquivo bruto
é registrado em `data/bronze/<fonte>/<ano>/manifest.json` com URL, SHA-256 e data.

| Fonte | Responsável | Licença/uso |
|---|---|---|
| Censo Escolar — microdados | INEP | dados abertos (verificar termos vigentes no portal do INEP) |
| IDEB — resultados por município | INEP | dados abertos (idem) |
| SIDRA — tabelas 4714 e 5938 | IBGE | dados abertos |
| Malha municipal (`geobr`) | IBGE/IPEA | dados abertos |

## Pré-processamento
Filtro de escolas em atividade; proporções como média de indicadores 0/1; razão
alunos/docente nula quando não há docentes; densidade e PIB per capita calculados; chave
de junção `code_muni` (7 dígitos) validada por contrato `pandera`. Os dados bronze nunca
são alterados.

## Privacidade e LGPD
- Base **agregada por município**; nenhuma variável identifica pessoas.
- Os microdados do Censo Escolar usados são de **escolas** (não de alunos ou docentes
  individuais); apenas contagens e indicadores 0/1 são lidos — nomes de escolas, endereços
  e demais colunas nem são carregados.
- Base legal: tratamento de dados públicos/anonimizados para estudos e pesquisa
  (art. 7º, IV e art. 12 da LGPD); não há dado pessoal na base final.
- Risco de reidentificação: municípios muito pequenos têm poucas escolas; os resultados
  são reportados por cluster e região, nunca por escola.

## Usos recomendados e não recomendados
- Recomendado: análise exploratória, tipologias, estudos espaciais.
- Não recomendado: inferência causal, avaliação individual de escolas, alocação de recursos
  sem análise complementar.

## Limitações conhecidas
Anos de referência distintos entre fontes; IDEB ausente em municípios pequenos;
autodeclaração no Censo Escolar; falácia ecológica ao interpretar resultados municipais.
Veja `reports/relatorio.md` (gerado) para a lista completa.

## Manutenção
Atualizar os anos em `configs/config.yaml` e reexecutar `make reproduce`.
