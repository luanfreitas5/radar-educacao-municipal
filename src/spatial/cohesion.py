"""Coesão espacial dos clusters: vizinhos no mesmo cluster versus o acaso."""

import numpy as np
import polars as pl
from libpysal.weights import W


def compute_cluster_cohesion(labels: np.ndarray, weights: W) -> pl.DataFrame:
    """Compara a fração observada de vizinhos no mesmo cluster com a esperada ao acaso.

    Para cada município, mede-se a fração de vizinhos Queen que pertencem ao seu
    próprio cluster. Sob distribuição espacial aleatória, essa fração esperada é
    a participação do cluster no total. Razão > 1 indica que o cluster forma
    manchas contíguas (tipologia com dimensão territorial).

    Parameters
    ----------
    labels : np.ndarray
        Rótulo de cluster de cada município, alinhado às linhas de ``weights``.
    weights : W
        Matriz de vizinhança sem ilhas.

    Returns
    -------
    pl.DataFrame
        Colunas ``cluster``, ``observed_share``, ``expected_share`` e ``ratio``.
    """
    adjacency = (weights.sparse > 0).astype(np.float64)  # pyright: ignore[reportAttributeAccessIssue]
    clusters = np.unique(labels)
    indicator = (labels[:, None] == clusters[None, :]).astype(np.float64)
    neighbors_in_cluster = adjacency @ indicator  # (n, k): vizinhos em cada cluster
    own = neighbors_in_cluster[np.arange(len(labels)), np.searchsorted(clusters, labels)]
    degree = np.asarray(adjacency.sum(axis=1)).ravel()
    same_share = own / degree

    rows = []
    for cluster in clusters:
        members = labels == cluster
        expected = float(members.mean())
        observed = float(same_share[members].mean())
        rows.append(
            {
                "cluster": int(cluster),
                "observed_share": observed,
                "expected_share": expected,
                "ratio": observed / expected if expected > 0 else float("nan"),
            }
        )
    return pl.DataFrame(rows)
