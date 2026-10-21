"""Ingestão das planilhas do IDEB por município (INEP)."""

from pathlib import Path
from typing import Literal
from urllib.parse import urlparse

from config.paths import ProjectPaths
from config.settings import Settings
from ingestion.downloader import download_file
from ingestion.manifest import ManifestEntry

SOURCE = "ideb"
IdebStage = Literal["early_years", "late_years"]
STAGES: tuple[IdebStage, ...] = ("early_years", "late_years")


def ideb_url(settings: Settings, stage: IdebStage) -> str:
    """Monta a URL da planilha do IDEB (anos iniciais ou finais)."""
    return settings.data_sources.ideb_urls[stage].format(year=settings.reference.ideb)


def ideb_path(settings: Settings, paths: ProjectPaths, stage: IdebStage) -> Path:
    """Caminho da planilha do IDEB na camada bronze."""
    filename = Path(urlparse(ideb_url(settings, stage)).path).name
    return paths.bronze_dir(SOURCE, settings.reference.ideb) / filename


def ingest_ideb(
    settings: Settings, paths: ProjectPaths, *, force: bool = False
) -> list[ManifestEntry]:
    """Baixa as planilhas do IDEB (anos iniciais e finais) por município.

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
    list[ManifestEntry]
        Um registro de proveniência por planilha.
    """
    return [
        download_file(
            ideb_url(settings, stage),
            ideb_path(settings, paths, stage),
            timeout=settings.data_sources.request_timeout_seconds,
            force=force,
        )
        for stage in STAGES
    ]
