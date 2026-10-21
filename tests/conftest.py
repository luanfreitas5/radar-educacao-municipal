"""Fixtures compartilhadas: configuração real e dados sintéticos pequenos."""

import os

os.environ.setdefault("MPLBACKEND", "Agg")  # figuras sem interface gráfica

import geopandas as gpd
import numpy as np
import polars as pl
import pytest
from shapely.geometry import box

from config.paths import ProjectPaths
from config.settings import Settings, load_settings
from constants.columns import CENSO_RAW_COLUMNS


@pytest.fixture(scope="session")
def settings() -> Settings:
    """Configuração real do repositório (também testa os YAML versionados)."""
    return load_settings()


@pytest.fixture
def tmp_paths(tmp_path) -> ProjectPaths:
    """Caminhos do projeto apontando para um diretório temporário."""
    paths = ProjectPaths(
        root=tmp_path,
        bronze=tmp_path / "data" / "bronze",
        silver=tmp_path / "data" / "silver",
        gold=tmp_path / "data" / "gold",
        staging=tmp_path / "data" / "silver" / "_staging",
        reports=tmp_path / "reports",
        figures=tmp_path / "reports" / "figures",
        logs=tmp_path / "logs",
    )
    paths.ensure_directories()
    return paths


@pytest.fixture
def schools() -> pl.DataFrame:
    """Escolas sintéticas de dois municípios (uma delas paralisada)."""
    rows = [
        # município, situação, dependência, localização, matrículas, docentes, flags...
        (1100015, 1, 3, 1, 100, 5, 1, 1, 0, 1, 1, 0, 1),
        (1100015, 1, 4, 2, 50, 5, 0, 0, 0, 0, 1, 0, 1),
        (1100015, 2, 3, 1, 999, 99, 1, 1, 1, 1, 1, 1, 1),  # paralisada: deve ser ignorada
        (1100023, 1, 3, 2, 30, 0, 0, 1, 0, 0, 0, 0, 1),
    ]
    return pl.DataFrame(rows, schema=list(CENSO_RAW_COLUMNS), orient="row")


@pytest.fixture
def blobs() -> tuple[np.ndarray, np.ndarray]:
    """Três grupos gaussianos bem separados em 4 dimensões, com rótulos verdadeiros."""
    rng = np.random.default_rng(0)
    centers = np.array([[0, 0, 0, 0], [8, 8, 0, 0], [0, 8, 8, 8]], dtype=float)
    matrix = np.vstack([center + rng.normal(size=(60, 4)) for center in centers])
    truth = np.repeat(np.arange(3), 60)
    return matrix, truth


@pytest.fixture
def grid_geodata() -> gpd.GeoDataFrame:
    """Grade 6x6 de quadrados; ``gradient`` cresce da esquerda para a direita."""
    cells = [(row, col) for row in range(6) for col in range(6)]
    return gpd.GeoDataFrame(
        {
            "code_muni": [1_000_000 + index for index in range(len(cells))],
            "gradient": [float(col) for _, col in cells],
            "checker": [float((row + col) % 2) for row, col in cells],
        },
        geometry=[box(col, row, col + 1, row + 1) for row, col in cells],
        crs="EPSG:4674",
    )
