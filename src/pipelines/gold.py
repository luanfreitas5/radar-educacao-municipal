"""Etapa 2b: silver -> gold (junção pelo código de 7 dígitos e integridade)."""

import json
import logging
from pathlib import Path

import polars as pl

from config.paths import ProjectPaths
from config.settings import Settings
from constants import files
from constants.columns import GEO_ATTRIBUTE_COLUMNS
from preprocessing.integration import build_municipality_table
from reporting.results import update_results
from schemas.gold import GOLD_SCHEMA
from utils.hashing import hash_file
from validation.contracts import validate_contract
from validation.integrity import assert_integrity, check_integrity

logger = logging.getLogger(__name__)


def run_gold(settings: Settings, paths: ProjectPaths) -> Path:
    """Integra as tabelas silver, valida a integridade e grava a base gold.

    O relatório de integridade é gravado **antes** de a falha ser levantada,
    para que uma base reprovada seja diagnosticável.

    Parameters
    ----------
    settings : Settings
        Configuração validada.
    paths : ProjectPaths
        Caminhos do projeto.

    Returns
    -------
    Path
        Arquivo Parquet da base municipal.

    Raises
    ------
    IntegrityError
        Se cobertura, duplicatas ou nulos violarem os limiares configurados.
    DataValidationError
        Se a base final violar o contrato da camada gold.
    """
    universe = pl.read_parquet(
        paths.silver / files.SILVER_GEOBR, columns=list(GEO_ATTRIBUTE_COLUMNS)
    )
    censo = pl.read_parquet(paths.silver / files.SILVER_CENSO)
    ideb = pl.read_parquet(paths.silver / files.SILVER_IDEB)
    sidra = pl.read_parquet(paths.silver / files.SILVER_SIDRA)

    municipalities = build_municipality_table(universe, censo, ideb, sidra)
    report = check_integrity(
        municipalities,
        {"censo_escolar": censo, "ideb": ideb, "sidra": sidra},
        settings.integrity,
    )
    paths.reports.mkdir(parents=True, exist_ok=True)
    (paths.reports / files.INTEGRITY_JSON).write_text(
        json.dumps(report.to_dict(), indent=2, ensure_ascii=False), encoding="utf-8"
    )
    assert_integrity(report)

    validate_contract(municipalities, GOLD_SCHEMA, "gold_municipalities")
    paths.gold.mkdir(parents=True, exist_ok=True)
    output = paths.gold / files.GOLD_MUNICIPALITIES
    municipalities.write_parquet(output)

    update_results(
        paths.reports / files.RESULTS_JSON,
        "integrity",
        {**report.to_dict(), "gold_sha256": hash_file(output)},
    )
    logger.info("Base gold gravada: %s (%d municípios)", output.name, municipalities.height)
    return output
