"""Configuração do projeto: caminhos, parâmetros validados e logging.

Módulos
-------
paths
    ``ROOT``, ``CONFIG_DIR``, :class:`PathsConfig` e :class:`ProjectPaths`.
settings
    :func:`load_settings` carrega e valida os YAML de ``configs/`` com Pydantic.
logging
    :func:`configure_logging` (console com rich + arquivo com rotação diária).
"""
