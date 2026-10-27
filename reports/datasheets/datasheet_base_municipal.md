# Datasheet — base municipal `data/gold/municipios.parquet`

## 1. Motivação
- Por que foi criado? Integrar indicadores de infraestrutura escolar, desempenho (IDEB) e contexto socioeconômico por município, para identificar tipologias e padrões espaciais. Não foi criado para decisões individuais nem para ranquear escolas.
- Quem criou e quem financiou? Luan Freitas, como projeto de portfólio/pesquisa, sem financiamento externo.

## 2. Composição
- O que cada instância representa? Um município da malha do IBGE.
- Número de instâncias e período coberto: 5.570 municípios; Censo Escolar 2023, IDEB 2023, população 2022 (Censo Demográfico), PIB 2021, malha 2022.
- Campos, tipos e contrato: identificação (`code_muni`, `name_muni`, `abbrev_state`, `region`), agregados do Censo Escolar (escolas em atividade), IDEB (rede pública, anos iniciais e finais) e indicadores do IBGE (população, área, densidade, PIB per capita). Contrato: `src/schemas/silver.py` e `src/schemas/gold.py`; dicionário em `src/constants/columns.py`.
- Rótulo: não há rótulo supervisionado. O IDEB (nota observada, rede pública) é usado como desfecho externo, fora da clusterização.
- Dados ausentes (taxa por coluna): `ideb_early_years` 2,5%; `ideb_late_years` 3,4%; demais colunas 0% (ver `reports/integrity_report.json`).
- Campos sensíveis / PII e tratamento: nenhum campo identifica pessoas; os dados são agregados por município.
- É amostra de uma população maior? Não — cobre a totalidade dos municípios da malha. Cobertura por fonte: Censo Escolar, população e PIB per capita 100%; IDEB anos iniciais 97,5% e anos finais 96,6%.

## 3. Processo de coleta
- Fontes e sistemas de origem: download automatizado e idempotente (`make ingest`) de fontes públicas, registrado em `data/bronze/<fonte>/<ano>/manifest.json` (URL, SHA-256 e data).

| Fonte | Responsável | Licença/uso |
|---|---|---|
| Censo Escolar — microdados | INEP | dados abertos (verificar termos vigentes no portal do INEP) |
| IDEB — resultados por município | INEP | dados abertos (idem) |
| SIDRA — tabelas 4714 e 5938 | IBGE | dados abertos |
| Malha municipal (`geobr`) | IBGE/IPEA | dados abertos |

- Período e frequência de coleta: snapshot único por execução; anos de referência em `configs/config.yaml`.
- Consentimento / aviso aos titulares: não se aplica — não há dado pessoal e as fontes são divulgadas publicamente pelos órgãos.

## 4. Pré-processamento
- Limpeza, filtragem e linhas removidas por regra: filtro de escolas em atividade; proporções como média de indicadores 0/1; razão alunos/docente nula quando não há docentes; densidade e PIB per capita calculados; junção à esquerda sobre a malha pela chave `code_muni` (7 dígitos), validada por contrato `pandera`. Nenhum município é removido na etapa gold (5.570 → 5.570); 0 chaves duplicadas e 0 órfãs.
- Anonimização / pseudonimização: não necessária. Dos microdados de escolas são lidas só contagens e indicadores 0/1; nomes de escolas, endereços e demais colunas nem são carregados.
- Hash SHA-256 dos dados brutos: um por arquivo, em `data/bronze/<fonte>/<ano>/manifest.json`. Hash da base gold: `3eb86d80853a64da7c29146eb6d5f75686e83638b890142b1cf97e56eb5a71d3`. Os dados bronze nunca são alterados.

## 5. Usos
- Usos pretendidos: análise exploratória, tipologias, estudos espaciais.
- Usos desaconselhados: inferência causal, avaliação individual de escolas, alocação de recursos sem análise complementar.
- Riscos de viés conhecidos: anos de referência distintos entre fontes; IDEB ausente em municípios pequenos (possível viés de seleção); autodeclaração no Censo Escolar; falácia ecológica ao interpretar resultados municipais; municípios muito pequenos têm poucas escolas e indicadores instáveis. Lista completa em `reports/relatorio.md`.

## 6. Distribuição
- Licença e restrições: código sob MIT; dados públicos sob os termos de cada órgão (INEP, IBGE/IPEA).
- Onde está armazenado: não é versionado no Git (`data/` é ignorado). É reconstruído com `make reproduce`. `TODO(Luan Freitas): definir remote DVC, se os dados passarem a ser versionados.`

## 7. Manutenção
- Responsável: Luan Freitas (luan.mgf@gmail.com).
- Frequência de atualização: a cada novo ciclo do Censo Escolar/IDEB; basta atualizar os anos em `configs/config.yaml` e reexecutar `make reproduce`. As URLs do INEP mudam com frequência (`configs/data_sources.yaml`).
- Como atender pedidos de exclusão de titulares: não se aplica; a base não contém dados pessoais.

## 8. LGPD
- Base legal (art. 7 / art. 11): tratamento de dados públicos/anonimizados para estudos e pesquisa (art. 7º, IV e art. 12). Não há dado pessoal na base final.
- Prazo de retenção: sem prazo específico; derivados podem ser regenerados a qualquer momento a partir das fontes.
- Relatório de impacto (RIPD) necessário? Não — sem dado pessoal. Risco residual de reidentificação baixo; resultados são reportados por cluster e região, nunca por escola.
