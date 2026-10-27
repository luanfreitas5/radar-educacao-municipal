"""Testes da carga e validação das configurações."""

import shutil
from pathlib import Path

import pytest

from config.paths import CONFIG_DIR, build_paths
from config.settings import load_settings
from exceptions import ConfigurationError


@pytest.mark.smoke
def test_real_configuration_is_valid(settings):
    """Os YAML versionados em configs/ passam na validação Pydantic."""
    assert settings.project.random_seed == 42
    assert settings.spatial.primary_variable in settings.spatial.variables
    assert set(settings.clustering.log_features) <= set(settings.clustering.features)


@pytest.mark.smoke
def test_paths_are_resolved_against_root(settings, tmp_path):
    """Os caminhos relativos são resolvidos contra a raiz informada."""
    paths = build_paths(settings.paths, root=tmp_path)
    assert paths.bronze == tmp_path / "data" / "bronze"
    assert paths.bronze_dir("ideb", 2023) == tmp_path / "data" / "bronze" / "ideb" / "2023"


def _copy_configs(destination: Path) -> Path:
    shutil.copytree(CONFIG_DIR, destination)
    return destination


def test_unknown_field_is_rejected(tmp_path):
    """Campos desconhecidos falham na inicialização (extra='forbid')."""
    config_dir = _copy_configs(tmp_path / "configs")
    with (config_dir / "paths.yaml").open("a", encoding="utf-8") as handle:
        handle.write("  nivel_inexistente: 1\n")
    with pytest.raises(ConfigurationError):
        load_settings(config_dir)


def test_missing_file_raises(tmp_path):
    """Arquivo de configuração ausente gera erro tipado."""
    config_dir = _copy_configs(tmp_path / "configs")
    (config_dir / "paths.yaml").unlink()
    with pytest.raises(ConfigurationError, match="não encontrado"):
        load_settings(config_dir)


def test_invalid_k_range_raises(tmp_path):
    """k_min maior que k_max é rejeitado na validação."""
    config_dir = _copy_configs(tmp_path / "configs")
    path = config_dir / "model_params.yaml"
    path.write_text(path.read_text(encoding="utf-8").replace("k_min: 3", "k_min: 20"), "utf-8")
    with pytest.raises(ConfigurationError):
        load_settings(config_dir)
