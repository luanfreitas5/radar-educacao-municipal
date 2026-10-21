"""Etapa 4: vizinhança Queen, I de Moran global/local (LISA) e mapas."""

import logging
from dataclasses import asdict
from pathlib import Path

import geopandas as gpd
import polars as pl

from config.paths import ProjectPaths
from config.settings import Settings
from constants import files
from constants.columns import KEY
from reporting.results import update_results
from spatial.autocorrelation import compute_global_moran, compute_local_moran
from spatial.cohesion import compute_cluster_cohesion
from spatial.weights import build_queen_weights
from utils.seed import seed_everything
from visualization.maps import plot_cluster_map, plot_lisa_map
from visualization.theme import configure_theme, save_figure

logger = logging.getLogger(__name__)


def _load_geodata(settings: Settings, paths: ProjectPaths) -> gpd.GeoDataFrame:
    """Une a malha silver aos clusters e às variáveis analisadas."""
    geodata = gpd.read_parquet(paths.silver / files.SILVER_GEOBR, columns=[KEY, "geometry"])
    attributes = pl.read_parquet(
        paths.gold / files.GOLD_CLUSTERS,
        columns=[KEY, "cluster", *settings.spatial.variables],
    ).to_pandas()
    return geodata.merge(attributes, on=KEY, how="left")  # pyright: ignore[reportReturnType]


def run_spatial(settings: Settings, paths: ProjectPaths) -> Path:
    """Executa a análise espacial das variáveis configuradas e dos clusters.

    Para cada variável: restringe-se aos municípios com valor, constrói-se a
    vizinhança Queen (removendo ilhas), calcula-se o I de Moran global e o LISA
    com correção FDR. Para os clusters, mede-se a coesão territorial (fração
    de vizinhos no mesmo cluster versus o esperado ao acaso).

    Parameters
    ----------
    settings : Settings
        Configuração validada.
    paths : ProjectPaths
        Caminhos do projeto.

    Returns
    -------
    Path
        Parquet com ``code_muni`` e, por variável, ``lisa_<var>_class``,
        ``lisa_<var>_i`` e ``lisa_<var>_p_adjusted``.
    """
    config = settings.spatial
    seed = settings.project.random_seed
    seed_everything(seed)
    configure_theme()
    geodata = _load_geodata(settings, paths)

    moran_results: list[dict[str, object]] = []
    lisa_counts: dict[str, dict[str, int]] = {}
    lisa_tables: list[pl.DataFrame] = []
    lisa_geodata: dict[str, gpd.GeoDataFrame] = {}

    for variable in config.variables:
        subset = geodata.dropna(subset=[variable])
        weights, connected = build_queen_weights(subset)  # pyright: ignore[reportArgumentType]
        values = connected[variable].to_numpy(dtype="float64")

        moran = compute_global_moran(values, weights, variable, config.permutations)
        local = compute_local_moran(
            values, weights, config.permutations, config.alpha, seed, config.apply_fdr
        )
        logger.info("Moran I (%s) = %.4f, p = %.4f", variable, moran.moran_i, moran.p_value)
        moran_results.append(asdict(moran))
        lisa_counts[variable] = {
            str(label): int(count) for label, count in local["lisa_class"].value_counts().rows()
        }
        lisa_tables.append(
            local.select(
                pl.Series(KEY, connected[KEY].to_numpy()),
                pl.col("lisa_class").alias(f"lisa_{variable}_class"),
                pl.col("local_i").alias(f"lisa_{variable}_i"),
                pl.col("p_adjusted").alias(f"lisa_{variable}_p_adjusted"),
            )
        )
        classified = connected[[KEY, "geometry"]].copy()
        classified["lisa_class"] = local["lisa_class"].to_numpy()
        lisa_geodata[variable] = classified

    for variable, classified in lisa_geodata.items():
        base = geodata[[KEY, "geometry"]].merge(classified[[KEY, "lisa_class"]], on=KEY, how="left")
        title = f"Clusters LISA — {variable} (I de Moran local, FDR)"
        save_figure(plot_lisa_map(base, "lisa_class", title), f"lisa_{variable}", paths.figures)

    clustered = geodata.dropna(subset=["cluster"])
    cluster_weights, connected_clusters = build_queen_weights(clustered)  # pyright: ignore[reportArgumentType]
    cohesion = compute_cluster_cohesion(
        connected_clusters["cluster"].to_numpy(dtype="int64"), cluster_weights
    )
    save_figure(plot_cluster_map(geodata), "cluster_map", paths.figures)

    output = paths.gold / files.GOLD_LISA
    lisa = lisa_tables[0]
    for table in lisa_tables[1:]:
        lisa = lisa.join(table, on=KEY, how="full", coalesce=True)
    lisa.sort(KEY).write_parquet(output)
    cohesion.write_parquet(paths.reports / "cluster_cohesion.parquet")

    update_results(
        paths.reports / files.RESULTS_JSON,
        "spatial",
        {
            "permutations": config.permutations,
            "alpha": config.alpha,
            "apply_fdr": config.apply_fdr,
            "primary_variable": config.primary_variable,
            "moran": moran_results,
            "lisa_counts": lisa_counts,
            "cohesion": cohesion.to_dicts(),
        },
    )
    return output
