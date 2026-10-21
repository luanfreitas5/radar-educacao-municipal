"""Ingestão idempotente das fontes para a camada bronze (imutável).

Cada fonte vira um snapshot em ``data/bronze/<fonte>/<referência>/`` com um
``manifest.json`` (URL, SHA-256, tamanho e data do download). Reexecutar não
baixa de novo arquivos cujo hash confere com o manifesto.

Módulos
-------
manifest
    :class:`ManifestEntry`, leitura/escrita do manifesto e :func:`register_file`.
downloader
    :func:`download_file` com cache local, escrita atômica e hash.
censo_escolar
    Microdados do Censo Escolar (INEP).
ideb
    Planilhas do IDEB por município (INEP).
sidra
    Tabelas da API SIDRA (IBGE).
geobr
    Malha municipal via pacote ``geobr``.
"""
