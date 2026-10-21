"""Clusterização de municípios: padronização, seleção de k, KMeans e estabilidade."""

import logging
from dataclasses import dataclass

import numpy as np
import polars as pl
from sklearn.cluster import KMeans
from sklearn.metrics import adjusted_rand_score, silhouette_score
from sklearn.preprocessing import StandardScaler

from exceptions import DataValidationError

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class StabilitySummary:
    """Estabilidade dos clusters sob subamostragem (ARI contra o ajuste completo)."""

    mean: float
    ci_low: float
    ci_high: float
    n_repeats: int


def build_feature_matrix(
    df: pl.DataFrame, features: list[str], log_features: list[str]
) -> np.ndarray:
    """Monta a matriz de atributos aplicando ``log1p`` nas variáveis assimétricas.

    Parameters
    ----------
    df : pl.DataFrame
        Tabela sem nulos nas colunas de ``features``.
    features : list[str]
        Variáveis usadas na clusterização, na ordem das colunas.
    log_features : list[str]
        Subconjunto de ``features`` que recebe ``log1p``.

    Returns
    -------
    np.ndarray
        Matriz ``(n_municípios, n_variáveis)`` em ``float64``.

    Raises
    ------
    DataValidationError
        Se houver nulos, valores infinitos ou valores menores ou iguais a -1
        em variável com ``log1p``.
    """
    selected = df.select(features)
    if sum(selected.null_count().row(0)) > 0:
        raise DataValidationError("A matriz de atributos não pode conter nulos")
    transformed = selected.with_columns([pl.col(name).log1p() for name in log_features])
    matrix = transformed.to_numpy().astype(np.float64)
    if not np.isfinite(matrix).all():
        raise DataValidationError(
            "A matriz contém valores não finitos (verifique variáveis com log1p)"
        )
    return matrix


def standardize(matrix: np.ndarray) -> tuple[np.ndarray, StandardScaler]:
    """Padroniza cada coluna para média 0 e desvio-padrão 1.

    Parameters
    ----------
    matrix : np.ndarray
        Matriz de atributos.

    Returns
    -------
    tuple[np.ndarray, StandardScaler]
        Matriz padronizada e o scaler ajustado.
    """
    scaler = StandardScaler()
    return scaler.fit_transform(matrix), scaler


def select_k(matrix: np.ndarray, k_min: int, k_max: int, n_init: int, seed: int) -> pl.DataFrame:
    """Avalia cada k pelo silhouette e pela inércia (método do cotovelo).

    Parameters
    ----------
    matrix : np.ndarray
        Matriz padronizada.
    k_min, k_max : int
        Faixa (inclusiva) de números de clusters.
    n_init : int
        Reinicializações do KMeans.
    seed : int
        Semente.

    Returns
    -------
    pl.DataFrame
        Colunas ``k``, ``inertia`` e ``silhouette``.
    """
    rows = []
    for k in range(k_min, k_max + 1):
        model = KMeans(n_clusters=k, n_init=n_init, random_state=seed).fit(matrix)  # pyright: ignore[reportArgumentType]
        score = float(silhouette_score(matrix, model.labels_))
        rows.append({"k": k, "inertia": float(model.inertia_), "silhouette": score})  # pyright: ignore[reportArgumentType]
        logger.info("k=%d silhouette=%.4f inércia=%.1f", k, score, model.inertia_)
    return pl.DataFrame(rows)


def choose_k(selection: pl.DataFrame) -> int:
    """Escolhe o k de maior silhouette (empates: o menor k, mais parcimonioso).

    Parameters
    ----------
    selection : pl.DataFrame
        Saída de :func:`select_k`.

    Returns
    -------
    int
        Número de clusters escolhido.
    """
    best = selection.sort(["silhouette", "k"], descending=[True, False]).row(0, named=True)
    return int(best["k"])


def relabel_by_size(labels: np.ndarray) -> np.ndarray:
    """Renumera clusters de 0 a k-1 em ordem decrescente de tamanho (rótulos estáveis).

    Parameters
    ----------
    labels : np.ndarray
        Rótulos originais.

    Returns
    -------
    np.ndarray
        Rótulos renumerados; a partição é preservada.
    """
    values, counts = np.unique(labels, return_counts=True)
    order = values[np.argsort(-counts, kind="stable")]
    mapping = {int(old): new for new, old in enumerate(order)}
    return np.array([mapping[int(label)] for label in labels], dtype=np.int64)


def fit_kmeans(matrix: np.ndarray, k: int, n_init: int, seed: int) -> tuple[np.ndarray, KMeans]:
    """Ajusta o KMeans e devolve rótulos ordenados por tamanho.

    Parameters
    ----------
    matrix : np.ndarray
        Matriz padronizada.
    k : int
        Número de clusters.
    n_init : int
        Reinicializações.
    seed : int
        Semente.

    Returns
    -------
    tuple[np.ndarray, KMeans]
        Rótulos (0 = maior cluster) e o modelo ajustado.
    """
    model = KMeans(n_clusters=k, n_init=n_init, random_state=seed).fit(matrix)  # pyright: ignore[reportArgumentType]
    return relabel_by_size(model.labels_), model  # pyright: ignore[reportArgumentType]


def evaluate_silhouette(matrix: np.ndarray, labels: np.ndarray) -> float:
    """Silhouette médio de uma partição.

    Parameters
    ----------
    matrix : np.ndarray
        Matriz padronizada.
    labels : np.ndarray
        Rótulos de cluster.

    Returns
    -------
    float
        Valor entre -1 e 1 (quanto maior, mais coesos e separados os clusters).
    """
    return float(silhouette_score(matrix, labels))


def assess_stability(
    matrix: np.ndarray,
    reference_labels: np.ndarray,
    k: int,
    repeats: int,
    fraction: float,
    n_init: int,
    seed: int,
) -> StabilitySummary:
    """Estima a estabilidade dos clusters por subamostragem.

    Em cada repetição ajusta-se o KMeans em uma subamostra aleatória, atribuem-se
    todos os municípios ao modelo obtido e compara-se com a partição de
    referência pelo índice de Rand ajustado (ARI). Valores próximos de 1 indicam
    tipologias robustas à composição da amostra.

    Parameters
    ----------
    matrix : np.ndarray
        Matriz padronizada.
    reference_labels : np.ndarray
        Partição do ajuste completo.
    k : int
        Número de clusters.
    repeats : int
        Número de subamostragens.
    fraction : float
        Fração do total em cada subamostra (0 a 1, exclusivo).
    n_init : int
        Reinicializações do KMeans.
    seed : int
        Semente.

    Returns
    -------
    StabilitySummary
        Média do ARI e intervalo de 95% (percentis 2,5 e 97,5).
    """
    rng = np.random.default_rng(seed)
    size = max(k, int(fraction * len(matrix)))
    scores = np.empty(repeats)
    for repeat in range(repeats):
        index = rng.choice(len(matrix), size=size, replace=False)
        model = KMeans(n_clusters=k, n_init=n_init, random_state=seed + repeat).fit(matrix[index])  # pyright: ignore[reportArgumentType]
        scores[repeat] = adjusted_rand_score(reference_labels, model.predict(matrix))
    low, high = np.percentile(scores, [2.5, 97.5])
    return StabilitySummary(
        mean=float(scores.mean()), ci_low=float(low), ci_high=float(high), n_repeats=repeats
    )
