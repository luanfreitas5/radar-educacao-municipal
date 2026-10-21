"""Carrega e valida em tempo de execução os YAML de ``configs/`` com Pydantic.

Uma configuração inválida falha na inicialização, com erro tipado em pt-BR,
nunca no meio do pipeline. Não há segredos neste projeto (todas as fontes são
públicas), portanto não se usa ``.env``.
"""

import logging
from pathlib import Path
from typing import Any, Literal

import yaml
from pydantic import BaseModel, ConfigDict, Field, ValidationError, model_validator

from config.paths import CONFIG_DIR, PathsConfig
from exceptions import ConfigurationError

logger = logging.getLogger(__name__)

CONFIG_FILES = (
    "config.yaml",
    "paths.yaml",
    "logging.yaml",
    "data_sources.yaml",
    "model_params.yaml",
)


class _FrozenModel(BaseModel):
    """Base: rejeita campos desconhecidos e torna a configuração imutável."""

    model_config = ConfigDict(extra="forbid", frozen=True)


class ProjectConfig(_FrozenModel):
    """Identificação do projeto e semente global."""

    name: str
    random_seed: int = 42


class ReferenceYears(_FrozenModel):
    """Ano de referência de cada fonte de dados."""

    censo_escolar: int
    ideb: int
    sidra_population: int
    sidra_gdp: int
    geobr: int


class IntegrityConfig(_FrozenModel):
    """Limiares dos testes de integridade da base municipal."""

    min_coverage: dict[str, float]
    max_null_share: float = Field(default=0.02, ge=0, le=1)
    null_share_overrides: dict[str, float] = Field(default_factory=dict)

    @model_validator(mode="after")
    def _check_fractions(self) -> "IntegrityConfig":
        """Garante que todos os limiares estejam entre 0 e 1."""
        values = [*self.min_coverage.values(), *self.null_share_overrides.values()]
        if any(not 0 <= value <= 1 for value in values):
            raise ValueError("limiares de cobertura e nulos devem estar entre 0 e 1")
        return self


class LoggingConfig(_FrozenModel):
    """Nível de log."""

    level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = "INFO"


class SidraTable(_FrozenModel):
    """Tabela da API SIDRA a ser consultada."""

    table: int
    variables: dict[str, str]
    reference: Literal["sidra_population", "sidra_gdp"]


class DataSourcesConfig(_FrozenModel):
    """URLs e parâmetros de download das fontes."""

    request_timeout_seconds: int = Field(default=120, gt=0)
    censo_escolar_url: str
    ideb_urls: dict[Literal["early_years", "late_years"], str]
    ideb_network: str
    sidra_base_url: str
    sidra_tables: dict[Literal["population", "gdp"], SidraTable]


class ClusteringConfig(_FrozenModel):
    """Hiperparâmetros da clusterização."""

    features: list[str] = Field(min_length=2)
    log_features: list[str] = Field(default_factory=list)
    outcomes: list[str]
    k_min: int = Field(default=3, ge=2)
    k_max: int = Field(default=10, ge=2)
    k: int | None = Field(default=None, ge=2)
    n_init: int = Field(default=20, gt=0)
    stability_repeats: int = Field(default=30, gt=0)
    subsample_fraction: float = Field(default=0.8, gt=0, lt=1)
    bootstrap_resamples: int = Field(default=2000, gt=0)
    min_slice_size: int = Field(default=10, gt=0)

    @model_validator(mode="after")
    def _check_consistency(self) -> "ClusteringConfig":
        """Valida a faixa de k e a coerência entre listas de variáveis."""
        if self.k_min > self.k_max:
            raise ValueError("k_min não pode ser maior que k_max")
        unknown = set(self.log_features) - set(self.features)
        if unknown:
            raise ValueError(f"log_features fora de features: {sorted(unknown)}")
        return self


class UmapConfig(_FrozenModel):
    """Hiperparâmetros do UMAP (usado apenas para visualização)."""

    n_neighbors: int = Field(default=15, gt=1)
    min_dist: float = Field(default=0.1, ge=0)


class SpatialConfig(_FrozenModel):
    """Parâmetros da análise espacial."""

    variables: list[str] = Field(min_length=1)
    primary_variable: str
    permutations: int = Field(default=999, gt=0)
    alpha: float = Field(default=0.05, gt=0, lt=1)
    apply_fdr: bool = True

    @model_validator(mode="after")
    def _check_primary(self) -> "SpatialConfig":
        """Exige que a variável principal esteja entre as analisadas."""
        if self.primary_variable not in self.variables:
            raise ValueError("primary_variable deve constar em variables")
        return self


class Settings(_FrozenModel):
    """Configuração global do projeto, validada."""

    project: ProjectConfig
    reference: ReferenceYears
    integrity: IntegrityConfig
    paths: PathsConfig
    logging: LoggingConfig
    data_sources: DataSourcesConfig
    clustering: ClusteringConfig
    umap: UmapConfig
    spatial: SpatialConfig


def _read_yaml(path: Path) -> dict[str, Any]:
    """Lê um arquivo YAML e devolve seu conteúdo como dicionário."""
    if not path.is_file():
        raise ConfigurationError(f"Arquivo de configuração não encontrado: {path}")
    try:
        content = yaml.safe_load(path.read_text(encoding="utf-8"))
    except yaml.YAMLError as exc:
        raise ConfigurationError(f"YAML inválido em {path}: {exc}") from exc
    if not isinstance(content, dict):
        raise ConfigurationError(f"O arquivo {path} deve conter um mapeamento na raiz")
    return content


def load_settings(config_dir: Path = CONFIG_DIR) -> Settings:
    """Carrega todos os YAML de configuração e os valida com Pydantic.

    Parameters
    ----------
    config_dir : Path, optional
        Diretório com os arquivos YAML, by default ``configs/``.

    Returns
    -------
    Settings
        Configuração validada e imutável.

    Raises
    ------
    ConfigurationError
        Se um arquivo estiver ausente, malformado, repetir uma seção ou
        violar o esquema.

    Examples
    --------
    >>> settings = load_settings()
    >>> settings.project.random_seed
    42
    """
    merged: dict[str, Any] = {}
    for filename in CONFIG_FILES:
        section = _read_yaml(config_dir / filename)
        repeated = merged.keys() & section.keys()
        if repeated:
            raise ConfigurationError(f"Seções repetidas em {filename}: {sorted(repeated)}")
        merged.update(section)
    try:
        return Settings(**merged)
    except ValidationError as exc:
        raise ConfigurationError(f"Configuração inválida:\n{exc}") from exc
