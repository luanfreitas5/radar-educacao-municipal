"""Centraliza os caminhos do projeto com ``pathlib.Path``."""

from dataclasses import dataclass
from pathlib import Path

from pydantic import BaseModel, ConfigDict

ROOT = Path(__file__).resolve().parents[2]
CONFIG_DIR = ROOT / "configs"


class PathsConfig(BaseModel):
    """Caminhos relativos à raiz do repositório, lidos de ``configs/paths.yaml``."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    bronze: str
    silver: str
    gold: str
    staging: str
    reports: str
    figures: str
    logs: str


@dataclass(frozen=True)
class ProjectPaths:
    """Caminhos absolutos resolvidos das camadas e saídas do projeto."""

    root: Path
    bronze: Path
    silver: Path
    gold: Path
    staging: Path
    reports: Path
    figures: Path
    logs: Path

    def bronze_dir(self, source: str, reference: int | str) -> Path:
        """Retorna o diretório de snapshot de uma fonte na camada bronze.

        Parameters
        ----------
        source : str
            Nome da fonte (ex.: ``"censo_escolar"``).
        reference : int or str
            Ano ou identificador de referência do snapshot.

        Returns
        -------
        Path
            ``data/bronze/<source>/<reference>``.
        """
        return self.bronze / source / str(reference)

    def ensure_directories(self) -> None:
        """Cria os diretórios de trabalho caso ainda não existam."""
        for directory in (
            self.bronze,
            self.silver,
            self.gold,
            self.staging,
            self.reports,
            self.figures,
            self.logs,
        ):
            directory.mkdir(parents=True, exist_ok=True)


def build_paths(config: PathsConfig, root: Path = ROOT) -> ProjectPaths:
    """Resolve os caminhos relativos da configuração contra a raiz do projeto.

    Parameters
    ----------
    config : PathsConfig
        Caminhos relativos validados.
    root : Path, optional
        Raiz do repositório, by default ``ROOT``.

    Returns
    -------
    ProjectPaths
        Caminhos absolutos.
    """
    return ProjectPaths(
        root=root,
        bronze=root / config.bronze,
        silver=root / config.silver,
        gold=root / config.gold,
        staging=root / config.staging,
        reports=root / config.reports,
        figures=root / config.figures,
        logs=root / config.logs,
    )
