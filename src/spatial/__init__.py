"""Análise espacial: vizinhança, autocorrelação (Moran/LISA) e coesão dos clusters.

Módulos
-------
weights
    :func:`build_queen_weights` (contiguidade Queen, sem ilhas).
autocorrelation
    I de Moran global e local (esda) com correção FDR.
cohesion
    Fração de vizinhos no mesmo cluster versus o esperado ao acaso.
"""
