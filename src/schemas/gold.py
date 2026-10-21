"""Contrato de dados da base municipal integrada (camada gold).

As colunas de valor aceitam nulos: a presença de dados por fonte é controlada
pelos testes de integridade (cobertura e nulos), não pelo schema, para que a
falha traga um relatório quantificado por coluna.
"""

import pandera.polars as pa

from schemas.silver import (
    censo_columns,
    geo_columns,
    ideb_column,
    key_column,
    sidra_columns,
)

GOLD_SCHEMA = pa.DataFrameSchema(
    {
        **geo_columns(),
        **censo_columns(nullable_counts=True),
        **sidra_columns(),
        "ideb_early_years": ideb_column(),
        "ideb_late_years": ideb_column(),
        "code_muni": key_column(),
    },
    strict=True,
    name="gold_municipalities",
)
