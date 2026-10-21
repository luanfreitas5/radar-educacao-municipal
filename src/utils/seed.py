"""Controle de aleatoriedade para reprodutibilidade."""

import os
import random

import numpy as np


def seed_everything(seed: int = 42) -> None:
    """Fixa as sementes de ``random``, ``numpy`` e ``PYTHONHASHSEED``.

    ``PYTHONHASHSEED`` só tem efeito em subprocessos; para o processo atual é
    exportado pelo ``Makefile``. A semente global do numpy também alimenta o
    ``esda.Moran`` (permutações), que não aceita ``seed`` próprio.

    Parameters
    ----------
    seed : int, optional
        Semente, by default 42.
    """
    os.environ["PYTHONHASHSEED"] = str(seed)
    random.seed(seed)
    np.random.seed(seed)  # noqa: NPY002 - necessário para o esda.Moran
