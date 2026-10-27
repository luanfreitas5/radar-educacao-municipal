"""Barra de progresso padrão do projeto (rich)."""

from rich.progress import (
    BarColumn,
    MofNCompleteColumn,
    Progress,
    SpinnerColumn,
    TaskProgressColumn,
    TextColumn,
    TimeElapsedColumn,
    TimeRemainingColumn,
)

from config.logging import CONSOLE


def create_progress() -> Progress:
    """Cria a barra de progresso com as colunas padronizadas do projeto.

    Returns
    -------
    Progress
        Instância pronta para uso como gerenciador de contexto.
    """
    return Progress(
        SpinnerColumn(),
        TextColumn("[bold blue]{task.description}"),
        BarColumn(),
        MofNCompleteColumn(),
        TaskProgressColumn(),
        TimeElapsedColumn(),
        TimeRemainingColumn(),
        console=CONSOLE,  # mesmo console do RichHandler: logs saem acima da barra
    )
