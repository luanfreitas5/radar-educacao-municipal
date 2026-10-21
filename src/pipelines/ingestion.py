"""Etapa 1: ingestão das fontes para a camada bronze."""

import logging
from collections.abc import Callable

from config.paths import ProjectPaths
from config.settings import Settings
from ingestion.censo_escolar import ingest_censo_escolar
from ingestion.geobr import ingest_geobr
from ingestion.ideb import ingest_ideb
from ingestion.manifest import ManifestEntry
from ingestion.sidra import ingest_sidra
from utils.progress import create_progress

logger = logging.getLogger(__name__)


def run_ingestion(
    settings: Settings, paths: ProjectPaths, *, force: bool = False
) -> list[ManifestEntry]:
    """Baixa todas as fontes (idempotente: usa o cache quando o hash confere).

    Parameters
    ----------
    settings : Settings
        Configuração validada.
    paths : ProjectPaths
        Caminhos do projeto.
    force : bool, optional
        Ignora o cache e baixa novamente, by default False.

    Returns
    -------
    list[ManifestEntry]
        Registros de proveniência de todos os arquivos.
    """
    steps: list[tuple[str, Callable[[], ManifestEntry | list[ManifestEntry]]]] = [
        ("Censo Escolar (INEP)", lambda: ingest_censo_escolar(settings, paths, force=force)),
        ("IDEB (INEP)", lambda: ingest_ideb(settings, paths, force=force)),
        ("SIDRA (IBGE)", lambda: ingest_sidra(settings, paths, force=force)),
        ("Malha municipal (geobr)", lambda: ingest_geobr(settings, paths, force=force)),
    ]
    entries: list[ManifestEntry] = []
    with create_progress() as progress:
        task = progress.add_task("Ingestão", total=len(steps))
        for description, step in steps:
            progress.update(task, description=f"Ingestão: {description}")
            result = step()
            entries.extend(result if isinstance(result, list) else [result])
            progress.advance(task)
    for entry in entries:
        logger.info("Bronze: %s (sha256 %s…)", entry.filename, entry.sha256[:12])
    return entries
