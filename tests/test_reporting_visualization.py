"""Testes do relatório, dos resultados persistidos, dos logs e das figuras."""

import logging

import numpy as np
import polars as pl
import pytest

from config.logging import configure_logging
from exceptions import RadarError
from reporting.report import LIMITATIONS, build_report, dataframe_to_markdown
from reporting.results import load_results, update_results
from utils.hashing import hash_file
from utils.seed import seed_everything
from visualization.clusters import plot_cluster_profile, plot_k_selection, plot_umap_clusters
from visualization.maps import plot_cluster_map, plot_lisa_map
from visualization.theme import configure_theme, save_figure


@pytest.mark.smoke
def test_markdown_table_formats_numbers_and_nulls():
    """Floats usam vírgula decimal e nulos viram traço."""
    table = dataframe_to_markdown(pl.DataFrame({"a": [1.2345, None], "b": ["x", "y"]}), digits=2)
    lines = table.splitlines()
    assert lines[0] == "| a | b |"
    assert lines[1] == "| --- | --- |"
    assert lines[2] == "| 1,23 | x |"
    assert lines[3] == "| — | y |"


def test_report_without_results_marks_pending_sections():
    """Sem resultados, o relatório avisa em vez de falhar e mantém as limitações."""
    report = build_report({}, pl.DataFrame(), pl.DataFrame())
    assert report.count("Etapa ainda não executada") == 3
    assert LIMITATIONS.splitlines()[0] in report


def test_results_roundtrip_preserves_other_sections(tmp_path):
    """Atualizar uma seção não apaga as demais."""
    path = tmp_path / "results.json"
    update_results(path, "a", {"x": 1})
    update_results(path, "b", {"y": 2})
    update_results(path, "a", {"x": 3})
    assert load_results(path) == {"a": {"x": 3}, "b": {"y": 2}}
    assert load_results(tmp_path / "inexistente.json") == {}


def test_corrupted_results_raise(tmp_path):
    """JSON corrompido gera erro tipado."""
    path = tmp_path / "results.json"
    path.write_text("{quebrado", encoding="utf-8")
    with pytest.raises(RadarError):
        load_results(path)


def test_hash_file_is_deterministic_and_content_sensitive(tmp_path):
    """Mesmo conteúdo -> mesmo hash; conteúdo diferente -> hash diferente."""
    first, second = tmp_path / "a.txt", tmp_path / "b.txt"
    first.write_bytes(b"abc")
    second.write_bytes(b"abd")
    assert hash_file(first) == hash_file(first)
    assert hash_file(first) != hash_file(second)
    assert len(hash_file(first)) == 64


def test_seed_everything_makes_numpy_reproducible():
    """A mesma semente reproduz a mesma sequência aleatória global."""
    seed_everything(123)
    first = np.random.rand(3)  # noqa: NPY002
    seed_everything(123)
    assert np.array_equal(first, np.random.rand(3))  # noqa: NPY002


def test_configure_logging_is_idempotent_and_writes_file(tmp_path):
    """Chamadas repetidas não duplicam handlers e o arquivo de log é criado."""
    root = logging.getLogger()
    original_handlers, original_level = list(root.handlers), root.level
    try:
        configure_logging("INFO", tmp_path)
        configure_logging("INFO", tmp_path)
        assert len(root.handlers) == 2
        logging.getLogger("teste").info("mensagem de teste")
        for handler in root.handlers:
            handler.flush()
        assert (tmp_path / "log.log").is_file()
    finally:
        for handler in list(root.handlers):
            root.removeHandler(handler)
            handler.close()  # libera o arquivo (necessário no Windows)
        for handler in original_handlers:
            root.addHandler(handler)
        root.setLevel(original_level)


@pytest.mark.smoke
def test_figures_are_saved_as_png_and_svg(tmp_path, grid_geodata):
    """Cada gráfico é gerado e salvo nos dois formatos."""
    configure_theme()
    labels = np.arange(36) % 3
    embedding = np.random.default_rng(0).normal(size=(36, 2))
    selection = pl.DataFrame({"k": [3, 4], "inertia": [10.0, 8.0], "silhouette": [0.4, 0.3]})
    zscores = pl.DataFrame({"cluster": [0, 1], "x": [1.0, -1.0], "y": [0.2, -0.2]})

    geodata = grid_geodata.assign(cluster=labels.astype(float))
    geodata["lisa_class"] = np.where(labels == 0, "Alto-Alto", "Não significativo")

    figures = {
        "k": plot_k_selection(selection, 3),
        "umap": plot_umap_clusters(embedding, labels),
        "profile": plot_cluster_profile(zscores),
        "cluster_map": plot_cluster_map(geodata),
        "lisa": plot_lisa_map(geodata, "lisa_class", "Teste"),
    }
    for name, figure in figures.items():
        outputs = save_figure(figure, name, tmp_path / "figures")
        assert all(path.is_file() and path.stat().st_size > 0 for path in outputs)
        assert {path.suffix for path in outputs} == {".png", ".svg"}
