"""Clusterização de municípios, projeção UMAP e perfil dos clusters.

Módulos
-------
clustering
    Matriz de atributos (log + padronização), seleção de k, KMeans e estabilidade.
embedding
    :func:`compute_umap` (somente para visualização).
profiling
    Perfil por cluster, teste de Kruskal-Wallis e IC bootstrap do desfecho.
"""
