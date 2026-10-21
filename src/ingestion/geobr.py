"""Ingestão da malha municipal via pacote ``geobr`` (IBGE/IPEA)."""

import logging
from pathlib import Path

from config.paths import ProjectPaths
from config.settings import Settings
from ingestion.manifest import ManifestEntry, read_manifest, register_file
from utils.hashing import hash_file

logger = logging.getLogger(__name__)

SOURCE = "geobr"


def geobr_path(settings: Settings, paths: ProjectPaths) -> Path:
    """Caminho do GeoParquet da malha municipal na camada bronze."""
    year = settings.reference.geobr
    return paths.bronze_dir(SOURCE, year) / f"municipios_{year}.parquet"


def ingest_geobr(settings: Settings, paths: ProjectPaths, *, force: bool = False) -> ManifestEntry:
    """Baixa a malha municipal e a grava como GeoParquet na camada bronze.

    Parameters
    ----------
    settings : Settings
        Configuração validada.
    paths : ProjectPaths
        Caminhos do projeto.
    force : bool, optional
        Ignora o cache local, by default False.

    Returns
    -------
    ManifestEntry
        Registro de proveniência do arquivo.
    """
    destination = geobr_path(settings, paths)
    destination.parent.mkdir(parents=True, exist_ok=True)

    if destination.exists() and not force:
        cached = read_manifest(destination.parent).get(destination.name)
        if cached is not None and cached.sha256 == hash_file(destination):
            logger.info("Cache válido, download ignorado: %s", destination.name)
            return cached

    import geobr  # importação sob demanda: o pacote é lento para carregar  # noqa: PLC0415

    year = settings.reference.geobr
    logger.info("Baixando a malha municipal do geobr (ano %s)", year)
    municipalities = geobr.read_municipality(code_muni="all", year=year, simplified=True)
    municipalities.to_parquet(destination)  # pyright: ignore[reportAttributeAccessIssue]
    return register_file(destination, f"geobr.read_municipality(code_muni='all', year={year})")
