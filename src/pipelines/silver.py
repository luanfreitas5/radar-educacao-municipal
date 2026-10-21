"""Etapa 2a: bronze -> silver (limpeza, agregação por município e contratos)."""

import logging
from pathlib import Path

import polars as pl

from config.paths import ProjectPaths
from config.settings import Settings
from constants import files
from ingestion.censo_escolar import censo_escolar_zip_path
from ingestion.geobr import geobr_path
from ingestion.ideb import STAGES, ideb_path
from ingestion.sidra import NAMES, sidra_path
from preprocessing.censo import build_censo_silver
from preprocessing.geo import build_geo_silver, extract_geo_attributes
from preprocessing.ideb import build_ideb_silver, parse_ideb_sheet, read_ideb_sheet
from preprocessing.sidra import build_sidra_silver, parse_sidra_records, read_sidra_records
from schemas.silver import CENSO_SCHEMA, GEO_SCHEMA, IDEB_SCHEMA, SIDRA_SCHEMA
from validation.contracts import validate_contract

logger = logging.getLogger(__name__)

_IDEB_OUTPUT = {"early_years": "ideb_early_years", "late_years": "ideb_late_years"}


def _build_ideb(settings: Settings, paths: ProjectPaths) -> pl.DataFrame:
    """Lê as duas planilhas do IDEB e combina em uma tabela por município."""
    parsed = {
        stage: parse_ideb_sheet(
            read_ideb_sheet(ideb_path(settings, paths, stage), paths.staging),
            settings.reference.ideb,
            settings.data_sources.ideb_network,
            _IDEB_OUTPUT[stage],
        )
        for stage in STAGES
    }
    return build_ideb_silver(parsed["early_years"], parsed["late_years"])


def _build_sidra(settings: Settings, paths: ProjectPaths) -> pl.DataFrame:
    """Converte as tabelas SIDRA e calcula densidade e PIB per capita."""
    tables = {
        name: parse_sidra_records(
            read_sidra_records(sidra_path(settings, paths, name)),
            settings.data_sources.sidra_tables[name].variables,
        )
        for name in NAMES
    }
    return build_sidra_silver(tables["population"], tables["gdp"])


def run_silver(settings: Settings, paths: ProjectPaths) -> dict[str, Path]:
    """Gera e valida as quatro tabelas silver a partir do bronze.

    Parameters
    ----------
    settings : Settings
        Configuração validada.
    paths : ProjectPaths
        Caminhos do projeto.

    Returns
    -------
    dict[str, Path]
        Nome da tabela -> arquivo Parquet gerado.

    Raises
    ------
    DataValidationError
        Se alguma tabela violar o contrato de dados.
    """
    paths.silver.mkdir(parents=True, exist_ok=True)
    outputs: dict[str, Path] = {}

    censo = validate_contract(
        build_censo_silver(censo_escolar_zip_path(settings, paths), paths.staging),
        CENSO_SCHEMA,
        "silver_censo_escolar",
    )
    outputs["censo_escolar"] = paths.silver / files.SILVER_CENSO
    censo.write_parquet(outputs["censo_escolar"])

    ideb = validate_contract(_build_ideb(settings, paths), IDEB_SCHEMA, "silver_ideb")
    outputs["ideb"] = paths.silver / files.SILVER_IDEB
    ideb.write_parquet(outputs["ideb"])

    sidra = validate_contract(_build_sidra(settings, paths), SIDRA_SCHEMA, "silver_sidra")
    outputs["sidra"] = paths.silver / files.SILVER_SIDRA
    sidra.write_parquet(outputs["sidra"])

    geodata = build_geo_silver(geobr_path(settings, paths))
    validate_contract(extract_geo_attributes(geodata), GEO_SCHEMA, "silver_geobr")
    outputs["geobr"] = paths.silver / files.SILVER_GEOBR
    geodata.to_parquet(outputs["geobr"])

    for name, path in outputs.items():
        logger.info("Silver gravada: %s -> %s", name, path.name)
    return outputs
