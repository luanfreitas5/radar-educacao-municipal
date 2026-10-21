"""Teste de integração: silver sintético -> gold -> clusters -> espacial -> relatório."""

import json

import geopandas as gpd
import numpy as np
import polars as pl
import pytest

from constants import files
from exceptions import IntegrityError
from main import build_parser, run
from pipelines.clustering import run_clustering
from pipelines.gold import run_gold
from pipelines.report import run_report
from pipelines.spatial import run_spatial

N = 36


def _write_synthetic_silver(paths, grid_geodata: gpd.GeoDataFrame) -> None:
    """Grava tabelas silver sintéticas com dois perfis de município (esquerda/direita)."""
    rng = np.random.default_rng(7)
    codes = grid_geodata["code_muni"].to_list()
    right = np.array(grid_geodata["gradient"] >= 3)

    def level(low: float, high: float, scale: float = 0.05) -> list[float]:
        base = np.where(right, high, low) + rng.normal(scale=scale, size=N)
        return np.clip(base, 0.0, 1.0).tolist()

    paths.silver.mkdir(parents=True, exist_ok=True)
    pl.DataFrame(
        {
            "code_muni": codes,
            "n_schools": rng.integers(5, 40, N).tolist(),
            "enrollments": rng.integers(500, 5000, N).tolist(),
            "teachers": rng.integers(30, 300, N).tolist(),
            "rural_share": level(0.7, 0.1),
            "municipal_network_share": level(0.8, 0.4),
            "internet_share": level(0.3, 0.9),
            "library_share": level(0.2, 0.7),
            "computer_lab_share": level(0.1, 0.6),
            "sports_court_share": level(0.2, 0.8),
            "water_network_share": level(0.4, 0.95),
            "sewage_network_share": level(0.1, 0.7),
            "electricity_network_share": level(0.9, 1.0),
            "students_per_teacher": (np.where(right, 18.0, 12.0) + rng.normal(size=N)).tolist(),
            "enrollments_per_school": (np.where(right, 300.0, 90.0) + rng.normal(size=N)).tolist(),
        }
    ).write_parquet(paths.silver / files.SILVER_CENSO)

    pl.DataFrame(
        {
            "code_muni": codes,
            "ideb_early_years": (
                np.where(right, 6.2, 4.8) + rng.normal(scale=0.2, size=N)
            ).tolist(),
            "ideb_late_years": (np.where(right, 5.4, 4.0) + rng.normal(scale=0.2, size=N)).tolist(),
        }
    ).write_parquet(paths.silver / files.SILVER_IDEB)

    population = np.where(right, 150_000.0, 8_000.0) * rng.uniform(0.8, 1.2, N)
    area = rng.uniform(100.0, 2000.0, N)
    pl.DataFrame(
        {
            "code_muni": codes,
            "population": population.tolist(),
            "area_km2": area.tolist(),
            "population_density": (population / area).tolist(),
            "gdp_per_capita": (
                np.where(right, 40_000.0, 12_000.0) * rng.uniform(0.9, 1.1, N)
            ).tolist(),
        }
    ).write_parquet(paths.silver / files.SILVER_SIDRA)

    geo = grid_geodata[["code_muni", "geometry"]].copy()
    geo["name_muni"] = [f"Município {code}" for code in codes]
    geo["abbrev_state"] = "RO"
    geo["region"] = "Norte"
    geo.to_parquet(paths.silver / files.SILVER_GEOBR)


@pytest.fixture
def fast_settings(settings):
    """Configuração real com hiperparâmetros reduzidos para o teste ser rápido."""
    return settings.model_copy(
        update={
            "clustering": settings.clustering.model_copy(
                update={"n_init": 3, "stability_repeats": 5, "bootstrap_resamples": 200}
            ),
            "spatial": settings.spatial.model_copy(update={"permutations": 99}),
        }
    )


@pytest.mark.integration
def test_pipeline_end_to_end(fast_settings, tmp_paths, grid_geodata):
    """Do silver ao relatório: arquivos gerados, achados coerentes e relatório completo."""
    _write_synthetic_silver(tmp_paths, grid_geodata)

    gold_path = run_gold(fast_settings, tmp_paths)
    assert pl.read_parquet(gold_path).height == N

    clusters_path = run_clustering(fast_settings, tmp_paths)
    clustered = pl.read_parquet(clusters_path)
    assert clustered["cluster"].null_count() == 0
    assert clustered["cluster"].n_unique() >= 2
    assert (tmp_paths.figures / "umap_clusters.png").is_file()
    assert (tmp_paths.figures / "umap_clusters.svg").is_file()

    lisa_path = run_spatial(fast_settings, tmp_paths)
    assert pl.read_parquet(lisa_path).height == N
    assert (tmp_paths.figures / "lisa_ideb_early_years.png").is_file()

    report_path = run_report(tmp_paths)
    report = report_path.read_text(encoding="utf-8")
    for expected in ("Integridade", "Tipologias", "I de Moran global", "Limitações"):
        assert expected in report

    results = json.loads((tmp_paths.reports / files.RESULTS_JSON).read_text(encoding="utf-8"))
    assert results["integrity"]["passed"] is True
    moran = {item["variable"]: item for item in results["spatial"]["moran"]}
    assert moran["ideb_early_years"]["moran_i"] > 0  # IDEB segue o padrão espacial sintético


@pytest.mark.integration
def test_gold_fails_loudly_when_coverage_is_insufficient(fast_settings, tmp_paths, grid_geodata):
    """Municípios sem IDEB acima do tolerado reprovam a integridade, mas o relatório é salvo."""
    _write_synthetic_silver(tmp_paths, grid_geodata)
    ideb = pl.read_parquet(tmp_paths.silver / files.SILVER_IDEB).head(10)
    ideb.write_parquet(tmp_paths.silver / files.SILVER_IDEB)

    with pytest.raises(IntegrityError, match="ideb_early_years"):
        run_gold(fast_settings, tmp_paths)

    report = json.loads((tmp_paths.reports / files.INTEGRITY_JSON).read_text(encoding="utf-8"))
    assert report["passed"] is False
    assert not (tmp_paths.gold / files.GOLD_MUNICIPALITIES).exists()


@pytest.mark.smoke
def test_cli_parser_accepts_all_stages():
    """O parser aceita cada etapa e rejeita nomes desconhecidos."""
    parser = build_parser()
    for stage in ("ingest", "silver", "gold", "cluster", "spatial", "report", "all"):
        assert parser.parse_args([stage]).stage == stage
    with pytest.raises(SystemExit):
        parser.parse_args(["etapa-inexistente"])


def test_run_returns_error_code_on_pipeline_failure(tmp_path):
    """Falha esperada do pipeline devolve código 1 em vez de traceback."""
    assert run(["gold", "--config-dir", str(tmp_path / "inexistente")]) == 1
