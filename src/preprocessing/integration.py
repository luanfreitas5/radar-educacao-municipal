"""Integração das tabelas silver pelo código de município de 7 dígitos."""

import polars as pl

from constants.columns import KEY
from exceptions import DataValidationError


def build_municipality_table(
    universe: pl.DataFrame,
    censo: pl.DataFrame,
    ideb: pl.DataFrame,
    sidra: pl.DataFrame,
) -> pl.DataFrame:
    """Une as fontes à malha municipal com junções à esquerda.

    A malha define o universo de municípios (uma linha cada): municípios sem
    dados em uma fonte ficam com nulos, quantificados depois pelos testes de
    integridade, em vez de desaparecerem silenciosamente por uma junção interna.

    Parameters
    ----------
    universe : pl.DataFrame
        Atributos da malha (``code_muni``, ``name_muni``, ``abbrev_state``, ``region``).
    censo : pl.DataFrame
        Indicadores do Censo Escolar por município.
    ideb : pl.DataFrame
        IDEB por município.
    sidra : pl.DataFrame
        Indicadores do IBGE por município.

    Returns
    -------
    pl.DataFrame
        Uma linha por município da malha, ordenada por ``code_muni``.

    Raises
    ------
    DataValidationError
        Se alguma junção alterar o número de linhas (chaves duplicadas).
    """
    result = universe
    for table in (censo, ideb, sidra):
        result = result.join(table, on=KEY, how="left", validate="1:1")
    if result.height != universe.height:
        raise DataValidationError("A junção alterou o número de municípios da malha")
    return result.sort(KEY)
