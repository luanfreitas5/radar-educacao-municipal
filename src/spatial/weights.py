"""Matriz de vizinhança por contiguidade (Queen)."""

import logging

import geopandas as gpd
from libpysal.weights import Queen, W

logger = logging.getLogger(__name__)


def build_queen_weights(geodata: gpd.GeoDataFrame) -> tuple[W, gpd.GeoDataFrame]:
    """Constrói a matriz Queen padronizada por linha, removendo municípios-ilha.

    Municípios sem vizinhos (ex.: Fernando de Noronha, ilhas oceânicas) não têm
    defasagem espacial definida e distorceriam a estatística. Eles são removidos
    e a matriz é reconstruída sobre os municípios conectados.

    Parameters
    ----------
    geodata : gpd.GeoDataFrame
        Municípios com geometria poligonal.

    Returns
    -------
    tuple[W, gpd.GeoDataFrame]
        Matriz de pesos (``transform = "r"``, ids = posição na tabela devolvida)
        e a tabela sem as ilhas, com índice reiniciado.

    Examples
    --------
    >>> weights, connected = build_queen_weights(geodata)  # doctest: +SKIP
    """
    table = geodata.reset_index(drop=True)
    weights = Queen.from_dataframe(table, use_index=True, silence_warnings=True)
    islands = list(weights.islands)  # pyright: ignore[reportAttributeAccessIssue]
    if islands:
        logger.info("Removendo %d municípios sem vizinhos (ilhas)", len(islands))
        table = table.drop(index=islands).reset_index(drop=True)
        weights = Queen.from_dataframe(table, use_index=True, silence_warnings=True)
    weights.transform = "r"  # pyright: ignore[reportAttributeAccessIssue]
    return weights, table  # pyright: ignore[reportReturnType]
