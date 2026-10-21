"""Agregação do Censo Escolar (escola) para município."""

import logging
import re
import shutil
import zipfile
from pathlib import Path

import polars as pl

from constants.columns import CENSO_FLAG_COLUMNS, CENSO_RAW_COLUMNS, KEY
from exceptions import DataValidationError

logger = logging.getLogger(__name__)

_CSV_PATTERN = re.compile(r"microdados_ed_basica_\d{4}\.csv$", re.IGNORECASE)
ACTIVE_SCHOOL = 1
MUNICIPAL_NETWORK = 3
RURAL_LOCATION = 2


def extract_censo_csv(zip_path: Path, staging_dir: Path) -> Path:
    """Extrai o CSV da Educação Básica do ``.zip`` para a área de staging.

    A extração é idempotente: se o arquivo já existe com o mesmo tamanho, é
    reaproveitado. O bronze (o ``.zip``) nunca é modificado.

    Parameters
    ----------
    zip_path : Path
        Arquivo ``.zip`` dos microdados na camada bronze.
    staging_dir : Path
        Diretório temporário (descartável) para o CSV extraído.

    Returns
    -------
    Path
        Caminho do CSV extraído.

    Raises
    ------
    DataValidationError
        Se o ``.zip`` não contiver o CSV ``microdados_ed_basica_AAAA.csv``.
    """
    staging_dir.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(zip_path) as archive:
        members = [name for name in archive.namelist() if _CSV_PATTERN.search(name)]
        if not members:
            raise DataValidationError(
                f"CSV 'microdados_ed_basica_AAAA.csv' não encontrado em {zip_path.name}"
            )
        member = members[0]
        target = staging_dir / Path(member).name  # só o nome: evita path traversal
        if target.exists() and target.stat().st_size == archive.getinfo(member).file_size:
            logger.info("CSV já extraído, reaproveitando: %s", target.name)
            return target
        logger.info("Extraindo %s", member)
        with archive.open(member) as source, target.open("wb") as sink:
            shutil.copyfileobj(source, sink)
    return target


def scan_schools(csv_path: Path) -> pl.LazyFrame:
    """Abre o CSV de escolas de forma lazy, mantendo só as colunas necessárias.

    O arquivo do INEP usa ``;`` e ISO-8859-1; como só colunas numéricas são
    lidas, a decodificação ``utf8-lossy`` é suficiente e permite o modo lazy.

    Parameters
    ----------
    csv_path : Path
        CSV extraído do Censo Escolar.

    Returns
    -------
    pl.LazyFrame
        Colunas de ``CENSO_RAW_COLUMNS`` convertidas para inteiro.

    Raises
    ------
    DataValidationError
        Se alguma coluna esperada não existir (dicionário de dados mudou).
    """
    lazy = pl.scan_csv(csv_path, separator=";", encoding="utf8-lossy", infer_schema_length=0)
    missing = set(CENSO_RAW_COLUMNS) - set(lazy.collect_schema().names())
    if missing:
        raise DataValidationError(
            f"Colunas ausentes no Censo Escolar: {sorted(missing)}. "
            "Confira o dicionário de dados do ano de referência."
        )
    return lazy.select(CENSO_RAW_COLUMNS).with_columns(pl.all().cast(pl.Int64, strict=False))


def aggregate_schools_by_municipality(schools: pl.LazyFrame | pl.DataFrame) -> pl.DataFrame:
    """Agrega escolas em atividade por município.

    As proporções (``*_share``) são médias de indicadores 0/1 entre as escolas
    em atividade; valores nulos do indicador são ignorados na média.

    Parameters
    ----------
    schools : pl.LazyFrame or pl.DataFrame
        Escolas com as colunas de ``CENSO_RAW_COLUMNS`` já numéricas.

    Returns
    -------
    pl.DataFrame
        Uma linha por município, ordenada por ``code_muni``.

    Examples
    --------
    >>> aggregate_schools_by_municipality(schools).columns[:2]  # doctest: +SKIP
    ['code_muni', 'n_schools']
    """
    active = schools.lazy().filter(pl.col("TP_SITUACAO_FUNCIONAMENTO") == ACTIVE_SCHOOL)
    aggregated = active.group_by("CO_MUNICIPIO").agg(
        pl.len().cast(pl.Int64).alias("n_schools"),
        pl.col("QT_MAT_BAS").sum().cast(pl.Int64).alias("enrollments"),
        pl.col("QT_DOC_BAS").sum().cast(pl.Int64).alias("teachers"),
        (pl.col("TP_LOCALIZACAO") == RURAL_LOCATION).mean().alias("rural_share"),
        (pl.col("TP_DEPENDENCIA") == MUNICIPAL_NETWORK).mean().alias("municipal_network_share"),
        *[
            pl.col(raw).cast(pl.Float64).mean().alias(name)
            for raw, name in CENSO_FLAG_COLUMNS.items()
        ],
    )
    return (
        aggregated.with_columns(
            pl.when(pl.col("teachers") > 0)
            .then(pl.col("enrollments") / pl.col("teachers"))
            .alias("students_per_teacher"),
            (pl.col("enrollments") / pl.col("n_schools")).alias("enrollments_per_school"),
        )
        .rename({"CO_MUNICIPIO": KEY})
        .sort(KEY)
        .collect()
    )


def build_censo_silver(zip_path: Path, staging_dir: Path) -> pl.DataFrame:
    """Gera a tabela silver do Censo Escolar a partir do ``.zip`` da camada bronze.

    Parameters
    ----------
    zip_path : Path
        ``.zip`` dos microdados na camada bronze.
    staging_dir : Path
        Diretório temporário para extração do CSV.

    Returns
    -------
    pl.DataFrame
        Indicadores por município (um registro por ``code_muni``).
    """
    csv_path = extract_censo_csv(zip_path, staging_dir)
    return aggregate_schools_by_municipality(scan_schools(csv_path))
