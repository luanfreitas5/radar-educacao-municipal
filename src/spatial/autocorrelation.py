"""I de Moran global e local (LISA) com correção para múltiplas comparações."""

from dataclasses import dataclass

import numpy as np
import polars as pl
from esda.moran import Moran, Moran_Local
from libpysal.weights import W
from scipy.stats import false_discovery_control

from constants.regions import LISA_NOT_SIGNIFICANT, LISA_QUADRANT_LABELS


@dataclass(frozen=True)
class GlobalMoranResult:
    """Resultado do I de Moran global."""

    variable: str
    moran_i: float
    expected_i: float
    p_value: float
    z_score: float
    permutations: int
    n: int


def compute_global_moran(
    values: np.ndarray, weights: W, variable: str, permutations: int
) -> GlobalMoranResult:
    """Calcula o I de Moran global com inferência por permutação.

    Parameters
    ----------
    values : np.ndarray
        Valores da variável, alinhados às linhas da matriz de pesos.
    weights : W
        Matriz de vizinhança (padronizada por linha).
    variable : str
        Nome da variável (apenas para identificação).
    permutations : int
        Número de permutações; o p-valor mínimo é ``1 / (permutations + 1)``.

    Returns
    -------
    GlobalMoranResult
        I observado, valor esperado sob aleatoriedade espacial, p-valor e z-score
        pseudo-significantes. A reprodutibilidade depende de ``np.random.seed``.
    """
    moran = Moran(values, weights, permutations=permutations)
    return GlobalMoranResult(
        variable=variable,
        moran_i=float(moran.I),
        expected_i=float(moran.EI),
        p_value=float(moran.p_sim),
        z_score=float(moran.z_sim),
        permutations=permutations,
        n=len(values),
    )


def compute_local_moran(
    values: np.ndarray,
    weights: W,
    permutations: int,
    alpha: float,
    seed: int,
    apply_fdr: bool = True,
) -> pl.DataFrame:
    """Calcula o LISA e classifica cada município em HH, LL, HL, LH ou não significativo.

    Com milhares de testes simultâneos, usar ``p < alpha`` sem correção produz
    muitos falsos positivos; por padrão aplica-se Benjamini-Hochberg (FDR).

    Parameters
    ----------
    values : np.ndarray
        Valores da variável, alinhados às linhas da matriz de pesos.
    weights : W
        Matriz de vizinhança (padronizada por linha).
    permutations : int
        Número de permutações condicionais.
    alpha : float
        Nível de significância (após a correção, se aplicada).
    seed : int
        Semente das permutações.
    apply_fdr : bool, optional
        Aplica a correção de Benjamini-Hochberg, by default True.

    Returns
    -------
    pl.DataFrame
        Colunas ``local_i``, ``quadrant``, ``p_value``, ``p_adjusted`` e
        ``lisa_class`` (rótulo em pt-BR), na ordem de ``values``.
    """
    local = Moran_Local(values, weights, permutations=permutations, seed=seed)
    p_values = np.asarray(local.p_sim, dtype=np.float64)
    p_adjusted = false_discovery_control(p_values, method="bh") if apply_fdr else p_values
    quadrants = np.asarray(local.q, dtype=np.int64)
    classes = [
        LISA_QUADRANT_LABELS[int(q)] if p < alpha else LISA_NOT_SIGNIFICANT
        for q, p in zip(quadrants, p_adjusted, strict=True)
    ]
    return pl.DataFrame(
        {
            "local_i": np.asarray(local.Is, dtype=np.float64),
            "quadrant": quadrants,
            "p_value": p_values,
            "p_adjusted": np.asarray(p_adjusted, dtype=np.float64),
            "lisa_class": classes,
        }
    )
