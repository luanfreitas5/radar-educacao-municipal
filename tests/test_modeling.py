"""Testes da clusterização, estabilidade, UMAP e perfil dos clusters."""

import numpy as np
import polars as pl
import pytest
from hypothesis import given
from hypothesis import strategies as st
from sklearn.metrics import adjusted_rand_score

from exceptions import DataValidationError
from modeling.clustering import (
    assess_stability,
    build_feature_matrix,
    choose_k,
    evaluate_silhouette,
    fit_kmeans,
    relabel_by_size,
    select_k,
    standardize,
)
from modeling.embedding import compute_umap
from modeling.profiling import (
    bootstrap_median_ci,
    compute_cluster_zscores,
    compute_median_by_slice,
    describe_clusters,
    evaluate_outcome_differences,
    profile_clusters,
)


@pytest.mark.smoke
def test_standardize_zero_mean_unit_variance(blobs):
    """Colunas padronizadas têm média ~0 e desvio ~1."""
    matrix, _ = blobs
    scaled, _ = standardize(matrix)
    assert np.allclose(scaled.mean(axis=0), 0, atol=1e-9)
    assert np.allclose(scaled.std(axis=0), 1, atol=1e-9)


def test_build_feature_matrix_applies_log_only_to_selected():
    """log1p é aplicado só às colunas indicadas, preservando a ordem."""
    df = pl.DataFrame({"a": [0.0, 3.0], "b": [0.5, 0.25]})
    matrix = build_feature_matrix(df, ["a", "b"], ["a"])
    assert matrix[:, 0].tolist() == pytest.approx([0.0, np.log1p(3.0)])
    assert matrix[:, 1].tolist() == [0.5, 0.25]


def test_build_feature_matrix_rejects_nulls_and_invalid_logs():
    """Nulos e log de valor <= -1 são rejeitados com erro explicativo."""
    with pytest.raises(DataValidationError, match="nulos"):
        build_feature_matrix(pl.DataFrame({"a": [1.0, None]}), ["a"], [])
    with pytest.raises(DataValidationError, match="finitos"):
        build_feature_matrix(pl.DataFrame({"a": [1.0, -1.0]}), ["a"], ["a"])


@pytest.mark.ml
def test_kmeans_recovers_well_separated_groups(blobs):
    """Behavioral: grupos bem separados são recuperados (ARI ~ 1) e k = 3 é o melhor."""
    matrix, truth = blobs
    scaled, _ = standardize(matrix)
    selection = select_k(scaled, k_min=2, k_max=6, n_init=5, seed=0)
    k = choose_k(selection)
    labels, _ = fit_kmeans(scaled, k, n_init=5, seed=0)

    assert k == 3
    assert adjusted_rand_score(truth, labels) > 0.95
    assert evaluate_silhouette(scaled, labels) > 0.5


@pytest.mark.ml
def test_stability_is_high_for_clear_structure(blobs):
    """Estrutura clara produz ARI alto sob subamostragem, com IC coerente."""
    scaled, _ = standardize(blobs[0])
    labels, _ = fit_kmeans(scaled, 3, n_init=5, seed=0)
    summary = assess_stability(scaled, labels, 3, repeats=8, fraction=0.7, n_init=3, seed=0)
    assert summary.mean > 0.9
    assert summary.ci_low <= summary.mean <= summary.ci_high


def test_choose_k_breaks_ties_with_smaller_k():
    """Empate de silhouette escolhe o menor k (mais parcimonioso)."""
    selection = pl.DataFrame(
        {"k": [3, 4, 5], "inertia": [3.0, 2.0, 1.0], "silhouette": [0.4, 0.4, 0.3]}
    )
    assert choose_k(selection) == 3


@given(st.lists(st.integers(min_value=0, max_value=6), min_size=1, max_size=60))
def test_relabel_by_size_preserves_partition_and_orders_by_size(labels):
    """Invariantes: mesma partição (ARI = 1), rótulos 0..k-1, tamanhos decrescentes."""
    original = np.array(labels)
    relabeled = relabel_by_size(original)

    assert adjusted_rand_score(original, relabeled) == pytest.approx(1.0)
    assert set(relabeled) == set(range(len(set(labels))))
    sizes = np.bincount(relabeled)
    assert all(sizes[i] >= sizes[i + 1] for i in range(len(sizes) - 1))


@pytest.mark.ml
def test_umap_returns_two_dimensions(blobs):
    """A projeção tem uma linha por município e duas colunas finitas."""
    scaled, _ = standardize(blobs[0])
    embedding = compute_umap(scaled, n_neighbors=10, min_dist=0.1, seed=0)
    assert embedding.shape == (len(scaled), 2)
    assert np.isfinite(embedding).all()


def _clustered_frame() -> pl.DataFrame:
    rng = np.random.default_rng(1)
    cluster = np.repeat([0, 1], 80)
    return pl.DataFrame(
        {
            "cluster": cluster,
            "x": np.where(cluster == 0, 0.0, 5.0) + rng.normal(size=160),
            "ideb": np.where(cluster == 0, 4.0, 6.0) + rng.normal(scale=0.3, size=160),
            "region": np.tile(["Norte", "Sul"], 80),
        }
    )


def test_profile_has_confidence_interval_around_median():
    """O perfil traz mediana do desfecho com IC 95% que a contém."""
    profile = profile_clusters(_clustered_frame(), ["x"], ["ideb"], n_resamples=300, seed=0)
    row = profile.filter(pl.col("cluster") == 1).row(0, named=True)
    assert row["n"] == 80
    assert row["ideb_ci_low"] <= row["ideb_median"] <= row["ideb_ci_high"]
    assert row["share"] == pytest.approx(0.5)


def test_zscores_and_descriptions_name_the_distinguishing_feature():
    """Cluster com x alto recebe z-score positivo e a variável é citada na descrição."""
    frame = _clustered_frame()
    zscores = compute_cluster_zscores(frame, ["x"])
    assert zscores.filter(pl.col("cluster") == 1)["x"].item() > 0
    assert "x (+" in describe_clusters(zscores)[1]


def test_outcome_difference_test_detects_real_difference():
    """Kruskal-Wallis detecta a diferença de IDEB e o efeito é grande."""
    result = evaluate_outcome_differences(_clustered_frame(), "ideb")
    assert result["p_value"] < 1e-6
    assert result["epsilon_squared"] > 0.5
    assert result["n"] == 160


def test_outcome_difference_with_single_group_is_nan():
    """Com menos de dois grupos o teste não se aplica."""
    single = _clustered_frame().filter(pl.col("cluster") == 0)
    assert np.isnan(evaluate_outcome_differences(single, "ideb")["p_value"])


def test_median_by_slice_hides_small_cells():
    """Células com menos observações que o mínimo ficam nulas."""
    table = compute_median_by_slice(_clustered_frame(), "ideb", "region", min_size=1000)
    assert table.select(pl.exclude("cluster")).null_count().sum_horizontal().item() == 2 * 2
    visible = compute_median_by_slice(_clustered_frame(), "ideb", "region", min_size=10)
    assert visible.null_count().sum_horizontal().item() == 0


def test_bootstrap_ci_handles_empty_input():
    """Amostra vazia devolve NaN em vez de falhar."""
    low, high = bootstrap_median_ci(np.array([]), 100, 0)
    assert np.isnan(low) and np.isnan(high)
