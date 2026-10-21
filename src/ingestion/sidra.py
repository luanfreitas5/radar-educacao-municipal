"""Ingestão de tabelas da API SIDRA (IBGE)."""

from pathlib import Path
from typing import Literal

from config.paths import ProjectPaths
from config.settings import Settings
from ingestion.downloader import download_file
from ingestion.manifest import ManifestEntry

SOURCE = "sidra"
SidraName = Literal["population", "gdp"]
NAMES: tuple[SidraName, ...] = ("population", "gdp")


def _period(settings: Settings, name: SidraName) -> int:
    """Ano de referência da tabela, conforme ``reference`` na configuração."""
    return getattr(settings.reference, settings.data_sources.sidra_tables[name].reference)


def build_sidra_url(settings: Settings, name: SidraName) -> str:
    """Monta a URL da API SIDRA para todos os municípios (nível territorial n6).

    Parameters
    ----------
    settings : Settings
        Configuração validada.
    name : {"population", "gdp"}
        Tabela configurada em ``data_sources.sidra_tables``.

    Returns
    -------
    str
        URL no formato ``.../values/t/<tabela>/n6/all/v/<variáveis>/p/<ano>``.
    """
    table = settings.data_sources.sidra_tables[name]
    variables = ",".join(table.variables)
    base = settings.data_sources.sidra_base_url.rstrip("/")
    return f"{base}/t/{table.table}/n6/all/v/{variables}/p/{_period(settings, name)}"


def sidra_path(settings: Settings, paths: ProjectPaths, name: SidraName) -> Path:
    """Caminho do JSON bruto da tabela na camada bronze."""
    table = settings.data_sources.sidra_tables[name]
    period = _period(settings, name)
    return paths.bronze_dir(SOURCE, period) / f"{name}_t{table.table}_{period}.json"


def ingest_sidra(
    settings: Settings, paths: ProjectPaths, *, force: bool = False
) -> list[ManifestEntry]:
    """Baixa as tabelas SIDRA configuradas (população/área e PIB).

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
        Um registro de proveniência por tabela.
    """
    return [
        download_file(
            build_sidra_url(settings, name),
            sidra_path(settings, paths, name),
            timeout=settings.data_sources.request_timeout_seconds,
            force=force,
        )
        for name in NAMES
    ]
