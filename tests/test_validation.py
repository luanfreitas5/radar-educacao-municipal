"""Testes dos contratos de dados e dos testes de integridade."""

import polars as pl
import pytest
from hypothesis import given
from hypothesis import strategies as st

from config.settings import IntegrityConfig
from exceptions import DataValidationError, IntegrityError
from schemas.silver import IDEB_SCHEMA, SIDRA_SCHEMA
from validation.contracts import validate_contract
from validation.integrity import (
    assert_integrity,
    check_integrity,
    compute_coverage,
    compute_null_share,
    count_duplicate_keys,
    count_orphan_keys,
)


@pytest.mark.smoke
def test_contract_accepts_valid_table():
    """Tabela dentro das faixas e com chave de 7 dígitos é aceita."""
    df = pl.DataFrame(
        {"code_muni": [1100015], "ideb_early_years": [5.5], "ideb_late_years": [None]},
        schema={
            "code_muni": pl.Int64,
            "ideb_early_years": pl.Float64,
            "ideb_late_years": pl.Float64,
        },
    )
    assert validate_contract(df, IDEB_SCHEMA, "teste").height == 1


@pytest.mark.parametrize("bad_code", [110015, 11000150], ids=["seis_digitos", "oito_digitos"])
def test_contract_rejects_key_without_seven_digits(bad_code):
    """Códigos de 6 ou 8 dígitos (erro clássico de junção) são barrados."""
    df = pl.DataFrame(
        {"code_muni": [bad_code], "ideb_early_years": [5.5], "ideb_late_years": [5.0]}
    )
    with pytest.raises(DataValidationError):
        validate_contract(df, IDEB_SCHEMA, "teste")


def test_contract_rejects_duplicate_keys_and_out_of_range_values():
    """Chave duplicada e nota fora de 0-10 violam o contrato."""
    duplicated = pl.DataFrame(
        {
            "code_muni": [1100015, 1100015],
            "ideb_early_years": [5.0, 6.0],
            "ideb_late_years": [1.0, 2.0],
        }
    )
    with pytest.raises(DataValidationError):
        validate_contract(duplicated, IDEB_SCHEMA, "teste")

    out_of_range = pl.DataFrame(
        {"code_muni": [1100015], "ideb_early_years": [11.0], "ideb_late_years": [2.0]}
    )
    with pytest.raises(DataValidationError):
        validate_contract(out_of_range, IDEB_SCHEMA, "teste")


def test_contract_rejects_unexpected_column():
    """strict=True rejeita colunas inesperadas."""
    df = pl.DataFrame(
        {
            "code_muni": [1100015],
            "population": [100.0],
            "area_km2": [1.0],
            "population_density": [100.0],
            "gdp_per_capita": [1.0],
            "extra": [1],
        }
    )
    with pytest.raises(DataValidationError):
        validate_contract(df, SIDRA_SCHEMA, "teste")


def test_coverage_duplicates_orphans_and_nulls():
    """Funções elementares de integridade em uma base pequena."""
    gold = pl.DataFrame({"code_muni": [1, 2, 2, 4], "valor": [1.0, None, 3.0, None]})
    assert compute_coverage(gold, "valor") == pytest.approx(0.5)
    assert count_duplicate_keys(gold) == 2
    assert compute_null_share(gold) == {"code_muni": 0.0, "valor": 0.5}
    source = pl.DataFrame({"code_muni": [1, 99]})
    assert count_orphan_keys(source, gold["code_muni"]) == 1
    assert compute_coverage(pl.DataFrame({"valor": []}, schema={"valor": pl.Float64}), "valor") == 0


def _config(**overrides) -> IntegrityConfig:
    base = {"min_coverage": {"valor": 0.9}, "max_null_share": 0.2, "null_share_overrides": {}}
    return IntegrityConfig(**{**base, **overrides})


def test_integrity_passes_on_clean_data():
    """Base completa e sem duplicatas é aprovada."""
    gold = pl.DataFrame({"code_muni": [1, 2, 3], "valor": [1.0, 2.0, 3.0]})
    report = check_integrity(gold, {"fonte": gold.select("code_muni")}, _config())
    assert report.passed
    assert_integrity(report)
    assert report.to_dict()["passed"] is True


def test_integrity_reports_every_violation():
    """Cobertura baixa, nulos e duplicatas aparecem como violações; o assert levanta."""
    gold = pl.DataFrame({"code_muni": [1, 2, 3, 3], "valor": [1.0, None, None, 4.0]})
    report = check_integrity(gold, {"fonte": pl.DataFrame({"code_muni": [1, 1, 9]})}, _config())

    assert not report.passed
    text = " | ".join(report.violations)
    assert "duplicadas em 'gold'" in text
    assert "duplicadas em 'fonte'" in text
    assert "cobertura de 'valor'" in text
    assert "nulos em 'valor'" in text
    assert report.orphan_keys["fonte"] == 1
    with pytest.raises(IntegrityError):
        assert_integrity(report)


def test_null_share_override_relaxes_threshold():
    """A exceção por coluna tem precedência sobre o limite padrão."""
    gold = pl.DataFrame({"code_muni": [1, 2, 3, 4], "valor": [1.0, None, None, 4.0]})
    config = _config(min_coverage={"valor": 0.4}, null_share_overrides={"valor": 0.6})
    assert check_integrity(gold, {}, config).passed


@given(st.lists(st.one_of(st.none(), st.floats(allow_nan=False)), max_size=50))
def test_null_share_is_a_valid_fraction(values):
    """Invariante: a fração de nulos está sempre em [0, 1]."""
    df = pl.DataFrame({"valor": values}, schema={"valor": pl.Float64})
    assert 0.0 <= compute_null_share(df)["valor"] <= 1.0
