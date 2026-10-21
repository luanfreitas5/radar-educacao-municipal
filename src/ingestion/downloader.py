"""Download idempotente com cache local, escrita atômica e verificação de hash."""

import logging
import time
from pathlib import Path

import requests
import truststore

from exceptions import IngestionError
from ingestion.manifest import ManifestEntry, read_manifest, register_file
from utils.hashing import hash_file

logger = logging.getLogger(__name__)

_RETRYABLE_ERRORS = (
    requests.ConnectionError,
    requests.Timeout,
    requests.exceptions.ChunkedEncodingError,
)


def configure_system_certificates() -> None:
    """Faz o ``requests`` validar TLS com os certificados do sistema operacional.

    O servidor do INEP não envia o certificado intermediário; o repositório do
    SO o completa, ao contrário do ``certifi``. A verificação TLS continua ativa.
    """
    truststore.inject_into_ssl()


def _is_retryable(exc: requests.RequestException) -> bool:
    """Indica se a falha é transitória (rede, timeout, HTTP 429/5xx)."""
    if isinstance(exc, _RETRYABLE_ERRORS):
        return True
    status = getattr(exc.response, "status_code", None)
    return status is not None and (status == 429 or status >= 500)


def _stream_to_part(url: str, temporary: Path, timeout: int, chunk_size: int) -> None:
    """Grava ``url`` em ``temporary``, retomando de onde parou se possível."""
    offset = temporary.stat().st_size if temporary.exists() else 0
    headers = {"Range": f"bytes={offset}-"} if offset else {}
    with requests.get(url, stream=True, timeout=timeout, headers=headers) as response:
        response.raise_for_status()
        resumed = offset > 0 and response.status_code == 206
        if offset and not resumed:
            logger.warning("Servidor ignorou o Range; reiniciando o download")
        with temporary.open("ab" if resumed else "wb") as handle:
            handle.writelines(response.iter_content(chunk_size=chunk_size))


def _read_valid_cache(destination: Path, url: str, force: bool) -> ManifestEntry | None:
    """Devolve o registro do arquivo em cache se ele existir e estiver íntegro."""
    if not destination.exists() or force:
        return None
    cached = read_manifest(destination.parent).get(destination.name)
    if cached is None:
        logger.info("Arquivo já existe sem registro; registrando hash: %s", destination.name)
        return register_file(destination, url)
    if cached.sha256 == hash_file(destination):
        logger.info("Cache válido, download ignorado: %s", destination.name)
        return cached
    logger.warning("Hash divergente do manifesto; baixando novamente: %s", destination.name)
    return None


def _download_with_retries(
    url: str, temporary: Path, timeout: int, chunk_size: int, retries: int, backoff: float
) -> None:
    """Baixa para o ``.part`` repetindo falhas transitórias com espera exponencial."""
    for attempt in range(retries + 1):
        try:
            _stream_to_part(url, temporary, timeout, chunk_size)
            break
        except requests.RequestException as exc:
            if attempt < retries and _is_retryable(exc):
                wait = backoff * 2**attempt
                logger.warning(
                    "Falha transitória (%s); nova tentativa %d/%d em %.0fs",
                    type(exc).__name__,
                    attempt + 1,
                    retries,
                    wait,
                )
                time.sleep(wait)
                continue
            temporary.unlink(missing_ok=True)
            logger.exception("Falha ao baixar %s", url)
            raise IngestionError(f"Falha ao baixar {url}: {exc}") from exc


def download_file(
    url: str,
    destination: Path,
    *,
    timeout: int = 120,
    force: bool = False,
    chunk_size: int = 1 << 20,
    retries: int = 5,
    backoff: float = 2.0,
) -> ManifestEntry:
    """Baixa ``url`` para ``destination`` apenas se ainda não estiver em cache.

    O cache é válido quando o arquivo existe e seu SHA-256 confere com o
    manifesto. O download é gravado em um ``.part`` e movido de forma atômica,
    de modo que uma falha no meio nunca deixa um arquivo truncado como se
    fosse válido.

    Parameters
    ----------
    url : str
        Endereço de origem.
    destination : Path
        Arquivo de destino na camada bronze.
    timeout : int, optional
        Timeout das requisições em segundos, by default 120.
    force : bool, optional
        Ignora o cache e baixa novamente, by default False.
    chunk_size : int, optional
        Tamanho do bloco de escrita em bytes, by default 1 MiB.
    retries : int, optional
        Tentativas extras após falhas transitórias (conexão resetada, timeout,
        HTTP 429/5xx); cada nova tentativa retoma do ``.part`` via ``Range``,
        by default 5.
    backoff : float, optional
        Base da espera exponencial entre tentativas, em segundos, by default 2.0.

    Returns
    -------
    ManifestEntry
        Registro de proveniência do arquivo.

    Raises
    ------
    IngestionError
        Se a requisição falhar (rede, status HTTP de erro, timeout).

    Examples
    --------
    >>> download_file(url, Path("data/bronze/fonte/2023/arquivo.zip"))  # doctest: +SKIP
    """
    configure_system_certificates()
    destination.parent.mkdir(parents=True, exist_ok=True)

    cached = _read_valid_cache(destination, url, force)
    if cached is not None:
        return cached

    temporary = destination.with_name(destination.name + ".part")
    logger.info("Baixando %s", url)
    if force:
        temporary.unlink(missing_ok=True)
    _download_with_retries(url, temporary, timeout, chunk_size, retries, backoff)

    temporary.replace(destination)
    return register_file(destination, url)
