"""Contratos de dados da camada silver (uma linha por município)."""

import pandera.polars as pa
import polars as pl

from constants.regions import REGIONS, UF_TO_REGION


def key_column() -> pa.Column:
    """Coluna-chave: código IBGE de 7 dígitos, único e não nulo."""
    return pa.Column(
        pl.Int64,
        checks=pa.Check.in_range(1_000_000, 9_999_999),
        unique=True,
        nullable=False,
    )


def share_column() -> pa.Column:
    """Proporção entre 0 e 1 (pode ser nula quando não há escolas informantes)."""
    return pa.Column(pl.Float64, checks=pa.Check.in_range(0.0, 1.0), nullable=True)


def ideb_column() -> pa.Column:
    """Nota do IDEB (escala de 0 a 10); nula quando o município não tem nota."""
    return pa.Column(pl.Float64, checks=pa.Check.in_range(0.0, 10.0), nullable=True)


def censo_columns(*, nullable_counts: bool = False) -> dict[str, pa.Column]:
    """Colunas agregadas do Censo Escolar.

    Parameters
    ----------
    nullable_counts : bool, optional
        Aceita nulos nas contagens (usado na camada gold, onde um município
        pode não ter escolas informantes), by default False.

    Returns
    -------
    dict[str, pa.Column]
        Definição das colunas.
    """
    return {
        "code_muni": key_column(),
        "n_schools": pa.Column(pl.Int64, checks=pa.Check.gt(0), nullable=nullable_counts),
        "enrollments": pa.Column(pl.Int64, checks=pa.Check.ge(0), nullable=nullable_counts),
        "teachers": pa.Column(pl.Int64, checks=pa.Check.ge(0), nullable=nullable_counts),
        "rural_share": share_column(),
        "municipal_network_share": share_column(),
        "internet_share": share_column(),
        "library_share": share_column(),
        "computer_lab_share": share_column(),
        "sports_court_share": share_column(),
        "water_network_share": share_column(),
        "sewage_network_share": share_column(),
        "electricity_network_share": share_column(),
        "students_per_teacher": pa.Column(
            pl.Float64, checks=pa.Check.in_range(0.0, 500.0), nullable=True
        ),
        "enrollments_per_school": pa.Column(
            pl.Float64, checks=pa.Check.in_range(0.0, 20_000.0), nullable=True
        ),
    }


def sidra_columns() -> dict[str, pa.Column]:
    """Colunas do IBGE; os intervalos detectam mapeamentos de variável errados."""
    return {
        "code_muni": key_column(),
        "population": pa.Column(
            pl.Float64, checks=pa.Check.in_range(1.0, 20_000_000.0), nullable=True
        ),
        "area_km2": pa.Column(pl.Float64, checks=pa.Check.in_range(0.1, 300_000.0), nullable=True),
        "population_density": pa.Column(
            pl.Float64, checks=pa.Check.in_range(0.0, 30_000.0), nullable=True
        ),
        "gdp_per_capita": pa.Column(
            pl.Float64, checks=pa.Check.in_range(0.0, 5_000_000.0), nullable=True
        ),
    }


def geo_columns() -> dict[str, pa.Column]:
    """Atributos não espaciais da malha municipal."""
    return {
        "code_muni": key_column(),
        "name_muni": pa.Column(pl.String, nullable=False),
        "abbrev_state": pa.Column(
            pl.String, checks=pa.Check.isin(sorted(UF_TO_REGION)), nullable=False
        ),
        "region": pa.Column(pl.String, checks=pa.Check.isin(list(REGIONS)), nullable=False),
    }


CENSO_SCHEMA = pa.DataFrameSchema(censo_columns(), strict=True, name="silver_censo_escolar")

IDEB_SCHEMA = pa.DataFrameSchema(
    {
        "code_muni": key_column(),
        "ideb_early_years": ideb_column(),
        "ideb_late_years": ideb_column(),
    },
    strict=True,
    name="silver_ideb",
)

SIDRA_SCHEMA = pa.DataFrameSchema(sidra_columns(), strict=True, name="silver_sidra")

GEO_SCHEMA = pa.DataFrameSchema(geo_columns(), strict=True, name="silver_geobr")
