# Fontes de dados

| Fonte | O que usamos | Granularidade original | Observações |
|---|---|---|---|
| Censo Escolar (INEP) | infraestrutura, matrículas e docentes da educação básica | escola | CSV `;` em ISO-8859-1; apenas escolas em atividade |
| IDEB (INEP) | nota observada, anos iniciais e finais, rede pública | município | planilha com preâmbulo; `-` = sem nota |
| SIDRA (IBGE) | população e área (Censo 2022, tabela 4714); PIB (tabela 5938) | município | PIB e população têm anos diferentes |
| geobr (IBGE/IPEA) | malha municipal e UF | município | CRS SIRGAS 2000 (EPSG:4674) |

## Cuidados

- As URLs do INEP mudam com frequência: ficam em `configs/data_sources.yaml`.
- Os nomes das colunas do Censo Escolar seguem o dicionário de dados do ano de referência;
  se mudarem, `scan_schools` falha listando as colunas ausentes.
- Os códigos das variáveis SIDRA (`93`, `614`, `37`) são validados indiretamente por
  intervalos plausíveis no schema silver (população, área, densidade e PIB per capita).
- **Privacidade (LGPD):** o pipeline usa apenas indicadores agregados por escola/município;
  não há dados pessoais. Veja o [datasheet](https://github.com/luanfreitas5/radar-educacao-municipal/blob/main/reports/datasheets/datasheet_base_municipal.md).
