"""Testes da agregação do Censo Escolar, IDEB, SIDRA e da integração."""

import io
import zipfile

import polars as pl
import pytest

from exceptions import DataValidationError
from preprocessing.censo import (
    aggregate_schools_by_municipality,
    extract_censo_csv,
    scan_schools,
)
from preprocessing.ideb import build_ideb_silver, parse_ideb_sheet, resolve_workbook
from preprocessing.integration import build_municipality_table
from preprocessing.sidra import build_sidra_silver, parse_sidra_records
from schemas.silver import CENSO_SCHEMA, IDEB_SCHEMA, SIDRA_SCHEMA
from validation.contracts import validate_contract


@pytest.mark.smoke
def test_aggregation_ignores_inactive_schools(schools):
    """Escolas paralisadas não entram na contagem nem nas proporções."""
    result = aggregate_schools_by_municipality(schools).sort("code_muni")
    first = result.row(0, named=True)

    assert result["code_muni"].to_list() == [1100015, 1100023]
    assert first["n_schools"] == 2
    assert first["enrollments"] == 150
    assert first["rural_share"] == pytest.approx(0.5)
    assert first["municipal_network_share"] == pytest.approx(0.5)
    assert first["internet_share"] == pytest.approx(0.5)
    assert first["students_per_teacher"] == pytest.approx(15.0)
    assert first["enrollments_per_school"] == pytest.approx(75.0)


def test_students_per_teacher_is_null_without_teachers(schools):
    """Município sem docentes registrados fica com razão nula, não infinita."""
    result = aggregate_schools_by_municipality(schools).filter(pl.col("code_muni") == 1100023)
    assert result["students_per_teacher"].to_list() == [None]


def test_aggregation_satisfies_silver_contract(schools):
    """A saída agregada cumpre o contrato da camada silver."""
    validate_contract(aggregate_schools_by_municipality(schools), CENSO_SCHEMA, "teste")


def test_scan_schools_reads_latin1_semicolon_csv(tmp_path, schools):
    """CSV no formato do INEP (; e ISO-8859-1) é lido e convertido para inteiros."""
    csv_path = tmp_path / "microdados_ed_basica_2023.csv"
    text = schools.with_columns(pl.lit("Escola Açaí").alias("NO_ENTIDADE")).write_csv(separator=";")
    csv_path.write_bytes(text.encode("latin-1"))

    result = scan_schools(csv_path).collect()
    assert result.height == schools.height
    assert result.schema["CO_MUNICIPIO"] == pl.Int64


def test_scan_schools_reports_missing_columns(tmp_path):
    """Coluna ausente (dicionário mudou) gera erro explicativo."""
    csv_path = tmp_path / "microdados_ed_basica_2023.csv"
    csv_path.write_text("CO_MUNICIPIO;OUTRA\n1;2\n", encoding="utf-8")
    with pytest.raises(DataValidationError, match="Colunas ausentes"):
        scan_schools(csv_path).collect()


def test_extract_censo_csv_is_idempotent(tmp_path):
    """A extração acha o CSV em subpasta do zip e reaproveita o arquivo existente."""
    zip_path = tmp_path / "censo.zip"
    with zipfile.ZipFile(zip_path, "w") as archive:
        archive.writestr("Anexos/leia-me.pdf", b"x")
        archive.writestr("dados/microdados_ed_basica_2023.csv", "CO_MUNICIPIO\n1\n")

    first = extract_censo_csv(zip_path, tmp_path / "staging")
    modified = first.stat().st_mtime_ns
    second = extract_censo_csv(zip_path, tmp_path / "staging")

    assert first == second
    assert second.stat().st_mtime_ns == modified
    assert first.read_text(encoding="utf-8").startswith("CO_MUNICIPIO")


def test_extract_censo_csv_without_expected_member(tmp_path):
    """Zip sem o CSV esperado gera erro tipado."""
    zip_path = tmp_path / "censo.zip"
    with zipfile.ZipFile(zip_path, "w") as archive:
        archive.writestr("outro.csv", "a\n1\n")
    with pytest.raises(DataValidationError):
        extract_censo_csv(zip_path, tmp_path / "staging")


def _ideb_raw() -> pl.DataFrame:
    """Planilha sintética: três linhas de preâmbulo, cabeçalho e dados."""
    rows = [
        ["Fonte: INEP", None, None, None],
        ["", None, None, None],
        [None, None, None, None],
        ["SG_UF", "CO_MUNICIPIO", "REDE", "VL_OBSERVADO_2023"],
        ["RO", "1100015", "Pública", "5,8"],
        ["RO", "1100015", "Privada", "6.5"],
        ["RO", "1100023", "Pública", "-"],
        ["RO", "1100031", "Pública", "6.1"],
    ]
    return pl.DataFrame(rows, schema={f"c{i}": pl.String for i in range(4)}, orient="row")


@pytest.mark.smoke
def test_parse_ideb_sheet_filters_network_and_cleans_values():
    """Mantém só a rede pública; vírgula decimal e '-' são tratados."""
    result = parse_ideb_sheet(_ideb_raw(), 2023, "Pública", "ideb_early_years").sort("code_muni")
    assert result["code_muni"].to_list() == [1100015, 1100023, 1100031]
    assert result["ideb_early_years"].to_list() == [5.8, None, 6.1]


def test_parse_ideb_sheet_without_year_column():
    """Ano sem coluna correspondente gera erro explicativo."""
    with pytest.raises(DataValidationError, match="VL_OBSERVADO_2019"):
        parse_ideb_sheet(_ideb_raw(), 2019, "Pública", "ideb_early_years")


def test_parse_ideb_sheet_without_header():
    """Planilha sem a linha de cabeçalho é rejeitada."""
    raw = pl.DataFrame({"a": ["x"], "b": ["y"]})
    with pytest.raises(DataValidationError, match="Cabeçalho"):
        parse_ideb_sheet(raw, 2023, "Pública", "ideb_early_years")


def test_build_ideb_silver_outer_join_and_contract():
    """Municípios presentes em apenas uma etapa são mantidos; o contrato é cumprido."""
    early = parse_ideb_sheet(_ideb_raw(), 2023, "Pública", "ideb_early_years")
    late = early.rename({"ideb_early_years": "ideb_late_years"}).head(2)
    combined = build_ideb_silver(early, late)
    assert combined.height == 3
    validate_contract(combined, IDEB_SCHEMA, "teste")


def test_resolve_workbook_extracts_from_zip(tmp_path):
    """Planilha dentro de .zip é extraída; .xlsx é devolvido como está."""
    xlsx = tmp_path / "ideb.xlsx"
    xlsx.write_bytes(b"conteudo")
    assert resolve_workbook(xlsx, tmp_path / "staging") == xlsx

    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        archive.writestr("pasta/ideb.xlsx", b"conteudo")
    zip_path = tmp_path / "ideb.zip"
    zip_path.write_bytes(buffer.getvalue())
    extracted = resolve_workbook(zip_path, tmp_path / "staging")
    assert extracted.read_bytes() == b"conteudo"


def _sidra_records() -> list[dict[str, str]]:
    header = {
        "NC": "Nível Territorial (Código)",
        "V": "Valor",
        "D1C": "Município (Código)",
        "D1N": "Município",
        "D2C": "Variável (Código)",
        "D2N": "Variável",
        "D3C": "Ano (Código)",
    }

    def row(code: str, variable: str, value: str) -> dict[str, str]:
        return {"V": value, "D1C": code, "D2C": variable, "D3C": "2022"}

    return [
        header,
        row("1100015", "93", "22000"),
        row("1100015", "614", "100"),
        row("1100023", "93", "..."),
        row("1100023", "614", "50"),
    ]


@pytest.mark.smoke
def test_parse_sidra_records_pivots_variables():
    """Registros longos viram colunas; '...' vira nulo."""
    wide = parse_sidra_records(_sidra_records(), {"93": "population", "614": "area_km2"})
    wide = wide.sort("code_muni")
    assert wide["population"].to_list() == [22000.0, None]
    assert wide["area_km2"].to_list() == [100.0, 50.0]


def test_parse_sidra_records_missing_variable():
    """Variável configurada que não veio na resposta gera erro."""
    with pytest.raises(DataValidationError, match="ausentes"):
        parse_sidra_records(_sidra_records(), {"93": "population", "999": "inexistente"})


def test_parse_sidra_records_empty_response():
    """Resposta só com cabeçalho é rejeitada."""
    with pytest.raises(DataValidationError, match="vazia"):
        parse_sidra_records([_sidra_records()[0]], {"93": "population"})


def test_build_sidra_silver_computes_density_and_gdp_per_capita():
    """Densidade = população/área; PIB per capita converte mil reais em reais."""
    population = pl.DataFrame(
        {"code_muni": [1100015], "population": [20000.0], "area_km2": [100.0]}
    )
    gdp = pl.DataFrame({"code_muni": [1100015], "gdp_thousand_brl": [400_000.0]})
    result = build_sidra_silver(population, gdp)
    row = result.row(0, named=True)
    assert row["population_density"] == pytest.approx(200.0)
    assert row["gdp_per_capita"] == pytest.approx(20_000.0)
    validate_contract(result, SIDRA_SCHEMA, "teste")


def test_build_municipality_table_keeps_universe_and_flags_duplicates():
    """Junção à esquerda preserva a malha; chave duplicada em uma fonte é rejeitada."""
    universe = pl.DataFrame({"code_muni": [1100015, 1100023, 1100031]})
    censo = pl.DataFrame({"code_muni": [1100015], "n_schools": [3]})
    ideb = pl.DataFrame({"code_muni": [1100023], "ideb_early_years": [5.0]})
    sidra = pl.DataFrame({"code_muni": [1100031], "population": [10.0]})

    result = build_municipality_table(universe, censo, ideb, sidra)
    assert result.height == 3
    assert result["n_schools"].null_count() == 2

    duplicated = pl.concat([censo, censo])
    with pytest.raises(pl.exceptions.ComputeError):
        build_municipality_table(universe, duplicated, ideb, sidra)
