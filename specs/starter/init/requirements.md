# 📋 Requisitos - IUNA API

**Projeto**: IUNA API  
**Versão**: 2.0.0  
**Última Atualização**: 2026-06-20

---

## 1. Visão Geral

A IUNA API é uma API REST construída com FastAPI para processamento inteligente, enriquecimento e busca de documentos armazenados no Elasticsearch. O sistema permite:

- **Gestão de documentos** — indexação, consulta e deleção de dois tipos de objetos: documentos com metadados estruturados e artefatos genéricos (PDFs diversos com metadados mínimos).
- **Enriquecimento com IA** — operações de inferência sobre o conteúdo textual: geração de resumo, extração e classificação de entidades, extração de keywords, vetorização (embeddings) e segmentação em chunks. Cada inferência grava resultado + timestamp no documento, enriquecendo-o progressivamente.
- **Busca avançada** — full-text com relevância (match_phrase + fuzziness), filtros estruturados, facetas, busca por entidades, busca por keywords, busca por similaridade vetorial (kNN), busca em chunks, highlights e autocomplete.
- **Chat conversacional (RAG)** — classificação de intenção via Rasa, busca híbrida (BM25 + kNN com RRF) nos chunks para montar contexto, geração de resposta pelo LLM com histórico de sessão.
- **Processamento em lote** — todas as operações (indexação, enriquecimento, busca) são executáveis via CLI/Batch sobre diretórios completos, usando o filename como identificador.

### 1.1 Tipos de Objeto

**`documentos` (índice `documentos_ifal`)** — Documentos com metadados ricos:
- Estrutura: `ato.titulo`, `ato.ementa`, `ato.fonte.*`, `ato.tipo_doc`, `ato.ano`, `ato.data_publicacao`, etc.
- Exemplos: editais, portarias, resoluções, regulamentos, atas, memorandos, ofícios, pareceres, contratos, convênios, apostilas, livros, planos de ensino, projetos de pesquisa/extensão, TCC.
- Busca rica com filtros por tipo, órgão, esfera, ano, etc.
- **Também enriquecido com IA**: resumo (`ato.resumo`), entidades (`ato.entidades`), embedding (`ato.embedding_vector`), chunks. Os dados de enriquecimento potencializam a busca por semelhantes, busca por entidades e o RAG.

**`artefatos` (índice `artefatos`)** — Documentos genéricos com metadados mínimos:
- Para PDFs diversos submetidos por aplicações (livros, materiais avulsos, documentos externos).
- Metadados: `titulo`, `filename`, `tipo`, `tags`, `uploaded_by`, `created_at`, `updated_at`.
- Conteúdo textual extraído automaticamente em `attachment.content`.
- **Todo o restante é inferido** pelo enriquecimento com IA: resumo, entidades, embedding, chunks.
- **Alvo principal de chunking** para RAG.

> **Ambos os tipos são enriquecidos.** O enriquecimento gera dados que são usados diretamente na busca: entidades permitem busca estruturada por nomes/organizações; embeddings permitem busca por similaridade (kNN); resumos melhoram relevância textual; chunks habilitam o RAG no chat.

### 1.2 Princípios

- Toda inferência **enriquece** o registro no ES (resultado + timestamp `*_at`).
- Consumidores da API: **aplicações frontend e outros sistemas** (não usuários humanos diretos).
- **Duplo ponto de entrada**: API HTTP e CLI/Batch — mesmos Services, zero duplicação.
- Serviços **reutilizados** para ambos os tipos — parâmetro `source_type` adapta índice e campos.

### 1.3 Organização em Módulos

| Módulo | Escopo |
|--------|--------|
| **Gestão (CRUD)** | Indexação (upload PDF), consulta, listagem, atualização parcial, deleção |
| **Busca** | Full-text, filtros, facetas, semelhantes, por entidade, por keyword, chunks, autocomplete |
| **Enriquecimento** | Resumo, entidades, keywords, vetorização, chunking — com suporte a lote e enrich via API |
| **Chat** | RAG com Rasa + LLM + histórico de sessão + contexto dinâmico (add docs) |
| **Scoring** | Relevância por uso (click, add_to_chat, download, share) |

---

## 2. Requisitos Funcionais

### RF-01u — Autenticação
- **RF-01u.1**: Todas as rotas `/api/v1/` (exceto `/health-check`, `/info`) exigem um token válido no header `Authorization: Bearer <token>`.
- **RF-01u.2**: O token é uma API key configurada via variável de ambiente (`API_SECRET_TOKEN`). A validação compara o token recebido com o configurado.
- **RF-01u.3**: Token inválido ou ausente → HTTP 401.
- **RF-01u.4**: Não há gestão de múltiplos usuários/clientes. O token é único e compartilhado com as aplicações que consomem a API.

---

### RF-02 — Módulo de Gestão (CRUD)

#### RF-02a — Indexação de Documentos
- **RF-02a.1**: `POST /api/v1/documentos/upload` aceita PDF (multipart/form-data) + metadados opcionais. O texto é extraído do PDF no backend.
- **RF-02a.2**: Metadados opcionais (podem ser inferidos pelo backend): `titulo`, `ementa`, `tipo_doc`, `numero`, `ano`, `data_publicacao`, `publico`, `tags`, `orgao`, `esfera`. O mínimo é o PDF.
- **RF-02a.3**: `ato.ato_id` gerado automaticamente se não fornecido.
- **RF-02a.4**: Se já existir (mesmo `ato.ato_id` ou `filename`) → HTTP 409 (conflict), exceto com flag `--force`.
- **RF-02a.5_cli**: Via CLI: `--directory` lê cada PDF e indexa usando filename como `ato.ato_id`.

#### RF-02b — Indexação de Artefatos
- **RF-02b.1**: `POST /api/v1/artefatos/upload` aceita PDF como arquivo anexo na requisição (multipart/form-data).
- **RF-02b.2**: O sistema extrai o conteúdo textual do PDF (via biblioteca Python, ex: PyPDF/pdfplumber) e grava em `attachment.content`. O PDF é enviado em base64 ou como arquivo e o texto é extraído no código da API antes da indexação.
- **RF-02b.3**: Metadados obrigatórios: `titulo`, `uploaded_by`. Opcionais: `tipo`, `tags`.
- **RF-02b.4**: Campos automáticos: `artefato_id` (gerado), `filename` (nome original do arquivo), `created_at`, `updated_at`.
- **RF-02b.5**: Via CLI: `--directory --source-type artefatos` lê cada PDF do diretório, extrai texto e indexa usando filename.
- **RF-02b.6**: Se o artefato for re-enviado (mesmo `filename`), os chunks antigos no `artefatos_chunks` devem ser deletados antes de reindexar (re-chunking automático).

#### RF-02a — Consulta de Documentos
- **RF-02a.5**: `GET /api/v1/documentos/{document_id}` → por `ato.ato_id`.
- **RF-02a.6**: `GET /api/v1/documentos/by-filename/{filename}` → por `filename.keyword`.

#### RF-02b — Consulta de Artefatos
- **RF-02b.5**: `GET /api/v1/artefatos/{artefato_id}` → por `artefato_id`.
- **RF-02b.6**: `GET /api/v1/artefatos/by-filename/{filename}` → por `filename.keyword`.

#### RF-02a — Deleção de Documentos
- **RF-02a.7**: `DELETE /api/v1/documentos/{document_id}` remove documento + chunks em `documentos_ifal_chunks`.

#### RF-02b — Deleção de Artefatos
- **RF-02b.7**: `DELETE /api/v1/artefatos/{artefato_id}` remove artefato + chunks em `artefatos_chunks`.

#### Regras universais de gestão
- **RF-02u.1**: Deleção disponível para qualquer cliente autenticado.
- **RF-02u.2**: Documento não encontrado → HTTP 404.
- **RF-02u.3**: Consulta retorna `_source` completo.
- **RF-02u.4**: Via CLI: `iuna delete --id <id> --source-type <tipo>`.
- **RF-02u.5**: Todas as operações de gestão executáveis em lote via `--directory` (itera por arquivo, filename como identificador).

---

### RF-03 — Módulo de Busca

> **Os recursos de busca dependem fortemente dos campos de enriquecimento.** Entidades extraídas alimentam a busca por entidade e semelhantes; embeddings viabilizam similaridade vetorial (kNN) e o RAG; resumos ampliam a superfície textual de match. O módulo de busca é projetado para explorar ao máximo os dados inferidos pelo módulo de enriquecimento (RF-04).

#### RF-03a — Busca Full-Text (`documentos`)
- **RF-03a.1**: `GET /api/v1/documentos/search` com `q` → busca `bool`, `minimum_should_match: 1`.
- **RF-03a.2**: `match_phrase` com boost/slop: `ato.ementa` (1.5/5), `ato.titulo` (1.5/2), `ato.tags` (1.5/2), `attachment.content` (1.25/5), `ato.resumo` (1.0/5).
- **RF-03a.3**: `match` com fuzziness: `ato.ementa` (1.5/1/3), `ato.tags` (1.5/1/3), `attachment.content` (1.0/1/3), `ato.resumo` (0.75/1/3), `ato.entidades.texto` (1.0/1/3).
- **RF-03a.4**: Modo busca exata (aspas) → `match_phrase` boost 2.0, slop 0.
- **RF-03a.5**: Highlights com `<em>` em `ato.ementa`, `ato.titulo`, `attachment.content`, `ato.resumo`.

#### RF-03b — Busca Full-Text (`artefatos`)
- **RF-03b.1**: `GET /api/v1/artefatos/search` com `q` → busca `bool` em `titulo`, `attachment.content`, `resumo` e `entidades.texto`.
- **RF-03b.2**: Mesma lógica de relevância (match_phrase + fuzziness), highlights.
- **RF-03b.3**: Filtros: `tipo`, `uploaded_by`, `data_inicio`/`data_fim` (sobre `created_at`).

#### RF-03a — Busca Filtrada (`documentos`)
- **RF-03a.6**: Filtros como cláusulas `filter` (term/range): `tipo_doc`, `orgao`, `esfera`, `ano`, `fonte`, `periodo`, `data_inicio`/`data_fim`, `publico`, `categoria` (institucional/didatico/projeto).
- **RF-03a.7**: Filtro `publico` filtra conforme valor enviado (sem forçamento automático).
- **RF-03a.8**: Múltiplos filtros = AND.

#### RF-03a — Busca Facetada (`documentos`)
- **RF-03a.9**: `GET /api/v1/documentos/search/facets` → resultados + agregações.
- **RF-03a.10**: Facetas: `ato.tipo_doc`, `ato.fonte.orgao.keyword`, `ato.fonte.esfera`, `ato.ano`, `ato.tags.keyword`, `ato.fonte.sigla`.
- **RF-03a.11**: Agregações em requisição separada (contagens globais).

#### RF-03u — Busca por Semelhantes
- **RF-03u.1**: `GET /api/v1/{tipo}/search/similar/{document_id}`.
- **RF-03u.2**: Similaridade por kNN (`embedding_vector`). Fallback: `more_like_this`.
- **RF-03u.3**: Entidades em comum elevam relevância.
- **RF-03u.4**: `limit` (default 10).

#### RF-03u — Busca por Entidades
- **RF-03u.5**: `GET /api/v1/{tipo}/search/by-entity` com `entity_text`, `entity_category`.
- **RF-03u.6**: Categorias: `DOCUMENTO`, `ORGANIZACAO`, `REGULAMENTO`, `DATA`, `PESSOA`, `LOCAL`, `CURSO`, `PROGRAMA`, `LEGISLACAO`.
- **RF-03u.7**: Opera sobre campo `entidades` (nested).
- **RF-03u.8**: Resultados indicam quais entidades fizeram match.

#### RF-03u — Busca em Chunks
- **RF-03u.9**: `GET /api/v1/{tipo}/search/chunks` com `q`.
- **RF-03u.10**: Retorna: conteúdo, `chunk_index`, `parent_document_id`, `parent_filename`, `total_chunks`.
- **RF-03u.11**: `document_id` ou `filename` restringe ao documento pai.
- **RF-03u.12**: Agrupa por documento pai. Indica blocos com match vs. total.

#### RF-03u — Autocomplete
- **RF-03u.13**: `GET /api/v1/{tipo}/search/suggest` com `q` (min 2 chars).
- **RF-03u.14**: Sugestões de títulos e tags.
- **RF-03u.15**: `limit` (default 5).

#### Regras universais de busca
- **RF-03u.16**: `q` vazio/ausente → HTTP 400.
- **RF-03u.17**: Paginação: `page` (default 1), `page_size` (default 20).
- **RF-03u.18**: Resposta: `total`, `page`, `page_size`, `results`, `took_ms`.
- **RF-03u.19**: Ordenação por `_score` por padrão.

---

### RF-04 — Módulo de Enriquecimento

Todas as operações deste módulo funcionam para ambos os tipos de objeto via `source_type`. Cada uma aceita texto bruto OU `document_id`/`filename` + `source_type`. Quando via ID/filename: busca texto de `attachment.content`, processa, grava resultado + `*_at` no documento. Enriquecimento é idempotente (re-executar sobrescreve). Todas executáveis em lote via CLI com flags combináveis.

#### RF-04u — Resumo
- **RF-04u.1**: `POST /api/v1/{tipo}/summary/generate`.
- **RF-04u.2**: Grava em `{root}.resumo` + `{root}.resumo_at`.
- **RF-04u.3**: Retorna resumo na resposta.

#### RF-04u — Vetorização
- **RF-04u.4**: `POST /api/v1/{tipo}/vectorization/generate`.
- **RF-04u.5**: A vetorização gera embedding **a partir do resumo** do documento (não do texto completo). Para documentos pequenos (~1 página), o resumo pode ser o próprio conteúdo quase integral.
- **RF-04u.6**: Grava em `{root}.embedding_vector` + `{root}.embedding_vector_at`.
- **RF-04u.7**: Retorna vetor na resposta.
- **RF-04u.8**: Depende que o resumo já exista. Se o resumo não existir ao vetorizar via ID/filename, o SummaryService deve ser invocado primeiro automaticamente.

#### RF-04u — Extração de Entidades
- **RF-04u.9**: `POST /api/v1/{tipo}/entities/extract`.
- **RF-04u.10**: Cada entidade: `{texto, categoria, confianca}`.
- **RF-04u.11**: Categorias: `DOCUMENTO`, `ORGANIZACAO`, `REGULAMENTO`, `DATA`, `PESSOA`, `LOCAL`, `CURSO`, `PROGRAMA`, `LEGISLACAO`.
- **RF-04u.12_e**: Grava em `{root}.entidades` (nested) + `{root}.entidades_at`.
- **RF-04u.13_e**: Alimenta busca por entidade (RF-03u.5) e semelhantes (RF-03u.1).

#### RF-04u — Extração de Keywords
- **RF-04u.14_k**: `POST /api/v1/{tipo}/keywords/extract`.
- **RF-04u.15_k**: Keywords são termos-chave/conceitos relevantes extraídos pelo LLM (ex: "licitação", "processo seletivo", "ética pública"). Diferem de entidades: não são nomes próprios, não têm categoria.
- **RF-04u.16_k**: Grava como array de strings em `{root}.keywords` + `{root}.keywords_at`.
- **RF-04u.17_k**: Keywords usadas na busca full-text (campo adicional no `should` com boost) e como faceta/filtro.
- **RF-04u.18_k**: Para `documentos_ifal`, keywords complementam o campo `ato.tags` existente.
- **RF-04u.19_k**: Busca por keyword: `GET /api/v1/{tipo}/search/by-keyword?keyword=<termo>`.

#### RF-04u — Segmentação (Chunking)
- **RF-04u.12**: `POST /api/v1/{tipo}/chunking/generate`.
- **RF-04u.13**: Tamanho padrão: **3000 caracteres** (~1 página). Overlap: **500 caracteres**.
- **RF-04u.14**: `chunk_size` mínimo 3000. Menor → HTTP 422.
- **RF-04u.15**: Indexa chunks no índice correspondente (`documentos_ifal_chunks` ou `artefatos_chunks`) com: `parent_document_id`, `parent_filename`, `chunk_index`, `content`, `total_chunks`, `embedding_vector`.
- **RF-04u.16**: Invoca VectorService para embedding de cada chunk.
- **RF-04u.17**: Atualiza `chunking_at` + `total_chunks` no documento pai.
- **RF-04u.18**: `artefatos` é o **alvo principal** de chunking.
- **RF-04u.19**: Busca em chunkeados opera sobre **TODOS** os blocos.
- **RF-04u.20_**: **Regra de aplicação automática**: documentos com `attachment.content` ≥ 10.000 caracteres (~3 páginas) devem ser chunkeados. Documentos menores não são chunkeados — o texto completo serve como contexto direto no RAG.
- **RF-04u.21_**: No `--enrich`, o sistema avalia automaticamente o tamanho do conteúdo e só aplica chunking se ≥ 10.000 caracteres. Não requer flag manual do operador.
- **RF-04u.22_**: Documentos sem chunks (< 10.000 chars): o chat (RF-05u) deve usar `attachment.content` completo como contexto, sem busca em chunks.

#### RF-04u — Processamento em Lote (CLI)

> **Separação fundamental**: indexação = só ES (rápido, sem LLM). Enriquecimento = envolve LLM (lento, tokens, rate limits). Comandos separados, combináveis.

**`iuna ingest`** — Indexação em lote (só Elasticsearch, sem LLM):
- **RF-04u.23**: `iuna ingest --source-type <tipo> --directory <path>` → lê cada PDF, extrai texto (pdfplumber), indexa no ES. Não chama LLM.
- **RF-04u.24**: Flag `--enrich` (opt-in) para após indexar cada doc, chamar automaticamente o enriquecimento completo (entidades → keywords → resumo → vetorização → chunking).
- **RF-04u.25**: Sem `--enrich`, o default é SÓ INDEXAR — rápido, sem dependência de LLM.
- **RF-04u.26**: `--force` sobrescreve docs existentes (mesmo filename). Sem `--force` → pula se já existe.
- **RF-04u.27**: `--concurrency N` (default 3).
- **RF-04u.28**: Progresso no terminal (arquivo atual / total).

**`iuna enrich`** — Enriquecimento em lote (envolve LLM):
- **RF-04u.29**: `iuna enrich --source-type <tipo> --directory <path>` ou `--ids <id1,id2>` → opera sobre docs já indexados.
- **RF-04u.30**: Flags seletivas: `--summarize`, `--vectorize`, `--entities`, `--keywords`, `--chunk`. Atalho `--enrich` = todas.
- **RF-04u.31**: Para cada documento executa os serviços na ordem: entidades → keywords → resumo → vetorização (usa resumo) → chunking (se conteúdo ≥ 10.000 chars).
- **RF-04u.32**: `--force` (reprocessar tudo) e `--skip-existing` (pular se `*_at` já existe).
- **RF-04u.33**: `--concurrency N` (default 3) para não sobrecarregar LLM.
- **RF-04u.34**: Progresso no terminal.

**Outros comandos CLI:**
- **RF-04u.35**: `iuna setup-indices [--suffix _test] [--recreate]` — cria índices a partir dos mappings.
- **RF-04u.36**: `iuna delete --id <id> --source-type <tipo>` — remove doc + chunks.
- **RF-04u.37**: `iuna stats` — mostra cobertura de enriquecimento (total docs, quantos sem resumo/entidades/keywords/embedding/chunks).

---

### RF-05u — Módulo de Chat

- **RF-05u.1**: `POST /api/v1/chat/message` aceita `message`, `session_id`.
- **RF-05u.2**: Opcionalmente: `document_ids`/`filenames` + `source_type` para restringir contexto.
- **RF-05u.3**: Classifica intenção via Rasa (`POST /model/parse`).
- **RF-05u.4**: `ask_about_document` → se o documento possui chunks, busca híbrida (BM25 + kNN, RRF) nos índices de chunks para montar contexto. Se o documento não possui chunks (< 10.000 chars), usa `attachment.content` completo como contexto.
- **RF-05u.5**: Sem filtro de `source_type`, busca em ambos os índices de chunks.
- **RF-05u.6**: Contexto (chunks ou texto completo + histórico + mensagem) → LLM para gerar resposta.
- **RF-05u.7**: `chitchat` → direto ao LLM sem busca.
- **RF-05u.8**: Histórico no índice `chat_sessions`: `session_id`, `client_id`, `messages[]`, `created_at`, `last_activity_at`.
- **RF-05u.9**: Últimas N mensagens (config, default 10) como contexto.
- **RF-05u.10**: Sessão expira após inatividade (configurável `CHAT_SESSION_TTL_HOURS`, default 24h).

---

### RF-05u.b — Scoring / Relevância por Uso
- **RF-05u.b.1**: Documentos e artefatos clicados em resultados de busca ou adicionados ao contexto de conversas devem acumular um `popularity_score`.
- **RF-05u.b.2**: O score é incrementado por ações do consumidor: `click` (+1), `add_to_chat` (+3), `download` (+2), `share` (+2).
- **RF-05u.b.3**: Os pesos de cada ação devem ser constantes parametrizáveis no código (extensíveis para novas ações futuras).
- **RF-05u.b.4**: A busca full-text deve aplicar boost baseado no `popularity_score` (via `function_score` com `field_value_factor`, modifier `log1p`), elevando documentos mais usados nos resultados.
- **RF-05u.b.5**: O incremento por `add_to_chat` deve ocorrer automaticamente ao usar `/chat/sessions/{id}/add-documento` ou `/chat/sessions/{id}/add-artefato`.
- **RF-05u.b.6**: O click e demais ações são registrados explicitamente via rota `POST /{tipo}/{id}/score`.

---

### RF-06u — Estatísticas e Health (`/api/v1/stats`, `/api/v1/health`)
- **RF-06u.1**: `GET /api/v1/stats` retorna estatísticas agregadas de ambos os índices.
- **RF-06u.2**: Total docs por tipo/índice, total chunks, docs sem resumo/entidades/embedding/chunking (`*_at` nulo).
- **RF-06u.3**: `took_ms`. Header `Cache-Control: max-age=60`.
- **RF-06u.4**: `GET /api/v1/health` retorna status detalhado de cada dependência: ES (acessível/inacessível), Rasa (acessível/inacessível), LLM provider (configurado/acessível).

---

### RF-07u — Respostas e Tratamento de Erros
- **RF-07u.1**: Sucesso: HTTP 200, JSON `{success, data, meta}`.
- **RF-07u.2**: Parâmetros inválidos → HTTP 422.
- **RF-07u.3**: ES indisponível → HTTP 503.
- **RF-07u.4**: Não encontrado → HTTP 404.
- **RF-07u.5**: Auth inválida → HTTP 401.
- **RF-07u.6**: Conflito → HTTP 409.
- **RF-07u.7**: Header `X-Request-Id` em todas as respostas.

---

## 3. Requisitos Não-Funcionais

### RNF-01 — Flexibilidade de LLM
- **RNF-01.1**: Interface abstrata `BaseLLMProvider`. Provedor ativo via `ACTIVE_LLM_PROVIDER`.
- **RNF-01.2**: Substituição sem alterar Services/Controllers.
- **RNF-01.3**: Provedores: `gemini` (default, cloud), `claude` (cloud), `ollama` (local/offline).

### RNF-02 — Segurança
- **RNF-02.1**: Credenciais no `.env` (nunca no código). `.env` no `.gitignore`.
- **RNF-02.2**: ES com autenticação usuário/senha. Token da API configurado via variável de ambiente.

### RNF-03 — Conteinerização
- **RNF-03.1**: Docker + `docker-compose.yml` (FastAPI + Rasa). ES externo via variáveis.

### RNF-04 — Testabilidade
- **RNF-04.1**: Services testáveis sem FastAPI. Mocks para ES/Rasa/LLM. Testes unit + integration separados.

### RNF-05 — Reuso
- **RNF-05.1**: EnrichmentService compartilhado recebe `(index, doc_id, root)` — mesma lógica para ambos os tipos.
- **RNF-05.2**: Services de busca são concretos (DocumentosSearchService, ArtefatosSearchService) com campos hardcoded. Funções utilitárias em `query_helpers.py` são reutilizadas por ambos.
- **RNF-05.3**: CLI e API compartilham os mesmos Services.

### RNF-06 — Índices Elasticsearch
- **RNF-06.1**: `documentos_ifal` — `elastic/documentos_ifal_mapping.json` + enriquecimento (`ato.resumo`, `ato.embedding_vector`, `ato.entidades`, timestamps `*_at`).
- **RNF-06.2**: `documentos_ifal_chunks` — `elastic/documentos_ifal_chunks_mapping.json`.
- **RNF-06.3**: `artefatos` — `elastic/artefatos_mapping.json` (alvo principal de chunking).
- **RNF-06.4**: `artefatos_chunks` — `elastic/artefatos_chunks_mapping.json`.
- **RNF-06.5**: `chat_sessions` — `elastic/chat_sessions_mapping.json`.

### RNF-07 — Configuração
- **RNF-07.1**: Variáveis: `API_SECRET_TOKEN`, `ACTIVE_LLM_PROVIDER`, `GEMINI_API_KEY`, `CLAUDE_API_KEY`, `OLLAMA_BASE_URL`, `OLLAMA_MODEL`, `ELASTICSEARCH_HOSTS`, `ELASTICSEARCH_USER`, `ELASTICSEARCH_PASSWORD`, `ES_INDEX_SUFFIX`, `RASA_API_URL`, `CHAT_SESSION_TTL_HOURS`, `CHAT_HISTORY_MAX_MESSAGES`, `BATCH_DEFAULT_CONCURRENCY`.
- **RNF-07.2**: `.env.example` com todas as variáveis.
