"""Regiões do IBGE e rótulos das classes LISA."""

UF_TO_REGION: dict[str, str] = {
    "AC": "Norte",
    "AP": "Norte",
    "AM": "Norte",
    "PA": "Norte",
    "RO": "Norte",
    "RR": "Norte",
    "TO": "Norte",
    "AL": "Nordeste",
    "BA": "Nordeste",
    "CE": "Nordeste",
    "MA": "Nordeste",
    "PB": "Nordeste",
    "PE": "Nordeste",
    "PI": "Nordeste",
    "RN": "Nordeste",
    "SE": "Nordeste",
    "ES": "Sudeste",
    "MG": "Sudeste",
    "RJ": "Sudeste",
    "SP": "Sudeste",
    "PR": "Sul",
    "RS": "Sul",
    "SC": "Sul",
    "DF": "Centro-Oeste",
    "GO": "Centro-Oeste",
    "MS": "Centro-Oeste",
    "MT": "Centro-Oeste",
}

REGIONS: tuple[str, ...] = ("Norte", "Nordeste", "Sudeste", "Sul", "Centro-Oeste")

# Quadrantes do esda.Moran_Local: 1 = HH, 2 = LH, 3 = LL, 4 = HL.
LISA_QUADRANT_LABELS: dict[int, str] = {
    1: "Alto-Alto",
    2: "Baixo-Alto",
    3: "Baixo-Baixo",
    4: "Alto-Baixo",
}
LISA_NOT_SIGNIFICANT = "Não significativo"
