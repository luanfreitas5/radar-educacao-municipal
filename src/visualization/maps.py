"""Mapas coropléticos: clusters e LISA."""

import geopandas as gpd
import matplotlib.pyplot as plt
from matplotlib.figure import Figure
from matplotlib.patches import Patch

from visualization.theme import LISA_COLORS, cluster_colors


def plot_cluster_map(geodata: gpd.GeoDataFrame, cluster_column: str = "cluster") -> Figure:
    """Mapa dos municípios coloridos pela tipologia (cluster).

    Parameters
    ----------
    geodata : gpd.GeoDataFrame
        Municípios com geometria e coluna de cluster (nula = sem cluster).
    cluster_column : str, optional
        Nome da coluna de cluster, by default ``"cluster"``.

    Returns
    -------
    Figure
        Figura com o mapa e a legenda.
    """
    fig, ax = plt.subplots(figsize=(9, 9))
    n_clusters = int(geodata[cluster_column].max()) + 1
    colors = cluster_colors(n_clusters)
    geodata.plot(ax=ax, color="#d9d9d9", linewidth=0)
    for cluster in range(n_clusters):
        subset = geodata[geodata[cluster_column] == cluster]
        subset.plot(ax=ax, color=colors[cluster], linewidth=0)
    ax.legend(
        handles=[Patch(color=colors[c], label=f"Cluster {c}") for c in range(n_clusters)]
        + [Patch(color="#d9d9d9", label="Sem classificação")],
        loc="lower left",
        title="Tipologia",
    )
    ax.set_title("Tipologias de municípios")
    ax.set_axis_off()
    return fig


def plot_lisa_map(geodata: gpd.GeoDataFrame, class_column: str, title: str) -> Figure:
    """Mapa de clusters LISA (Alto-Alto, Baixo-Baixo, outliers espaciais).

    Parameters
    ----------
    geodata : gpd.GeoDataFrame
        Municípios com geometria e a coluna de classe LISA.
    class_column : str
        Coluna com os rótulos de ``LISA_COLORS`` (nulo = sem dado).
    title : str
        Título do mapa.

    Returns
    -------
    Figure
        Figura com o mapa e a legenda.
    """
    fig, ax = plt.subplots(figsize=(9, 9))
    colors = geodata[class_column].map(LISA_COLORS).fillna("#ffffff")
    geodata.plot(ax=ax, color=colors, linewidth=0)
    ax.legend(
        handles=[Patch(color=color, label=label) for label, color in LISA_COLORS.items()],
        loc="lower left",
        title="Classe LISA",
    )
    ax.set_title(title)
    ax.set_axis_off()
    return fig
