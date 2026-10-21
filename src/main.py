"""Orquestra o pipeline: ingestão -> silver -> gold -> clusters -> espacial -> relatório.

Uso
---
    uv run python src/main.py all
    uv run python src/main.py ingest --force
    uv run python src/main.py cluster --log-level DEBUG
"""

import argparse
import logging
from collections.abc import Callable, Sequence
from pathlib import Path

from config.logging import configure_logging
from config.paths import CONFIG_DIR, ProjectPaths, build_paths
from config.settings import Settings, load_settings
from exceptions import RadarError
from pipelines.clustering import run_clustering
from pipelines.gold import run_gold
from pipelines.ingestion import run_ingestion
from pipelines.report import run_report
from pipelines.silver import run_silver
from pipelines.spatial import run_spatial
from utils.seed import seed_everything

logger = logging.getLogger(__name__)

STAGES: tuple[str, ...] = ("ingest", "silver", "gold", "cluster", "spatial", "report")


def build_parser() -> argparse.ArgumentParser:
    """Cria o parser de linha de comando.

    Returns
    -------
    argparse.ArgumentParser
        Parser com a etapa (posicional) e as opções globais.
    """
    parser = argparse.ArgumentParser(
        prog="radar-educacao-municipal",
        description="Pipeline de tipologias e análise espacial da educação municipal.",
    )
    parser.add_argument(
        "stage",
        choices=(*STAGES, "all"),
        help="Etapa a executar; 'all' roda todas em sequência.",
    )
    parser.add_argument(
        "--config-dir", type=Path, default=CONFIG_DIR, help="Diretório dos YAML de configuração."
    )
    parser.add_argument(
        "--force", action="store_true", help="Na ingestão, ignora o cache e baixa novamente."
    )
    parser.add_argument(
        "--log-level",
        choices=("DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"),
        default=None,
        help="Sobrescreve o nível de log de configs/logging.yaml.",
    )
    return parser


def run_stage(stage: str, settings: Settings, paths: ProjectPaths, *, force: bool = False) -> None:
    """Executa uma etapa do pipeline.

    Parameters
    ----------
    stage : str
        Um valor de ``STAGES``.
    settings : Settings
        Configuração validada.
    paths : ProjectPaths
        Caminhos do projeto.
    force : bool, optional
        Repassado à ingestão, by default False.
    """
    runners: dict[str, Callable[[], object]] = {
        "ingest": lambda: run_ingestion(settings, paths, force=force),
        "silver": lambda: run_silver(settings, paths),
        "gold": lambda: run_gold(settings, paths),
        "cluster": lambda: run_clustering(settings, paths),
        "spatial": lambda: run_spatial(settings, paths),
        "report": lambda: run_report(paths),
    }
    logger.info("Iniciando etapa: %s", stage)
    runners[stage]()
    logger.info("Etapa concluída: %s", stage)


def run(argv: Sequence[str] | None = None) -> int:
    """Ponto de entrada testável: interpreta argumentos e executa as etapas.

    Parameters
    ----------
    argv : Sequence[str] or None, optional
        Argumentos; ``None`` usa ``sys.argv``.

    Returns
    -------
    int
        Código de saída (0 = sucesso, 1 = falha esperada do pipeline).
    """
    args = build_parser().parse_args(argv)
    try:
        settings = load_settings(args.config_dir)
        paths = build_paths(settings.paths)
        paths.ensure_directories()
        configure_logging(args.log_level or settings.logging.level, paths.logs)
        seed_everything(settings.project.random_seed)
        stages = STAGES if args.stage == "all" else (args.stage,)
        for stage in stages:
            run_stage(stage, settings, paths, force=args.force)
    except RadarError as exc:
        logger.error("Pipeline interrompido: %s", exc)  # noqa: TRY400 - erro de domínio esperado, sem traceback
        return 1
    return 0


def main() -> None:
    """Executa o pipeline e encerra o processo com o código de saída."""
    raise SystemExit(run())


if __name__ == "__main__":
    main()
