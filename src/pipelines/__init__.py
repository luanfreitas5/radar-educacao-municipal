"""Etapas ponta a ponta do pipeline, orquestradas por ``src/main.py``.

Módulos
-------
ingestion
    :func:`run_ingestion` — fontes -> bronze.
silver
    :func:`run_silver` — bronze -> silver (limpeza, agregação e contratos).
gold
    :func:`run_gold` — silver -> gold (junção e testes de integridade).
clustering
    :func:`run_clustering` — padronização, KMeans, UMAP e perfil.
spatial
    :func:`run_spatial` — vizinhança, Moran, LISA e mapas.
report
    :func:`run_report` — relatório Markdown.
"""
