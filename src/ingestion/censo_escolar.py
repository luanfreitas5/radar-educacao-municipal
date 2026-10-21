"""Ingestão dos microdados do Censo Escolar (INEP)."""

from pathlib import Path
from urllib.parse import urlparse

from config.paths import ProjectPaths
from config.settings import Settings
from ingestion.downloader import download_file
from ingestion.manifest import ManifestEntry

SOURCE = "censo_escolar"


def censo_escolar_url(settings: Settings) -> str:
    """Monta a URL do arquivo ``.zip`` do ano de referência."""
    return settings.data_sources.censo_escolar_url.format(year=settings.reference.censo_escolar)


def censo_escolar_zip_path(settings: Settings, paths: ProjectPaths) -> Path:
    """Caminho do ``.zip`` do Censo Escolar na camada bronze."""
    filename = Path(urlparse(censo_escolar_url(settings)).path).name
    return paths.bronze_dir(SOURCE, settings.reference.censo_escolar) / filename


def ingest_censo_escolar(
    settings: Settings, paths: ProjectPaths, *, force: bool = False
) -> ManifestEntry:
    """Baixa os microdados do Censo Escolar do ano de referência.

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
    return download_file(
        censo_escolar_url(settings),
        censo_escolar_zip_path(settings, paths),
        timeout=settings.data_sources.request_timeout_seconds,
        force=force,
    )
