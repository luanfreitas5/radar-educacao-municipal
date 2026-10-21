"""Configura o logging com handler rich no console e arquivo com rotação diária."""

import logging
from logging.handlers import TimedRotatingFileHandler
from pathlib import Path

from rich.logging import RichHandler

FILE_FORMAT = "%(asctime)s \t %(levelname)s \t %(name)s \t %(message)s"


def _rotated_name(default_name: str) -> str:
    """Converte ``log.log.2026-10-18`` em ``log_2026-10-18.log``."""
    path = Path(default_name)
    date_suffix = path.name.rsplit(".", 1)[-1]
    return str(path.with_name(f"log_{date_suffix}.log"))


def configure_logging(level: str = "INFO", log_dir: Path | None = None) -> None:
    """Configura o logger raiz com console (rich) e, opcionalmente, arquivo.

    A chamada é idempotente: handlers anteriores são removidos antes de
    adicionar os novos. Mensagens de log do projeto são escritas em pt-BR e
    nunca devem conter dados pessoais ou segredos.

    Parameters
    ----------
    level : str, optional
        Nível de log (``"DEBUG"``, ``"INFO"`` ...), by default ``"INFO"``.
    log_dir : Path or None, optional
        Diretório dos arquivos ``log_AAAA-MM-DD.log``; ``None`` desativa o
        arquivo, by default None.
    """
    root_logger = logging.getLogger()
    for handler in root_logger.handlers.copy():
        root_logger.removeHandler(handler)
        handler.close()

    root_logger.setLevel(level)
    console = RichHandler(rich_tracebacks=True, show_path=False, markup=False)
    console.setFormatter(logging.Formatter("%(name)s - %(message)s"))
    root_logger.addHandler(console)

    if log_dir is not None:
        log_dir.mkdir(parents=True, exist_ok=True)
        file_handler = TimedRotatingFileHandler(
            log_dir / "log.log",
            when="midnight",
            backupCount=30,
            encoding="utf-8",
            delay=True,
        )
        file_handler.namer = _rotated_name
        file_handler.setFormatter(logging.Formatter(FILE_FORMAT))
        root_logger.addHandler(file_handler)
