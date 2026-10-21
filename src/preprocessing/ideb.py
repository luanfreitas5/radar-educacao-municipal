"""Leitura das planilhas do IDEB por município."""

import logging
import shutil
import zipfile
from pathlib import Path

import polars as pl

from constants.columns import KEY
from exceptions import DataValidationError

logger = logging.getLogger(__name__)

HEADER_SEARCH_ROWS = 30
CODE_COLUMN = "CO_MUNICIPIO"
NETWORK_COLUMN = "REDE"


def resolve_workbook(path: Path, staging_dir: Path) -> Path:
    """Devolve o ``.xlsx``; se ``path`` for um ``.zip``, extrai a planilha para staging.

    Parameters
    ----------
    path : Path
        Arquivo baixado do INEP (``.xlsx`` ou ``.zip``).
    staging_dir : Path
        Diretório temporário para a planilha extraída.

    Returns
    -------
    Path
        Caminho de um arquivo ``.xlsx``.

    Raises
    ------
    DataValidationError
        Se o ``.zip`` não contiver nenhuma planilha ``.xlsx``.
    """
    if path.suffix.lower() != ".zip":
        return path
    staging_dir.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(path) as archive:
        members = [name for name in archive.namelist() if name.lower().endswith(".xlsx")]
        if not members:
            raise DataValidationError(f"Nenhuma planilha .xlsx encontrada em {path.name}")
        target = staging_dir / Path(members[0]).name
        with archive.open(members[0]) as source, target.open("wb") as sink:
            shutil.copyfileobj(source, sink)
    return target


def read_ideb_sheet(path: Path, staging_dir: Path) -> pl.DataFrame:
    """Lê a primeira aba da planilha do IDEB como texto, sem interpretar cabeçalho.

    Parameters
    ----------
    path : Path
        Planilha (``.xlsx`` ou ``.zip``) na camada bronze.
    staging_dir : Path
        Diretório temporário para extração, se necessário.

    Returns
    -------
    pl.DataFrame
        Todas as células como texto (a linha de cabeçalho é localizada depois).
    """
    workbook = resolve_workbook(path, staging_dir)
    return pl.read_excel(workbook, has_header=False, infer_schema_length=0)


def _find_header_row(raw: pl.DataFrame) -> int:
    """Localiza a linha que contém ``CO_MUNICIPIO`` (as planilhas têm preâmbulo)."""
    for index, row in enumerate(raw.head(HEADER_SEARCH_ROWS).rows()):
        if any(isinstance(cell, str) and cell.strip() == CODE_COLUMN for cell in row):
            return index
    raise DataValidationError(
        f"Cabeçalho com '{CODE_COLUMN}' não encontrado nas primeiras {HEADER_SEARCH_ROWS} linhas"
    )


def parse_ideb_sheet(
    raw: pl.DataFrame, year: int, network: str, output_column: str
) -> pl.DataFrame:
    """Extrai a nota do IDEB observada de uma rede, por município.

    Parameters
    ----------
    raw : pl.DataFrame
        Saída de :func:`read_ideb_sheet` (células como texto).
    year : int
        Ano do IDEB (define a coluna ``VL_OBSERVADO_<ano>``).
    network : str
        Rede de ensino desejada (ex.: ``"Pública"``), sem distinção de caixa.
    output_column : str
        Nome da coluna de saída.

    Returns
    -------
    pl.DataFrame
        Colunas ``code_muni`` e ``output_column``; ``"-"`` e vazios viram nulo.

    Raises
    ------
    DataValidationError
        Se faltarem colunas esperadas ou o cabeçalho não for encontrado.
    """
    header_index = _find_header_row(raw)
    header = [
        str(cell).strip() if cell is not None else f"unnamed_{position}"
        for position, cell in enumerate(raw.row(header_index))
    ]
    body = raw.slice(header_index + 1)
    body.columns = header

    value_column = f"VL_OBSERVADO_{year}"
    missing = {CODE_COLUMN, NETWORK_COLUMN, value_column} - set(header)
    if missing:
        raise DataValidationError(f"Colunas ausentes na planilha do IDEB: {sorted(missing)}")

    return (
        body.filter(pl.col(NETWORK_COLUMN).str.strip_chars().str.to_lowercase() == network.lower())
        .select(
            pl.col(CODE_COLUMN)
            .str.strip_chars()
            .str.replace(r"\.0$", "")
            .cast(pl.Int64, strict=False)
            .alias(KEY),
            pl.col(value_column)
            .str.strip_chars()
            .str.replace(",", ".")
            .cast(pl.Float64, strict=False)
            .alias(output_column),
        )
        .drop_nulls(KEY)
    )


def build_ideb_silver(early_years: pl.DataFrame, late_years: pl.DataFrame) -> pl.DataFrame:
    """Combina anos iniciais e finais em uma única tabela por município.

    Parameters
    ----------
    early_years : pl.DataFrame
        Saída de :func:`parse_ideb_sheet` com ``ideb_early_years``.
    late_years : pl.DataFrame
        Saída de :func:`parse_ideb_sheet` com ``ideb_late_years``.

    Returns
    -------
    pl.DataFrame
        Junção externa pelos códigos de município, ordenada por ``code_muni``.
    """
    return early_years.join(late_years, on=KEY, how="full", coalesce=True).sort(KEY)
