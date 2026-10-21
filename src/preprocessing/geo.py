"""Leitura da malha municipal e atributos básicos."""

from pathlib import Path

import geopandas as gpd
import polars as pl

from constants.columns import GEO_ATTRIBUTE_COLUMNS, KEY
from constants.regions import UF_TO_REGION
from exceptions import DataValidationError

REQUIRED_COLUMNS = (KEY, "name_muni", "abbrev_state", "geometry")


def build_geo_silver(path: Path) -> gpd.GeoDataFrame:
    """Lê o GeoParquet do bronze, tipa a chave e adiciona a região do IBGE.

    Parameters
    ----------
    path : Path
        GeoParquet da malha municipal na camada bronze.

    Returns
    -------
    gpd.GeoDataFrame
        ``code_muni`` (Int64), ``name_muni``, ``abbrev_state``, ``region`` e
        geometria, preservando o CRS original (SIRGAS 2000).

    Raises
    ------
    DataValidationError
        Se faltarem colunas esperadas da malha.
    """
    municipalities = gpd.read_parquet(path)
    missing = set(REQUIRED_COLUMNS) - set(municipalities.columns)
    if missing:
        raise DataValidationError(f"Colunas ausentes na malha do geobr: {sorted(missing)}")
    silver = municipalities.loc[:, list(REQUIRED_COLUMNS)].copy()
    silver[KEY] = silver[KEY].astype("int64")
    silver["region"] = silver["abbrev_state"].map(UF_TO_REGION)
    return silver.sort_values(KEY).reset_index(drop=True)


def extract_geo_attributes(municipalities: gpd.GeoDataFrame) -> pl.DataFrame:
    """Descarta a geometria e devolve os atributos como ``pl.DataFrame``.

    Parameters
    ----------
    municipalities : gpd.GeoDataFrame
        Saída de :func:`build_geo_silver`.

    Returns
    -------
    pl.DataFrame
        Colunas de ``GEO_ATTRIBUTE_COLUMNS``.
    """
    attributes = municipalities.loc[:, list(GEO_ATTRIBUTE_COLUMNS)]
    return pl.from_pandas(attributes.reset_index(drop=True))
