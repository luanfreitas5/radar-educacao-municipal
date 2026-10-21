"""Etapa 3: clusterização dos municípios, UMAP e perfil das tipologias."""

import logging
from pathlib import Path

import numpy as np
import polars as pl

from config.paths import ProjectPaths
from config.settings import Settings
from constants import files
from constants.columns import KEY
from modeling.clustering import (
    assess_stability,
    build_feature_matrix,
    choose_k,
    evaluate_silhouette,
    fit_kmeans,
    select_k,
    standardize,
)
from modeling.embedding import compute_umap
from modeling.profiling import (
    compute_cluster_zscores,
    compute_median_by_slice,
    describe_clusters,
    evaluate_outcome_differences,
    profile_clusters,
)
from reporting.results import update_results
from visualization.clusters import plot_cluster_profile, plot_k_selection, plot_umap_clusters
from visualization.theme import configure_theme, save_figure

logger = logging.getLogger(__name__)


def _evaluate_outcomes(
    clustered: pl.DataFrame, outcomes: list[str], min_slice_size: int
) -> tuple[dict, dict]:
    """Testa as diferenças entre clusters e calcula a mediana por região para cada desfecho."""
    tests = {outcome: evaluate_outcome_differences(clustered, outcome) for outcome in outcomes}
    by_region = {
        outcome: compute_median_by_slice(clustered, outcome, "region", min_slice_size).to_dicts()
        for outcome in outcomes
    }
    return tests, by_region


def run_clustering(settings: Settings, paths: ProjectPaths) -> Path:
    """Agrupa os municípios em tipologias e perfila cada grupo.

    Fluxo: remoção de municípios com valores ausentes nas variáveis de entrada
    (quantificada) -> ``log1p`` nas variáveis assimétricas -> padronização ->
    seleção de k por silhouette -> KMeans -> estabilidade por subamostragem ->
    UMAP (visualização) -> perfil, testes e figuras. O IDEB não participa da
    clusterização: é o desfecho usado para validar as tipologias.

    Parameters
    ----------
    settings : Settings
        Configuração validada.
    paths : ProjectPaths
        Caminhos do projeto.

    Returns
    -------
    Path
        Parquet com a base gold acrescida de ``cluster``, ``umap_1`` e ``umap_2``.
    """
    config = settings.clustering
    seed = settings.project.random_seed
    gold = pl.read_parquet(paths.gold / files.GOLD_MUNICIPALITIES)

    complete = gold.drop_nulls(config.features)
    dropped = gold.height - complete.height
    logger.info("Municípios clusterizados: %d (descartados: %d)", complete.height, dropped)

    raw_matrix = build_feature_matrix(complete, config.features, config.log_features)
    matrix, _ = standardize(raw_matrix)

    selection = select_k(matrix, config.k_min, config.k_max, config.n_init, seed)
    k = config.k if config.k is not None else choose_k(selection)
    labels, _ = fit_kmeans(matrix, k, config.n_init, seed)
    silhouette = evaluate_silhouette(matrix, labels)
    stability = assess_stability(
        matrix, labels, k, config.stability_repeats, config.subsample_fraction, config.n_init, seed
    )
    logger.info("k=%d, ARI médio=%.3f", k, stability.mean)

    embedding = compute_umap(matrix, settings.umap.n_neighbors, settings.umap.min_dist, seed)
    clustered = complete.with_columns(
        pl.Series("cluster", labels),
        pl.Series("umap_1", embedding[:, 0]),
        pl.Series("umap_2", embedding[:, 1]),
    )

    profile = profile_clusters(
        clustered, config.features, config.outcomes, config.bootstrap_resamples, seed
    )
    zscores = compute_cluster_zscores(clustered, config.features)
    descriptions = describe_clusters(zscores)
    tests, by_region = _evaluate_outcomes(clustered, config.outcomes, config.min_slice_size)

    configure_theme()
    save_figure(plot_k_selection(selection, k), "k_selection", paths.figures)
    save_figure(plot_umap_clusters(embedding, labels), "umap_clusters", paths.figures)
    save_figure(plot_cluster_profile(zscores), "cluster_profile", paths.figures)

    paths.gold.mkdir(parents=True, exist_ok=True)
    output = paths.gold / files.GOLD_CLUSTERS
    gold.join(
        clustered.select(KEY, "cluster", "umap_1", "umap_2"), on=KEY, how="left"
    ).write_parquet(output)
    profile.write_parquet(paths.reports / files.CLUSTER_PROFILE)

    update_results(
        paths.reports / files.RESULTS_JSON,
        "clustering",
        {
            "n_clustered": complete.height,
            "n_dropped": dropped,
            "k": k,
            "silhouette": silhouette,
            "selection": selection.to_dicts(),
            "stability": {
                "mean": stability.mean,
                "ci_low": stability.ci_low,
                "ci_high": stability.ci_high,
                "n_repeats": stability.n_repeats,
            },
            "outcome_tests": tests,
            "descriptions": {str(cluster): text for cluster, text in descriptions.items()},
            "median_by_region": by_region,
            "cluster_sizes": {
                str(int(c)): int(n)
                for c, n in zip(*np.unique(labels, return_counts=True), strict=True)
            },
        },
    )
    return output
