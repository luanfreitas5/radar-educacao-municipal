"""Aplicação de contratos de dados pandera com erros em pt-BR."""

import logging

import pandera.polars as pa
import polars as pl
from pandera.errors import SchemaError, SchemaErrors

from exceptions import DataValidationError

logger = logging.getLogger(__name__)


def validate_contract(df: pl.DataFrame, schema: pa.DataFrameSchema, name: str) -> pl.DataFrame:
    """Valida ``df`` contra o contrato e falha cedo se houver violação.

    Parameters
    ----------
    df : pl.DataFrame
        Tabela a validar.
    schema : pa.DataFrameSchema
        Contrato de dados da camada.
    name : str
        Nome legível da tabela, usado nas mensagens.

    Returns
    -------
    pl.DataFrame
        A própria tabela, validada.

    Raises
    ------
    DataValidationError
        Se a tabela violar o contrato (tipos, faixas, unicidade, colunas).
    """
    try:
        validated = schema.validate(df)
    except (SchemaError, SchemaErrors) as exc:
        logger.exception("Contrato de dados violado em %s", name)
        raise DataValidationError(f"Contrato de dados violado em '{name}': {exc}") from exc
    logger.info("Contrato validado: %s (%d linhas)", name, df.height)
    return validated
