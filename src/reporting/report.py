"""Geração do relatório final em Markdown (pt-BR) a partir dos resultados."""

from typing import Any

import polars as pl

LIMITATIONS = """\
- **Agregação municipal (falácia ecológica):** os resultados descrevem municípios, não
  escolas nem estudantes; padrões municipais não se aplicam automaticamente a indivíduos.
- **Associação, não causalidade:** as tipologias descrevem perfis e o IDEB varia entre
  elas, mas nada aqui estima o efeito de infraestrutura ou renda sobre a aprendizagem.
- **Janelas temporais distintas:** Censo Escolar, IDEB, Censo Demográfico e PIB têm anos
  de referência diferentes; o PIB per capita divide o PIB de um ano pela população de outro.
- **IDEB ausente:** municípios sem nota (poucos alunos ou participação insuficiente no Saeb)
  ficam fora da comparação do desfecho; se a ausência não for aleatória, há viés de seleção.
- **KMeans:** supõe grupos aproximadamente esféricos no espaço padronizado; o número de
  clusters foi escolhido por silhouette, critério que favorece poucos grupos. A estabilidade
  (ARI) quantifica a sensibilidade à amostra, mas não à escolha do algoritmo.
- **UMAP:** projeção apenas ilustrativa; distâncias e tamanhos no plano não são interpretáveis.
- **Contiguidade Queen:** municípios-ilha foram removidos da análise espacial; o tamanho
  e o formato irregular dos municípios afetam a definição de vizinhança (problema da
  unidade espacial modificável, MAUP).
- **LISA:** os p-valores locais usam permutações e correção FDR; os clusters indicam
  associação espacial local, não identificam a causa do agrupamento.
- **Bases públicas agregadas:** nenhum dado pessoal é processado; ainda assim, o Censo
  Escolar é autodeclarado pelas escolas e está sujeito a erros de preenchimento.
"""


def dataframe_to_markdown(df: pl.DataFrame, digits: int = 3) -> str:
    """Converte um ``pl.DataFrame`` em tabela Markdown.

    Parameters
    ----------
    df : pl.DataFrame
        Tabela a converter.
    digits : int, optional
        Casas decimais para números de ponto flutuante, by default 3.

    Returns
    -------
    str
        Tabela no formato GitHub Markdown.
    """

    def fmt(value: object) -> str:
        if value is None:
            return "—"
        if isinstance(value, float):
            return f"{value:.{digits}f}".replace(".", ",")
        return str(value)

    header = "| " + " | ".join(df.columns) + " |"
    separator = "| " + " | ".join("---" for _ in df.columns) + " |"
    body = ["| " + " | ".join(fmt(cell) for cell in row) + " |" for row in df.rows()]
    return "\n".join([header, separator, *body])


def _section(title: str, content: str) -> str:
    """Formata uma seção de segundo nível."""
    return f"## {title}\n\n{content.strip()}\n"


def _integrity_section(integrity: dict[str, Any]) -> str:
    """Resume os testes de integridade."""
    coverage = pl.DataFrame(
        {
            "coluna": list(integrity["coverage"]),
            "cobertura": [f"{value:.1%}" for value in integrity["coverage"].values()],
        }
    )
    status = "aprovados" if integrity["passed"] else "REPROVADOS"
    duplicates = sum(integrity["duplicate_keys"].values())
    orphans = ", ".join(f"{name}: {count}" for name, count in integrity["orphan_keys"].items())
    return (
        f"Testes de integridade **{status}** para {integrity['n_municipalities']} municípios.\n\n"
        f"- Chaves duplicadas (todas as tabelas): **{duplicates}**\n"
        f"- Chaves órfãs em relação à malha — {orphans}\n\n"
        f"{dataframe_to_markdown(coverage)}"
    )


def _clustering_section(clustering: dict[str, Any], profile_table: str) -> str:
    """Resume a clusterização e o teste de diferença do desfecho."""
    stability = clustering["stability"]
    lines = [
        f"- Municípios clusterizados: **{clustering['n_clustered']}** "
        f"({clustering['n_dropped']} descartados por valores ausentes)",
        f"- Número de clusters: **{clustering['k']}** "
        f"(silhouette = {clustering['silhouette']:.3f})".replace(".", ","),
        f"- Estabilidade por subamostragem (ARI): **{stability['mean']:.2f}** "
        f"[IC 95%: {stability['ci_low']:.2f}; {stability['ci_high']:.2f}]".replace(".", ","),
        "",
    ]
    for outcome, test in clustering["outcome_tests"].items():
        lines.append(
            f"- `{outcome}` entre clusters — Kruskal-Wallis: H = {test['h']:.1f}, "
            f"p = {test['p_value']:.2g}, ε² = {test['epsilon_squared']:.3f} "
            f"(n = {int(test['n'])})"
        )
    descriptions = "\n".join(
        f"- **Cluster {cluster}:** {text}"
        for cluster, text in sorted(clustering["descriptions"].items(), key=lambda i: int(i[0]))
    )
    return (
        "\n".join(lines)
        + "\n\n**Características marcantes (z-score da mediana):**\n\n"
        + descriptions
        + "\n\n**Perfil (medianas; IDEB com IC 95% bootstrap):**\n\n"
        + profile_table
    )


def _spatial_section(spatial: dict[str, Any], cohesion_table: str) -> str:
    """Resume Moran global, classes LISA e coesão dos clusters."""
    moran = pl.DataFrame(spatial["moran"])
    lisa = pl.DataFrame(
        [
            {"variável": variable, "classe": label, "municípios": count}
            for variable, counts in spatial["lisa_counts"].items()
            for label, count in counts.items()
        ]
    )
    return (
        f"Vizinhança Queen, matriz padronizada por linha; "
        f"{spatial['permutations']} permutações; "
        f"correção FDR: {'sim' if spatial['apply_fdr'] else 'não'}.\n\n"
        "**I de Moran global:**\n\n"
        f"{dataframe_to_markdown(moran, digits=4)}\n\n"
        "**Contagem de municípios por classe LISA:**\n\n"
        f"{dataframe_to_markdown(lisa)}\n\n"
        "**Coesão espacial das tipologias (fração de vizinhos no mesmo cluster):**\n\n"
        f"{cohesion_table}"
    )


def build_report(results: dict[str, Any], profile: pl.DataFrame, cohesion: pl.DataFrame) -> str:
    """Monta o relatório em Markdown com achados e limitações.

    Seções cujos resultados ainda não foram gerados (etapa não executada)
    aparecem com um aviso, em vez de falhar.

    Parameters
    ----------
    results : dict[str, Any]
        Conteúdo de ``results.json`` (seções ``integrity``, ``clustering``, ``spatial``).
    profile : pl.DataFrame
        Perfil dos clusters (``cluster_profile.parquet``).
    cohesion : pl.DataFrame
        Coesão espacial por cluster.

    Returns
    -------
    str
        Documento Markdown completo.
    """
    pending = "_Etapa ainda não executada. Rode `make reproduce`._"
    parts = [
        "# Radar da Educação Municipal — relatório de resultados\n",
        _section(
            "1. Integridade da base",
            _integrity_section(results["integrity"]) if "integrity" in results else pending,
        ),
        _section(
            "2. Tipologias de municípios",
            _clustering_section(results["clustering"], dataframe_to_markdown(profile, digits=2))
            if "clustering" in results
            else pending,
        ),
        _section(
            "3. Análise espacial",
            _spatial_section(results["spatial"], dataframe_to_markdown(cohesion))
            if "spatial" in results
            else pending,
        ),
        _section("4. Limitações", LIMITATIONS),
    ]
    if "gold_sha256" in results.get("integrity", {}):
        parts.append(
            _section(
                "5. Reprodutibilidade",
                f"SHA-256 da base gold: `{results['integrity']['gold_sha256']}`",
            )
        )
    return "\n".join(parts)
