"""Testes da vizinhança Queen, Moran global/local e coesão dos clusters."""

import geopandas as gpd
import numpy as np
import pandas as pd
import pytest
from shapely.geometry import box

from spatial.autocorrelation import compute_global_moran, compute_local_moran
from spatial.cohesion import compute_cluster_cohesion
from spatial.weights import build_queen_weights

PERMUTATIONS = 199


@pytest.mark.smoke
def test_queen_weights_on_grid(grid_geodata):
    """Em grade 6x6, o canto tem 3 vizinhos Queen e o centro tem 8."""
    weights, table = build_queen_weights(grid_geodata)
    assert len(table) == 36
    assert weights.cardinalities[0] == 3
    assert weights.cardinalities[14] == 8  # linha 2, coluna 2
    assert weights.transform == "R"


def test_islands_are_removed(grid_geodata):
    """Um polígono isolado é removido e a matriz fica sem ilhas."""
    island = gpd.GeoDataFrame(
        {"code_muni": [2_000_000], "gradient": [1.0], "checker": [0.0]},
        geometry=[box(100, 100, 101, 101)],
        crs=grid_geodata.crs,
    )
    combined = gpd.GeoDataFrame(
        pd.concat([grid_geodata, island], ignore_index=True), crs=grid_geodata.crs
    )

    weights, table = build_queen_weights(combined)
    assert len(table) == 36
    assert 2_000_000 not in set(table["code_muni"])
    assert not weights.islands


@pytest.mark.ml
def test_global_moran_detects_positive_and_negative_autocorrelation(grid_geodata):
    """Gradiente espacial gera I > 0 significativo; tabuleiro gera I < 0."""
    weights, table = build_queen_weights(grid_geodata)
    np.random.seed(0)  # noqa: NPY002 - esda usa o estado global do NumPy
    smooth = compute_global_moran(table["gradient"].to_numpy(), weights, "gradient", PERMUTATIONS)
    np.random.seed(0)  # noqa: NPY002
    checker = compute_global_moran(table["checker"].to_numpy(), weights, "checker", PERMUTATIONS)

    assert smooth.moran_i > 0.5
    assert smooth.p_value < 0.05
    assert checker.moran_i < 0
    assert smooth.expected_i == pytest.approx(-1 / 35)
    assert smooth.n == 36


@pytest.mark.ml
def test_local_moran_classifies_hot_and_cold_spots(grid_geodata):
    """Extremos do gradiente aparecem como Alto-Alto (direita) e Baixo-Baixo (esquerda)."""
    weights, table = build_queen_weights(grid_geodata)
    local = compute_local_moran(
        table["gradient"].to_numpy(), weights, PERMUTATIONS, alpha=0.2, seed=0, apply_fdr=False
    )
    classes = local["lisa_class"].to_list()
    right_edge = [i for i, g in enumerate(table["gradient"]) if g == 5.0]
    left_edge = [i for i, g in enumerate(table["gradient"]) if g == 0.0]

    assert any(classes[i] == "Alto-Alto" for i in right_edge)
    assert any(classes[i] == "Baixo-Baixo" for i in left_edge)
    assert local.height == 36
    assert local["p_adjusted"].min() >= 0  # pyright: ignore[reportOperatorIssue]


def test_fdr_never_increases_significant_count(grid_geodata):
    """Invariante: a correção FDR não aumenta o número de municípios significativos."""
    weights, table = build_queen_weights(grid_geodata)
    values = table["gradient"].to_numpy()
    raw = compute_local_moran(values, weights, PERMUTATIONS, 0.1, seed=3, apply_fdr=False)
    adjusted = compute_local_moran(values, weights, PERMUTATIONS, 0.1, seed=3, apply_fdr=True)

    def significant(frame) -> int:
        return int((frame["lisa_class"] != "Não significativo").sum())

    assert significant(adjusted) <= significant(raw)


def test_cluster_cohesion_high_for_contiguous_blocks(grid_geodata):
    """Blocos contíguos têm razão observado/esperado > 1; tabuleiro tem razão < 1."""
    weights, table = build_queen_weights(grid_geodata)
    blocks = (table["gradient"].to_numpy() >= 3).astype("int64")
    checker = table["checker"].to_numpy().astype("int64")

    contiguous = compute_cluster_cohesion(blocks, weights)
    alternating = compute_cluster_cohesion(checker, weights)

    assert (contiguous["ratio"] > 1).all()
    assert (alternating["ratio"] < 1).all()
    assert contiguous["expected_share"].sum() == pytest.approx(1.0)
