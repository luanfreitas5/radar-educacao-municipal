# Changelog

Todas as mudanças relevantes deste projeto são documentadas aqui.
O formato segue o [Keep a Changelog](https://keepachangelog.com/pt-BR/1.1.0/) e o projeto
adota [Versionamento Semântico](https://semver.org/lang/pt-BR/).

## [Não lançado]

### Adicionado
- Ingestão idempotente com cache e manifesto SHA-256 (Censo Escolar, IDEB, SIDRA, geobr).
- Agregação por município, junção pelo código de 7 dígitos e contratos `pandera`.
- Testes de integridade: cobertura, duplicatas, chaves órfãs e nulos.
- Clusterização (KMeans) com padronização, estabilidade por subamostragem, UMAP e perfil.
- Análise espacial: vizinhança Queen, I de Moran global e local (LISA) com correção FDR.
- Relatório automático em Markdown, datasheet e documentação MkDocs.
