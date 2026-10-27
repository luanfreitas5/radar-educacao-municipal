# Model Card — Tipologia municipal (KMeans, k = 4) v0.1.0

**Status:** APPROVED FOR análise exploratória e descritiva de municípios (portfólio/pesquisa)
**Bloqueios pendentes:**
- IC 95% por região para o IDEB dos clusters (seção 8) — bloqueia qualquer uso que compare regiões formalmente.
- Validação externa (outro ano de referência do Censo Escolar) — bloqueia uso em planejamento de políticas.
- Monitoramento de drift — bloqueia reuso em ciclos anuais sem reavaliar k e a estabilidade.

## 1. Detalhes do modelo
- **Responsável / contato:** Luan Freitas — luan.mgf@gmail.com
- **Data:** 2026-10-26
- **Algoritmo:** pipeline não supervisionado: `log1p` nas variáveis assimétricas → `StandardScaler` → `KMeans` (scikit-learn, k escolhido por silhouette em 3–10, `n_init` = 20, seed 42). UMAP apenas para visualização. Hiperparâmetros em `configs/model_params.yaml`.
- **Rastreabilidade:** Git SHA `6567f30` (último commit; o working tree tinha alterações não commitadas na data) · MLflow run: não aplicável (o projeto não usa MLflow; os resultados ficam em `reports/results.json`) · hash dos dados (gold) `3eb86d80853a64da7c29146eb6d5f75686e83638b890142b1cf97e56eb5a71d3`
- **Licença:** MIT (código). Dados públicos: ver [datasheet](../datasheets/datasheet_base_municipal.md).

## 2. Uso pretendido
- **Uso primário:** descrever perfis de municípios (infraestrutura escolar, porte e renda) e relacioná-los ao IDEB e à estrutura espacial, para análise exploratória.
- **Usuários pretendidos:** analistas de dados, pesquisadores e revisores de portfólio.
- **Humano no circuito:** sim — os clusters são perfis descritivos para interpretação; não geram decisão automática.

## 3. Usos fora do escopo
- Avaliar, ranquear ou punir escolas, gestores ou estudantes (a unidade é o município; falácia ecológica).
- Alocar recursos ou definir metas de política pública sem análise complementar.
- Inferência causal (ex.: "infraestrutura causa IDEB maior"): o estudo mostra associação.
- Uso em outros anos de referência ou outros países sem reexecutar o pipeline e revalidar k e estabilidade.

## 4. Fatores
- **Grupos relevantes:** região (Norte, Nordeste, Sudeste, Sul, Centro-Oeste), porte populacional, perfil urbano/rural.
- **Ambientes:** Censo Escolar 2023, IDEB 2023, população 2022, PIB 2021, malha municipal 2022.

## 5. Métricas
- **Métrica principal:** silhouette = **0,189** (k = 3: 0,173; k = 5: 0,146) — usada para escolher k; é **baixa**, ou seja, os grupos se sobrepõem. Justificativa: não há rótulo; o custo de um erro é interpretar fronteiras difusas como categorias nítidas, por isso reportamos também estabilidade e efeito sobre o IDEB.
- **Métricas complementares:** estabilidade por subamostragem (30 repetições, 80%): ARI = **0,98** (IC 95%: 0,95–0,99); Kruskal-Wallis do IDEB (variável fora da clusterização) com ε².
- **Limiar de decisão:** não aplicável (modelo não supervisionado); k fixado pelo máximo da silhouette.
- **Calibração:** não aplicável (não há probabilidades).

## 6. Dados de avaliação
Os mesmos 5.570 municípios usados no ajuste (não há conjunto de teste: a avaliação é interna). O IDEB, que **não** entra na clusterização, funciona como desfecho externo: n = 5.430 (anos iniciais) e 5.382 (anos finais). Validação interna apenas; sem validação externa.

## 7. Dados de treino
Base gold `data/gold/municipios.parquet`, uma linha por município. Detalhes em [reports/datasheets/datasheet_base_municipal.md](../datasheets/datasheet_base_municipal.md).

## 8. Análise quantitativa
IDEB por cluster (mediana, IC 95% bootstrap, 2.000 reamostragens):

| Recorte | n | IDEB anos iniciais | IDEB anos finais | Baseline |
|---|---|---|---|---|
| Geral | 5.570 | — | — | — (descritivo; não há baseline preditivo) |
| Cluster 0 (rural, rede municipal) | 1.981 | 5,2 [5,1; 5,2] | 4,3 [4,3; 4,4] | — |
| Cluster 1 (água encanada, menos alunos/docente) | 1.952 | 6,2 [6,2; 6,3] | 5,1 [5,0; 5,1] | — |
| Cluster 2 (urbano, esgotamento, escolas maiores) | 1.526 | 6,1 [6,1; 6,2] | 5,0 [5,0; 5,0] | — |
| Cluster 3 (infraestrutura crítica, Norte) | 111 | 4,6 [4,3; 4,8] | 3,9 [3,8; 4,2] | — |

Diferença entre clusters (Kruskal-Wallis): anos iniciais H = 1324,8, p ≈ 6e-287, ε² = 0,24; anos finais H = 1045,1, p ≈ 3e-226, ε² = 0,19.

Por região, a ordem entre clusters se mantém, mas o nível varia mais por região do que entre os clusters 1 e 2 (ex.: anos iniciais no cluster 2: Sul 6,2 vs. Nordeste 5,4). Medianas por região em `reports/results.json` (`median_by_region`). `TODO(Luan Freitas): IC 95% por região × cluster; o cluster 3 só tem municípios com IDEB na região Norte, então não há comparação regional para ele.`

Estrutura espacial (Queen, 999 permutações): I de Moran do IDEB = 0,625 (anos iniciais) e 0,591 (anos finais), p = 0,001 (mínimo possível com 999 permutações). Coesão territorial dos clusters: 1,7× a 2,0× o esperado ao acaso nos clusters 0–2 e 30,7× no cluster 3.

## 9. Considerações éticas e fairness
- **Atributos sensíveis auditados:** região e porte do município. Não há atributos de pessoas.
- **Disparidades encontradas:** o cluster 3 (2% dos municípios) concentra-se na região Norte e tem o menor IDEB; o nível do IDEB varia mais entre regiões do que entre os clusters 1 e 2.
- **Mitigação aplicada:** nenhuma; o modelo é descritivo e não decide nada sobre municípios. Rótulos de cluster não devem ser usados como "mérito".
- **Base legal LGPD:** não há dado pessoal; dados públicos agregados por município (art. 7º, IV e art. 12 da LGPD).

## 10. Limitações, riscos e monitoramento
- **Limitações conhecidas:** silhouette baixa (grupos sobrepostos); KMeans supõe grupos esféricos e k por silhouette favorece poucos grupos; IDEB ausente em 2,5% (anos iniciais) e 3,4% (anos finais) dos municípios, possivelmente não aleatório; anos de referência distintos entre fontes (PIB 2021 / população 2022); MAUP e ilhas removidas na vizinhança Queen; UMAP é só ilustrativo; associação, não causalidade.
- **Mudanças de distribuição previstas:** nova edição do Censo Escolar/IDEB altera as proporções e pode reordenar clusters; efeitos da pandemia nos ciclos de IDEB anteriores a 2023 não foram tratados.
- **Monitoramento:** não há serviço em produção. A cada atualização dos anos em `configs/config.yaml`, reexecutar `make reproduce` e comparar silhouette, ARI e tamanhos de cluster com os valores acima. `TODO(Luan Freitas): definir limiar de alerta (ex.: ARI < 0,90 entre execuções).`
- **Critério de retreino / descontinuação:** reexecutar a cada novo ciclo de dados; descontinuar a versão se o teste de integridade falhar ou se a estabilidade (ARI) cair abaixo do limiar a definir.
