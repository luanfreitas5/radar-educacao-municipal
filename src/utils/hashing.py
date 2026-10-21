"""Hash de arquivos para rastrear a versão dos dados."""

import hashlib
from pathlib import Path


def hash_file(path: Path, chunk_size: int = 1 << 20) -> str:
    """Calcula o SHA-256 de um arquivo lendo-o em blocos (baixo uso de memória).

    Parameters
    ----------
    path : Path
        Arquivo a ser verificado.
    chunk_size : int, optional
        Tamanho do bloco de leitura em bytes, by default 1 MiB.

    Returns
    -------
    str
        Hash SHA-256 em hexadecimal.

    Raises
    ------
    FileNotFoundError
        Se o arquivo não existir.
    """
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(chunk_size), b""):
            digest.update(chunk)
    return digest.hexdigest()
