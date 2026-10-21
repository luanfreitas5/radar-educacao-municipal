# Arquitetura

```
fontes públicas ──► bronze ──► silver ──► gold ──► clusters ──► espacial ──► relatório
 (INEP, IBGE)      (imutável)  (tipado,    (base     (KMeans +   (Queen,       (Markdown)
                    + manifest  validado)   única)    UMAP)       Moran, LISA)
```

| Camada | Conteúdo | Garantia |
|---|---|---|
| `data/bronze` | arquivos como recebidos + `manifest.json` (URL, SHA-256, data) | nunca modificada; ingestão idempotente |
| `data/silver` | uma tabela por fonte, **uma linha por município** | contrato `pandera` (tipos, faixas, chave única de 7 dígitos) |
| `data/gold` | base integrada, clusters e classes LISA | junção à esquerda sobre a malha + testes de integridade |

## Decisões

- **Malha como universo.** A junção parte da malha do IBGE (`geobr`) com `left join`;
  município ausente em uma fonte vira nulo *quantificado* (cobertura), não some.
- **IDEB fora da clusterização.** As tipologias usam infraestrutura escolar e contexto
  socioeconômico; o IDEB é o desfecho usado para validá-las (evita circularidade).
- **Incerteza sempre reportada.** Estabilidade dos clusters (ARI por subamostragem),
  IC 95% bootstrap da mediana do IDEB e correção FDR nos p-valores do LISA.
- **Ilhas removidas.** Municípios sem vizinhos Queen saem da análise espacial.
- **Sem segredos.** Todas as fontes são públicas; não há `.env`.

## Pacotes de `src/`

| Pacote | Responsabilidade |
|---|---|
| `config` | caminhos, YAML validado com Pydantic, logging |
| `ingestion` | download com cache, manifesto e hash |
| `preprocessing` | bronze → silver e junção |
| `schemas`, `validation` | contratos de dados e testes de integridade |
| `modeling` | clusterização, UMAP e perfil |
| `spatial` | vizinhança, Moran/LISA e coesão |
| `visualization`, `reporting` | figuras e relatório |
| `pipelines` | uma função por etapa; `main.py` orquestra |
