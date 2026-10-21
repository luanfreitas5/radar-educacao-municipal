"""Gráficos da clusterização: seleção de k, UMAP e perfil."""

import matplotlib.pyplot as plt
import numpy as np
import polars as pl
import seaborn as sns
from matplotlib.figure import Figure

from visualization.theme import cluster_colors


def plot_k_selection(selection: pl.DataFrame, chosen_k: int) -> Figure:
    """Mostra silhouette e inércia por número de clusters.

    Parameters
    ----------
    selection : pl.DataFrame
        Colunas ``k``, ``inertia`` e ``silhouette``.
    chosen_k : int
        k escolhido (destacado com linha vertical).

    Returns
    -------
    Figure
        Figura com dois painéis.
    """
    fig, (ax_silhouette, ax_inertia) = plt.subplots(1, 2, figsize=(11, 4))
    ax_silhouette.plot(selection["k"], selection["silhouette"], marker="o")
    ax_silhouette.set_title("Silhouette por número de clusters")
    ax_silhouette.set_ylabel("Silhouette médio")
    ax_inertia.plot(selection["k"], selection["inertia"], marker="o")
    ax_inertia.set_title("Inércia por número de clusters")
    ax_inertia.set_ylabel("Soma dos quadrados intra-cluster")
    for axis in (ax_silhouette, ax_inertia):
        axis.axvline(chosen_k, color="gray", linestyle="--", label=f"k = {chosen_k}")
        axis.set_xlabel("Número de clusters (k)")
        axis.legend()
    return fig


def plot_umap_clusters(embedding: np.ndarray, labels: np.ndarray) -> Figure:
    """Dispersão da projeção UMAP colorida por cluster.

    Parameters
    ----------
    embedding : np.ndarray
        Matriz ``(n, 2)`` com as coordenadas.
    labels : np.ndarray
        Rótulo de cluster de cada ponto.

    Returns
    -------
    Figure
        Figura com a projeção.
    """
    fig, ax = plt.subplots(figsize=(8, 6.5))
    colors = cluster_colors(int(labels.max()) + 1)
    for cluster in np.unique(labels):
        points = embedding[labels == cluster]
        ax.scatter(
            points[:, 0],
            points[:, 1],
            s=6,
            alpha=0.6,
            color=colors[int(cluster)],
            label=f"Cluster {cluster}",
        )
    ax.set_title("Projeção UMAP dos municípios (apenas visualização)")
    ax.set_xlabel("UMAP 1 (adimensional)")
    ax.set_ylabel("UMAP 2 (adimensional)")
    ax.legend(markerscale=3, title="Tipologia")
    return fig


def plot_cluster_profile(zscores: pl.DataFrame) -> Figure:
    """Mapa de calor da mediana de cada variável por cluster, em z-scores.

    Parameters
    ----------
    zscores : pl.DataFrame
        Saída de ``compute_cluster_zscores``.

    Returns
    -------
    Figure
        Mapa de calor divergente centrado em zero.
    """
    pandas_frame = zscores.to_pandas().set_index("cluster")
    fig, ax = plt.subplots(figsize=(11, 0.6 * len(pandas_frame) + 3))
    sns.heatmap(
        pandas_frame,
        cmap="RdBu_r",
        center=0,
        annot=True,
        fmt=".1f",
        linewidths=0.5,
        cbar_kws={"label": "Mediana do cluster (desvios-padrão da média geral)"},
        ax=ax,
    )
    ax.set_title("Perfil dos clusters")
    ax.set_xlabel("Variável")
    ax.set_ylabel("Cluster")
    plt.setp(ax.get_xticklabels(), rotation=45, ha="right")
    return fig
