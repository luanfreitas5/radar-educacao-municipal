"""Projeção UMAP em duas dimensões (apenas para visualização)."""

import numpy as np


def compute_umap(matrix: np.ndarray, n_neighbors: int, min_dist: float, seed: int) -> np.ndarray:
    """Projeta a matriz padronizada em 2D com UMAP.

    A projeção serve só para visualizar as tipologias: distâncias entre nuvens e
    tamanhos de grupos no plano não têm interpretação quantitativa, e os
    clusters são definidos no espaço original padronizado, não no UMAP.

    Parameters
    ----------
    matrix : np.ndarray
        Matriz padronizada.
    n_neighbors : int
        Tamanho da vizinhança local.
    min_dist : float
        Distância mínima entre pontos no plano.
    seed : int
        Semente (também torna a execução determinística, em um único thread).

    Returns
    -------
    np.ndarray
        Matriz ``(n, 2)`` com as coordenadas.
    """
    import umap  # importação sob demanda: carregar numba/umap é lento  # noqa: PLC0415

    reducer = umap.UMAP(
        n_components=2,
        n_neighbors=min(n_neighbors, len(matrix) - 1),
        min_dist=min_dist,
        random_state=seed,
    )
    return np.asarray(reducer.fit_transform(matrix))
