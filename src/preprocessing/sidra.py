"""Conversão do JSON da API SIDRA em colunas por município."""

import json
from collections.abc import Mapping
from pathlib import Path

import polars as pl

from constants.columns import KEY
from exceptions import DataValidationError

THOUSAND = 1000.0


def read_sidra_records(path: Path) -> list[dict[str, str]]:
    """Lê o JSON bruto da API SIDRA (lista de registros).

    Parameters
    ----------
    path : Path
        JSON na camada bronze.

    Returns
    -------
    list[dict[str, str]]
        Registros; o primeiro contém os rótulos das colunas.

    Raises
    ------
    DataValidationError
        Se o conteúdo não for uma lista de objetos.
    """
    records = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(records, list) or not all(isinstance(item, dict) for item in records):
        raise DataValidationError(f"Resposta inesperada da API SIDRA em {path.name}")
    return records


def _find_key(header: Mapping[str, str], prefix: str) -> str:
    """Acha a chave (ex.: ``D1C``) cujo rótulo no cabeçalho começa com ``prefix``."""
    for key, label in header.items():
        if label.strip().lower().startswith(prefix) and "cód" in label.lower():
            return key
    raise DataValidationError(f"Coluna '{prefix}' não encontrada no cabeçalho da resposta SIDRA")


def parse_sidra_records(
    records: list[dict[str, str]], variable_names: Mapping[str, str]
) -> pl.DataFrame:
    """Converte registros SIDRA em uma tabela larga (uma linha por município).

    O formato SIDRA traz um registro de cabeçalho (rótulos das colunas) e, depois,
    um registro por (município, variável). As colunas de município e variável são
    localizadas pelos rótulos do cabeçalho, e não por posição.

    Parameters
    ----------
    records : list[dict[str, str]]
        Resposta da API (primeiro item = cabeçalho).
    variable_names : Mapping[str, str]
        Código da variável SIDRA -> nome da coluna de saída.

    Returns
    -------
    pl.DataFrame
        ``code_muni`` e uma coluna por variável (Float64); ``"..."``, ``"-"`` e
        ``"X"`` viram nulo.

    Raises
    ------
    DataValidationError
        Se a resposta for vazia, sem os rótulos esperados, ou faltar variável.
    """
    if len(records) < 2:
        raise DataValidationError("Resposta da API SIDRA vazia")
    header, rows = records[0], records[1:]
    municipality_key = _find_key(header, "munic")
    variable_key = _find_key(header, "variável")

    long = pl.DataFrame(rows).select(
        pl.col(municipality_key).cast(pl.Int64, strict=False).alias(KEY),
        pl.col(variable_key).alias("variable"),
        pl.col("V").cast(pl.Float64, strict=False).alias("value"),
    )
    wide = (
        long.filter(pl.col("variable").is_in(list(variable_names)))
        .with_columns(pl.col("variable").replace(dict(variable_names)))
        .pivot(on="variable", index=KEY, values="value")
    )
    missing = set(variable_names.values()) - set(wide.columns)
    if missing:
        raise DataValidationError(f"Variáveis ausentes na resposta SIDRA: {sorted(missing)}")
    return wide


def build_sidra_silver(population: pl.DataFrame, gdp: pl.DataFrame) -> pl.DataFrame:
    """Calcula densidade demográfica e PIB per capita por município.

    O PIB (ano ``sidra_gdp``) é dividido pela população do Censo
    (ano ``sidra_population``): os anos diferem e isso é uma limitação conhecida.

    Parameters
    ----------
    population : pl.DataFrame
        Tabela com ``population`` e ``area_km2``.
    gdp : pl.DataFrame
        Tabela com ``gdp_thousand_brl`` (mil reais correntes).

    Returns
    -------
    pl.DataFrame
        ``code_muni``, ``population``, ``area_km2``, ``population_density`` e
        ``gdp_per_capita`` (R$ por habitante).
    """
    return (
        population.join(gdp, on=KEY, how="left")
        .with_columns(
            (pl.col("population") / pl.col("area_km2")).alias("population_density"),
            (pl.col("gdp_thousand_brl") * THOUSAND / pl.col("population")).alias("gdp_per_capita"),
        )
        .select(KEY, "population", "area_km2", "population_density", "gdp_per_capita")
        .sort(KEY)
    )
