"""Nomes dos arquivos produzidos em cada camada do pipeline."""

# Silver
SILVER_CENSO = "censo_escolar_municipio.parquet"
SILVER_IDEB = "ideb_municipio.parquet"
SILVER_SIDRA = "sidra_municipio.parquet"
SILVER_GEOBR = "geobr_municipio.parquet"  # GeoParquet (inclui geometria)

# Gold
GOLD_MUNICIPALITIES = "municipios.parquet"
GOLD_CLUSTERS = "municipios_clusters.parquet"
GOLD_LISA = "municipios_lisa.parquet"

# Relatórios
RESULTS_JSON = "results.json"
INTEGRITY_JSON = "integrity_report.json"
CLUSTER_PROFILE = "cluster_profile.parquet"
REPORT_MARKDOWN = "relatorio.md"
