"""Nomes de colunas brutas (INEP) e das tabelas derivadas (inglês)."""

KEY = "code_muni"  # código do município no IBGE, 7 dígitos

# Colunas booleanas (0/1) do Censo Escolar -> proporção de escolas com o recurso.
CENSO_FLAG_COLUMNS: dict[str, str] = {
    "IN_INTERNET": "internet_share",
    "IN_BIBLIOTECA": "library_share",
    "IN_LABORATORIO_INFORMATICA": "computer_lab_share",
    "IN_QUADRA_ESPORTES": "sports_court_share",
    "IN_AGUA_REDE_PUBLICA": "water_network_share",
    "IN_ESGOTO_REDE_PUBLICA": "sewage_network_share",
    "IN_ENERGIA_REDE_PUBLICA": "electricity_network_share",
}

# Colunas lidas do CSV de microdados (dicionário de dados do INEP).
CENSO_RAW_COLUMNS: tuple[str, ...] = (
    "CO_MUNICIPIO",
    "TP_SITUACAO_FUNCIONAMENTO",  # 1 = em atividade
    "TP_DEPENDENCIA",  # 1 federal, 2 estadual, 3 municipal, 4 privada
    "TP_LOCALIZACAO",  # 1 urbana, 2 rural
    "QT_MAT_BAS",  # matrículas da educação básica
    "QT_DOC_BAS",  # docentes da educação básica
    *CENSO_FLAG_COLUMNS,
)

CENSO_COLUMNS: tuple[str, ...] = (
    KEY,
    "n_schools",
    "enrollments",
    "teachers",
    "rural_share",
    "municipal_network_share",
    *CENSO_FLAG_COLUMNS.values(),
    "students_per_teacher",
    "enrollments_per_school",
)

IDEB_COLUMNS: tuple[str, ...] = (KEY, "ideb_early_years", "ideb_late_years")

SIDRA_COLUMNS: tuple[str, ...] = (
    KEY,
    "population",
    "area_km2",
    "population_density",
    "gdp_per_capita",
)

GEO_ATTRIBUTE_COLUMNS: tuple[str, ...] = (KEY, "name_muni", "abbrev_state", "region")
