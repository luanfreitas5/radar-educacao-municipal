"""Tema visual compartilhado e salvamento de figuras."""

from pathlib import Path

import matplotlib.pyplot as plt
import seaborn as sns
from matplotlib.figure import Figure

from constants.regions import LISA_NOT_SIGNIFICANT

LISA_COLORS: dict[str, str] = {
    "Alto-Alto": "#b2182b",
    "Baixo-Baixo": "#2166ac",
    "Baixo-Alto": "#92c5de",
    "Alto-Baixo": "#f4a582",
    LISA_NOT_SIGNIFICANT: "#d9d9d9",
}

CLUSTER_PALETTE_NAME = "colorblind"


def configure_theme() -> None:
    """Aplica o estilo padrão (seaborn, fonte e resolução) a todas as figuras."""
    sns.set_theme(style="whitegrid", context="notebook", palette=CLUSTER_PALETTE_NAME)
    plt.rcParams["figure.dpi"] = 120


def cluster_colors(n_clusters: int) -> list[tuple[float, float, float]]:
    """Cores categóricas (daltonismo-amigáveis) para os clusters.

    Parameters
    ----------
    n_clusters : int
        Número de clusters.

    Returns
    -------
    list[tuple[float, float, float]]
        Uma cor RGB por cluster.
    """
    return list(sns.color_palette(CLUSTER_PALETTE_NAME, n_clusters))


def save_figure(fig: Figure, name: str, figures_dir: Path) -> list[Path]:
    """Salva a figura em PNG (300 dpi) e SVG e a fecha.

    Parameters
    ----------
    fig : Figure
        Figura do matplotlib.
    name : str
        Nome-base do arquivo, sem extensão.
    figures_dir : Path
        Diretório de saída (criado se necessário).

    Returns
    -------
    list[Path]
        Caminhos dos arquivos gerados.
    """
    figures_dir.mkdir(parents=True, exist_ok=True)
    fig.tight_layout()
    outputs = [figures_dir / f"{name}.png", figures_dir / f"{name}.svg"]
    fig.savefig(outputs[0], dpi=300)
    fig.savefig(outputs[1])
    plt.close(fig)
    return outputs
