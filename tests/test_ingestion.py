"""Testes da ingestão: download idempotente, manifesto e URLs."""

import pytest
import requests

from exceptions import IngestionError
from ingestion import downloader
from ingestion.censo_escolar import censo_escolar_url, censo_escolar_zip_path
from ingestion.downloader import download_file
from ingestion.ideb import ideb_path
from ingestion.manifest import read_manifest
from ingestion.sidra import build_sidra_url, sidra_path


class FakeResponse:
    """Resposta HTTP mínima compatível com ``requests.get(..., stream=True)``."""

    def __init__(self, payload: bytes, status_error: bool = False) -> None:
        self.payload = payload
        self.status_error = status_error
        self.status_code = 200

    def __enter__(self) -> "FakeResponse":
        return self

    def __exit__(self, *exc_info) -> None:
        return None

    def raise_for_status(self) -> None:
        if self.status_error:
            raise requests.HTTPError("404")

    def iter_content(self, chunk_size: int):
        for start in range(0, len(self.payload), chunk_size):
            yield self.payload[start : start + chunk_size]


@pytest.fixture
def fake_get(monkeypatch):
    """Substitui ``requests.get`` e conta as chamadas."""
    calls: list[str] = []

    def _get(url, **kwargs):
        calls.append(url)
        return FakeResponse(b"conteudo-de-teste")

    monkeypatch.setattr(downloader.requests, "get", _get)
    return calls


@pytest.mark.smoke
def test_download_is_idempotent(tmp_path, fake_get):
    """A segunda execução usa o cache e não faz nova requisição."""
    destination = tmp_path / "fonte" / "2023" / "arquivo.zip"
    first = download_file("https://exemplo/arquivo.zip", destination)
    second = download_file("https://exemplo/arquivo.zip", destination)

    assert len(fake_get) == 1
    assert first.sha256 == second.sha256
    assert destination.read_bytes() == b"conteudo-de-teste"
    assert "arquivo.zip" in read_manifest(destination.parent)


def test_force_downloads_again(tmp_path, fake_get):
    """``force=True`` ignora o cache."""
    destination = tmp_path / "arquivo.bin"
    download_file("https://exemplo/a", destination)
    download_file("https://exemplo/a", destination, force=True)
    assert len(fake_get) == 2


def test_corrupted_cache_is_downloaded_again(tmp_path, fake_get):
    """Arquivo alterado após o registro (hash divergente) é baixado de novo."""
    destination = tmp_path / "arquivo.bin"
    download_file("https://exemplo/a", destination)
    destination.write_bytes(b"corrompido")
    entry = download_file("https://exemplo/a", destination)
    assert len(fake_get) == 2
    assert destination.read_bytes() == b"conteudo-de-teste"
    assert entry.size_bytes == len(b"conteudo-de-teste")


def test_http_error_leaves_no_partial_file(tmp_path, monkeypatch):
    """Falha HTTP levanta IngestionError e não deixa .part nem destino."""
    monkeypatch.setattr(
        downloader.requests, "get", lambda url, **kwargs: FakeResponse(b"", status_error=True)
    )
    destination = tmp_path / "arquivo.bin"
    with pytest.raises(IngestionError):
        download_file("https://exemplo/404", destination)
    assert not destination.exists()
    assert not list(tmp_path.glob("*.part"))


def test_transient_failure_is_retried(tmp_path, monkeypatch):
    """Conexão resetada é repetida e o download conclui sem erro."""
    monkeypatch.setattr(downloader.time, "sleep", lambda _: None)
    attempts = []

    def _get(url, **kwargs):
        attempts.append(url)
        if len(attempts) < 3:
            raise requests.ConnectionError("reset")
        return FakeResponse(b"conteudo-de-teste")

    monkeypatch.setattr(downloader.requests, "get", _get)
    destination = tmp_path / "arquivo.bin"
    download_file("https://exemplo/a", destination)
    assert len(attempts) == 3
    assert destination.read_bytes() == b"conteudo-de-teste"


def test_retries_exhausted_raises(tmp_path, monkeypatch):
    """Após esgotar as tentativas, levanta IngestionError sem deixar .part."""
    monkeypatch.setattr(downloader.time, "sleep", lambda _: None)

    def _get(url, **kwargs):
        raise requests.ConnectionError("reset")

    monkeypatch.setattr(downloader.requests, "get", _get)
    with pytest.raises(IngestionError):
        download_file("https://exemplo/a", tmp_path / "a.bin", retries=2)
    assert not list(tmp_path.glob("*.part"))


def test_source_urls_and_paths(settings, tmp_paths):
    """URLs e caminhos bronze seguem o ano de referência configurado."""
    assert str(settings.reference.censo_escolar) in censo_escolar_url(settings)
    assert censo_escolar_zip_path(settings, tmp_paths).parent.name == str(
        settings.reference.censo_escolar
    )
    assert ideb_path(settings, tmp_paths, "early_years").suffix in {".xlsx", ".zip"}
    url = build_sidra_url(settings, "population")
    assert "/n6/all/" in url
    assert url.endswith(f"/p/{settings.reference.sidra_population}")
    assert sidra_path(settings, tmp_paths, "gdp").suffix == ".json"
