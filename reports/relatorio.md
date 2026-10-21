# Radar da Educação Municipal — relatório de resultados

## 1. Integridade da base

Testes de integridade **aprovados** para 5570 municípios.

- Chaves duplicadas (todas as tabelas): **0**
- Chaves órfãs em relação à malha — censo_escolar: 0, ideb: 0, sidra: 0

| coluna | cobertura |
| --- | --- |
| n_schools | 100.0% |
| population | 100.0% |
| gdp_per_capita | 100.0% |
| ideb_early_years | 97.5% |
| ideb_late_years | 96.6% |

## 2. Tipologias de municípios

- Municípios clusterizados: **5570** (0 descartados por valores ausentes)
- Número de clusters: **4** (silhouette = 0,189)
- Estabilidade por subamostragem (ARI): **0,98** [IC 95%: 0,95; 0,99]

- `ideb_early_years` entre clusters — Kruskal-Wallis: H = 1324.8, p = 6.3e-287, ε² = 0.244 (n = 5430)
- `ideb_late_years` entre clusters — Kruskal-Wallis: H = 1045.1, p = 2.9e-226, ε² = 0.194 (n = 5382)

**Características marcantes (z-score da mediana):**

- **Cluster 0:** rural_share (+0,9), municipal_network_share (+0,9), computer_lab_share (-0,9)
- **Cluster 1:** water_network_share (+0,9), students_per_teacher (-0,7), library_share (+0,6)
- **Cluster 2:** sewage_network_share (+1,1), rural_share (-0,9), enrollments_per_school (+0,8)
- **Cluster 3:** electricity_network_share (-5,9), internet_share (-3,9), water_network_share (-2,5)

**Perfil (medianas; IDEB com IC 95% bootstrap):**

| cluster | n | share | enrollments_per_school_median | students_per_teacher_median | rural_share_median | municipal_network_share_median | internet_share_median | library_share_median | computer_lab_share_median | sports_court_share_median | water_network_share_median | sewage_network_share_median | electricity_network_share_median | population_median | population_density_median | gdp_per_capita_median | ideb_early_years_median | ideb_early_years_ci_low | ideb_early_years_ci_high | ideb_early_years_n | ideb_late_years_median | ideb_late_years_ci_low | ideb_late_years_ci_high | ideb_late_years_n |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 0 | 1981 | 0,36 | 165,75 | 15,48 | 0,57 | 0,83 | 0,93 | 0,21 | 0,13 | 0,19 | 0,60 | 0,17 | 1,00 | 11890,00 | 22,17 | 12555,49 | 5,20 | 5,10 | 5,20 | 1947 | 4,30 | 4,30 | 4,40 | 1929 |
| 1 | 1952 | 0,35 | 170,44 | 11,95 | 0,20 | 0,67 | 1,00 | 0,57 | 0,43 | 0,50 | 1,00 | 0,44 | 1,00 | 4969,00 | 16,94 | 34554,05 | 6,20 | 6,20 | 6,30 | 1855 | 5,10 | 5,00 | 5,10 | 1841 |
| 2 | 1526 | 0,27 | 278,50 | 15,35 | 0,08 | 0,60 | 1,00 | 0,42 | 0,39 | 0,48 | 0,96 | 0,86 | 1,00 | 32598,00 | 72,76 | 33274,72 | 6,10 | 6,10 | 6,20 | 1519 | 5,00 | 5,00 | 5,00 | 1507 |
| 3 | 111 | 0,02 | 126,85 | 15,96 | 0,81 | 0,88 | 0,37 | 0,10 | 0,07 | 0,07 | 0,17 | 0,02 | 0,52 | 20718,00 | 1,69 | 14448,94 | 4,60 | 4,30 | 4,80 | 109 | 3,90 | 3,80 | 4,20 | 105 |

## 3. Análise espacial

Vizinhança Queen, matriz padronizada por linha; 999 permutações; correção FDR: sim.

**I de Moran global:**

| variable | moran_i | expected_i | p_value | z_score | permutations | n |
| --- | --- | --- | --- | --- | --- | --- |
| ideb_early_years | 0,6250 | -0,0002 | 0,0010 | 76,6718 | 999 | 5428 |
| ideb_late_years | 0,5905 | -0,0002 | 0,0010 | 68,7769 | 999 | 5380 |

**Contagem de municípios por classe LISA:**

| variável | classe | municípios |
| --- | --- | --- |
| ideb_early_years | Baixo-Alto | 43 |
| ideb_early_years | Alto-Alto | 575 |
| ideb_early_years | Não significativo | 3953 |
| ideb_early_years | Alto-Baixo | 39 |
| ideb_early_years | Baixo-Baixo | 818 |
| ideb_late_years | Não significativo | 4169 |
| ideb_late_years | Alto-Alto | 538 |
| ideb_late_years | Alto-Baixo | 32 |
| ideb_late_years | Baixo-Alto | 13 |
| ideb_late_years | Baixo-Baixo | 628 |

**Coesão espacial das tipologias (fração de vizinhos no mesmo cluster):**

| cluster | observed_share | expected_share | ratio |
| --- | --- | --- | --- |
| 0 | 0,723 | 0,356 | 2,032 |
| 1 | 0,595 | 0,351 | 1,696 |
| 2 | 0,531 | 0,274 | 1,939 |
| 3 | 0,613 | 0,020 | 30,734 |

## 4. Limitações

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

## 5. Reprodutibilidade

SHA-256 da base gold: `3eb86d80853a64da7c29146eb6d5f75686e83638b890142b1cf97e56eb5a71d3`
