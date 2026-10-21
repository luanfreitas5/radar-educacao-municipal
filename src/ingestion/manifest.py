"""Manifesto de proveniência dos arquivos da camada bronze."""

import json
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path

from exceptions import IngestionError
from utils.hashing import hash_file

MANIFEST_NAME = "manifest.json"


@dataclass(frozen=True)
class ManifestEntry:
    """Registro de proveniência de um arquivo baixado."""

    filename: str
    url: str
    sha256: str
    size_bytes: int
    downloaded_at: str


def read_manifest(directory: Path) -> dict[str, ManifestEntry]:
    """Lê o manifesto de um diretório de snapshot.

    Parameters
    ----------
    directory : Path
        Diretório que contém (ou conterá) o ``manifest.json``.

    Returns
    -------
    dict[str, ManifestEntry]
        Entradas indexadas pelo nome do arquivo; vazio se não houver manifesto.

    Raises
    ------
    IngestionError
        Se o manifesto existir, mas estiver corrompido.
    """
    path = directory / MANIFEST_NAME
    if not path.is_file():
        return {}
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
        return {name: ManifestEntry(**entry) for name, entry in raw.items()}
    except (json.JSONDecodeError, TypeError) as exc:
        raise IngestionError(f"Manifesto corrompido: {path}") from exc


def write_manifest_entry(directory: Path, entry: ManifestEntry) -> None:
    """Insere ou atualiza uma entrada no manifesto do diretório.

    Parameters
    ----------
    directory : Path
        Diretório do snapshot.
    entry : ManifestEntry
        Entrada a registrar.
    """
    entries = read_manifest(directory)
    entries[entry.filename] = entry
    payload = {name: asdict(value) for name, value in sorted(entries.items())}
    (directory / MANIFEST_NAME).write_text(
        json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8"
    )


def register_file(path: Path, url: str) -> ManifestEntry:
    """Calcula o hash de um arquivo existente e o registra no manifesto.

    Parameters
    ----------
    path : Path
        Arquivo já gravado na camada bronze.
    url : str
        Origem do arquivo (URL ou identificador da chamada de API).

    Returns
    -------
    ManifestEntry
        Entrada registrada.
    """
    entry = ManifestEntry(
        filename=path.name,
        url=url,
        sha256=hash_file(path),
        size_bytes=path.stat().st_size,
        downloaded_at=datetime.now(timezone.utc).isoformat(timespec="seconds"),
    )
    write_manifest_entry(path.parent, entry)
    return entry
