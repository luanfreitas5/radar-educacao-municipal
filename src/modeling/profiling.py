"""Perfil dos clusters: medianas, z-scores, IC bootstrap e teste de diferença do desfecho."""

import numpy as np
import polars as pl
from scipy import stats

CLUSTER = "cluster"


def bootstrap_median_ci(
    values: np.ndarray, n_resamples: int, seed: int, level: float = 0.95
) -> tuple[float, float]:
    """Intervalo de confiança percentílico (bootstrap) para a mediana.

    Parameters
    ----------
    values : np.ndarray
        Amostra sem nulos.
    n_resamples : int
        Número de reamostragens com reposição.
    seed : int
        Semente.
    level : float, optional
        Nível de confiança, by default 0.95.

    Returns
    -------
    tuple[float, float]
        Limites inferior e superior; ``(nan, nan)`` para amostra vazia.
    """
    if len(values) == 0:
        return float("nan"), float("nan")
    rng = np.random.default_rng(seed)
    samples = rng.choice(values, size=(n_resamples, len(values)), replace=True)
    medians = np.median(samples, axis=1)
    alpha = (1 - level) / 2
    low, high = np.quantile(medians, [alpha, 1 - alpha])
    return float(low), float(high)


def profile_clusters(
    df: pl.DataFrame,
    features: list[str],
    outcomes: list[str],
    n_resamples: int,
    seed: int,
) -> pl.DataFrame:
    """Resume cada cluster: tamanho, mediana das variáveis e do desfecho com IC 95%.

    Parameters
    ----------
    df : pl.DataFrame
        Tabela com a coluna ``cluster`` (municípios clusterizados).
    features : list[str]
        Variáveis da clusterização (escala original).
    outcomes : list[str]
        Desfechos não usados na clusterização (ex.: IDEB).
    n_resamples : int
        Reamostragens do bootstrap.
    seed : int
        Semente.

    Returns
    -------
    pl.DataFrame
        Uma linha por cluster, com ``n``, ``share``, ``<variável>_median`` e,
        para cada desfecho, ``_median``, ``_ci_low``, ``_ci_high`` e ``_n``.
    """
    total = df.height
    rows = []
    for (cluster,), group in df.group_by(CLUSTER, maintain_order=True):
        row: dict[str, object] = {
            CLUSTER: cluster,
            "n": group.height,
            "share": group.height / total,
        }
        for name in features:
            row[f"{name}_median"] = group[name].median()
        for name in outcomes:
            valid = group[name].drop_nulls().to_numpy()
            low, high = bootstrap_median_ci(valid, n_resamples, seed)
            row[f"{name}_median"] = float(np.median(valid)) if len(valid) else None
            row[f"{name}_ci_low"] = low
            row[f"{name}_ci_high"] = high
            row[f"{name}_n"] = len(valid)
        rows.append(row)
    return pl.DataFrame(rows, infer_schema_length=None).sort(CLUSTER)


def compute_cluster_zscores(df: pl.DataFrame, features: list[str]) -> pl.DataFrame:
    """Mediana de cada cluster em desvios-padrão da média geral (para o mapa de calor).

    Parameters
    ----------
    df : pl.DataFrame
        Tabela com a coluna ``cluster``.
    features : list[str]
        Variáveis a comparar.

    Returns
    -------
    pl.DataFrame
        ``cluster`` e uma coluna por variável com o z-score da mediana do cluster.
    """
    return (
        df.group_by(CLUSTER)
        .agg([pl.col(name).median() for name in features])
        .with_columns(
            [((pl.col(name) - df[name].mean()) / df[name].std()).alias(name) for name in features]
        )
        .sort(CLUSTER)
    )


def describe_clusters(zscores: pl.DataFrame, top: int = 3) -> dict[int, str]:
    """Descreve cada cluster pelas variáveis mais distantes da média geral.

    Parameters
    ----------
    zscores : pl.DataFrame
        Saída de :func:`compute_cluster_zscores`.
    top : int, optional
        Número de variáveis citadas por cluster, by default 3.

    Returns
    -------
    dict[int, str]
        Cluster -> texto como ``"população (+1,2), internet (-0,8)"``.
    """
    descriptions: dict[int, str] = {}
    features = [name for name in zscores.columns if name != CLUSTER]
    for row in zscores.iter_rows(named=True):
        ranked = sorted(features, key=lambda name: abs(row[name]), reverse=True)[:top]
        parts = [f"{name} ({row[name]:+.1f})".replace(".", ",") for name in ranked]
        descriptions[int(row[CLUSTER])] = ", ".join(parts)
    return descriptions


def evaluate_outcome_differences(df: pl.DataFrame, outcome: str) -> dict[str, float]:
    """Testa se o desfecho difere entre clusters (Kruskal-Wallis + tamanho de efeito).

    O epsilon² de Kruskal-Wallis, ``H / (n - 1)``, mede a fração da variação
    dos postos explicada pelos clusters; é reportado junto ao p-valor, pois
    com milhares de municípios quase qualquer diferença é "significativa".

    Parameters
    ----------
    df : pl.DataFrame
        Tabela com ``cluster`` e o desfecho.
    outcome : str
        Nome do desfecho.

    Returns
    -------
    dict[str, float]
        ``h``, ``p_value``, ``epsilon_squared`` e ``n``; vazios se houver
        menos de dois clusters com dados.
    """
    groups = [
        group[outcome].drop_nulls().to_numpy()
        for _, group in df.group_by(CLUSTER)
        if group[outcome].drop_nulls().len() > 0
    ]
    n = sum(len(group) for group in groups)
    if len(groups) < 2:
        return {"h": float("nan"), "p_value": float("nan"), "epsilon_squared": float("nan"), "n": n}
    result = stats.kruskal(*groups)
    return {
        "h": float(result.statistic),
        "p_value": float(result.pvalue),
        "epsilon_squared": float(result.statistic) / (n - 1),
        "n": n,
    }


def compute_median_by_slice(
    df: pl.DataFrame, outcome: str, slice_column: str, min_size: int
) -> pl.DataFrame:
    """Mediana do desfecho por cluster e fatia (ex.: região), ocultando células pequenas.

    Parameters
    ----------
    df : pl.DataFrame
        Tabela com ``cluster``, ``slice_column`` e o desfecho.
    outcome : str
        Desfecho.
    slice_column : str
        Coluna de fatiamento (ex.: ``"region"``).
    min_size : int
        Células com menos observações válidas ficam nulas.

    Returns
    -------
    pl.DataFrame
        Formato largo: uma linha por cluster e uma coluna por fatia.
    """
    long = (
        df.drop_nulls([outcome, slice_column])
        .group_by(CLUSTER, slice_column)
        .agg(pl.col(outcome).median().alias("median"), pl.len().alias("n"))
        .with_columns(pl.when(pl.col("n") >= min_size).then(pl.col("median")).alias("median"))
    )
    return long.pivot(on=slice_column, index=CLUSTER, values="median").sort(CLUSTER)
