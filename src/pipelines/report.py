"""Etapa 5: relatório final em Markdown."""

import logging
from pathlib import Path

import polars as pl

from config.paths import ProjectPaths
from constants import files
from reporting.report import build_report
from reporting.results import load_results

logger = logging.getLogger(__name__)


def run_report(paths: ProjectPaths) -> Path:
    """Gera ``reports/relatorio.md`` a partir dos resultados das etapas anteriores.

    Parameters
    ----------
    paths : ProjectPaths
        Caminhos do projeto.

    Returns
    -------
    Path
        Arquivo Markdown gerado.
    """
    results = load_results(paths.reports / files.RESULTS_JSON)
    profile_path = paths.reports / files.CLUSTER_PROFILE
    cohesion_path = paths.reports / "cluster_cohesion.parquet"
    profile = pl.read_parquet(profile_path) if profile_path.is_file() else pl.DataFrame()
    cohesion = pl.read_parquet(cohesion_path) if cohesion_path.is_file() else pl.DataFrame()

    output = paths.reports / files.REPORT_MARKDOWN
    output.write_text(build_report(results, profile, cohesion), encoding="utf-8")
    logger.info("Relatório gerado: %s", output)
    return output
