"""Testes de integridade da base municipal: cobertura, duplicatas e nulos."""

import logging
from collections.abc import Mapping
from dataclasses import asdict, dataclass, field

import polars as pl

from config.settings import IntegrityConfig
from constants.columns import KEY
from exceptions import IntegrityError

logger = logging.getLogger(__name__)


@dataclass
class IntegrityReport:
    """Resultado quantificado dos testes de integridade."""

    n_municipalities: int
    coverage: dict[str, float] = field(default_factory=dict)
    duplicate_keys: dict[str, int] = field(default_factory=dict)
    orphan_keys: dict[str, int] = field(default_factory=dict)
    null_share: dict[str, float] = field(default_factory=dict)
    violations: list[str] = field(default_factory=list)

    @property
    def passed(self) -> bool:
        """Verdadeiro quando nenhuma violação foi registrada."""
        return not self.violations

    def to_dict(self) -> dict[str, object]:
        """Serializa o relatório (inclui o status) para JSON."""
        return {**asdict(self), "passed": self.passed}


def compute_coverage(df: pl.DataFrame, column: str) -> float:
    """Fração de linhas com valor não nulo em ``column``.

    Parameters
    ----------
    df : pl.DataFrame
        Base municipal (uma linha por município da malha).
    column : str
        Coluna indicadora da fonte.

    Returns
    -------
    float
        Cobertura entre 0 e 1 (0 para tabela vazia).
    """
    if df.height == 0:
        return 0.0
    return 1.0 - df[column].null_count() / df.height


def count_duplicate_keys(df: pl.DataFrame, key: str = KEY) -> int:
    """Número de linhas cuja chave aparece mais de uma vez."""
    return int(df.select(pl.col(key).is_duplicated().sum()).item())


def count_orphan_keys(source: pl.DataFrame, universe: pl.Series, key: str = KEY) -> int:
    """Número de chaves de uma fonte ausentes da malha municipal.

    Chaves órfãs costumam indicar código com 6 dígitos, malha de outro ano ou
    município extinto/criado entre as bases.
    """
    return int(source.select(~pl.col(key).is_in(universe.implode())).to_series().sum())


def compute_null_share(df: pl.DataFrame) -> dict[str, float]:
    """Fração de nulos de cada coluna."""
    if df.height == 0:
        return dict.fromkeys(df.columns, 1.0)
    return {name: df[name].null_count() / df.height for name in df.columns}


def check_integrity(
    gold: pl.DataFrame,
    sources: Mapping[str, pl.DataFrame],
    config: IntegrityConfig,
) -> IntegrityReport:
    """Executa os testes de integridade e acumula as violações.

    Verifica: (1) duplicatas de chave na base final e em cada fonte; (2) chaves
    órfãs de cada fonte em relação à malha; (3) cobertura mínima por fonte;
    (4) fração máxima de nulos por coluna.

    Parameters
    ----------
    gold : pl.DataFrame
        Base municipal integrada (uma linha por município da malha).
    sources : Mapping[str, pl.DataFrame]
        Tabelas silver por nome de fonte, para duplicatas e órfãs.
    config : IntegrityConfig
        Limiares de cobertura e nulos.

    Returns
    -------
    IntegrityReport
        Relatório com métricas e lista de violações (vazia se aprovado).
    """
    report = IntegrityReport(n_municipalities=gold.height)
    universe = gold[KEY]

    report.duplicate_keys["gold"] = count_duplicate_keys(gold)
    for name, table in sources.items():
        report.duplicate_keys[name] = count_duplicate_keys(table)
        report.orphan_keys[name] = count_orphan_keys(table, universe)
    for name, count in report.duplicate_keys.items():
        if count:
            report.violations.append(f"{count} chaves duplicadas em '{name}'")

    for column, minimum in config.min_coverage.items():
        coverage = compute_coverage(gold, column)
        report.coverage[column] = coverage
        if coverage < minimum:
            report.violations.append(
                f"cobertura de '{column}' = {coverage:.1%} abaixo do mínimo de {minimum:.1%}"
            )

    report.null_share = compute_null_share(gold)
    for column, share in report.null_share.items():
        limit = config.null_share_overrides.get(column, config.max_null_share)
        if share > limit:
            report.violations.append(
                f"{share:.1%} de nulos em '{column}' acima do limite de {limit:.1%}"
            )

    return report


def assert_integrity(report: IntegrityReport) -> None:
    """Levanta :class:`IntegrityError` se o relatório contiver violações.

    Parameters
    ----------
    report : IntegrityReport
        Relatório retornado por :func:`check_integrity`.

    Raises
    ------
    IntegrityError
        Se houver ao menos uma violação.
    """
    if report.passed:
        logger.info("Testes de integridade aprovados (%d municípios)", report.n_municipalities)
        return
    for violation in report.violations:
        logger.error("Integridade: %s", violation)
    raise IntegrityError("Testes de integridade reprovados:\n- " + "\n- ".join(report.violations))
