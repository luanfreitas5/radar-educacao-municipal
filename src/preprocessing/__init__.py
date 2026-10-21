"""Transformação bronze -> silver e integração silver -> gold.

Módulos
-------
censo
    Extrai o CSV do ``.zip`` e agrega as escolas por município.
ideb
    Lê as planilhas XLSX do IDEB e extrai a nota da rede pública por município.
sidra
    Converte o JSON da API SIDRA em colunas por município.
geo
    Lê a malha municipal e adiciona a região do IBGE.
integration
    Junta as tabelas silver pelo código de 7 dígitos (:func:`build_municipality_table`).
"""
