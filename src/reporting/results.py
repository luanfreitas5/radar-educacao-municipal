"""Persistência incremental dos resultados de cada etapa em JSON."""

import json
from pathlib import Path
from typing import Any

from exceptions import RadarError


def load_results(path: Path) -> dict[str, Any]:
    """Lê o JSON de resultados; devolve dicionário vazio se ainda não existir.

    Parameters
    ----------
    path : Path
        Arquivo ``results.json``.

    Returns
    -------
    dict[str, Any]
        Resultados acumulados das etapas anteriores.

    Raises
    ------
    RadarError
        Se o arquivo existir, mas estiver corrompido.
    """
    if not path.is_file():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise RadarError(f"Arquivo de resultados corrompido: {path}") from exc


def update_results(path: Path, section: str, content: dict[str, Any]) -> None:
    """Substitui uma seção do JSON de resultados, preservando as demais.

    Parameters
    ----------
    path : Path
        Arquivo ``results.json`` (criado se necessário).
    section : str
        Nome da seção (ex.: ``"clustering"``).
    content : dict[str, Any]
        Conteúdo serializável em JSON.
    """
    results = load_results(path)
    results[section] = content
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(results, indent=2, ensure_ascii=False), encoding="utf-8")
