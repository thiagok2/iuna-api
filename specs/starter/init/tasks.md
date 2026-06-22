# 📋 Tasks — IUNA API

**Versão**: 2.0.0  
**Princípio**: Blocos testáveis. Após cada bloco, algo funcional está rodando e pode ser validado manualmente.

---

## Bloco 1 — Esqueleto (API + CLI + ES conectados)

> **Ao final deste bloco**: API respondendo, CLI executando, ES conectado, índices criados, PDFs de exemplo prontos para submissão.

### T-01: Config + Dependências + .env
- [x] Atualizar `app/config.py` (todas as variáveis: API_SECRET_TOKEN, ES_*, LLM_*, RASA_*, CHAT_*, BATCH_*)
- [x] Properties para nomes de índice (`index_documentos`, `index_artefatos`, etc.)
- [x] Criar `.env.example` completo
- [x] Atualizar `requirements.txt` / `pyproject.toml`: fastapi, uvicorn, pydantic-settings, elasticsearch[async], httpx, pdfplumber, PyPDF2, typer, python-multipart
- [x] **Validar**: app inicia sem erro com `uvicorn app.main:app`

### T-02: ESClient + Health
- [x] Criar `app/clients/es_client.py` (AsyncElasticsearch singleton)
- [x] Métodos: connect, close, ping, search, get, index, update, delete, delete_by_query, bulk_index, create_index, delete_index
- [x] Startup/shutdown no `app/main.py`
- [x] Criar `app/api/routers/health.py`:
  - `GET /health-check` → 200 (sem auth)
  - `GET /info` → nome/versão (sem auth)
  - `GET /api/v1/health` → verifica ES (acessível/inacessível)
- [x] **Validar**: `curl localhost:8000/api/v1/health` → mostra status do ES

### T-03: Auth middleware + X-Request-Id
- [x] Dependency `verify_token` (compara Bearer com API_SECRET_TOKEN)
- [x] Middleware `RequestIdMiddleware`
- [x] Exception handlers globais (NotFound, Conflict, Unauthorized, ServiceUnavailable)
- [x] **Validar**:
  - `curl localhost:8000/api/v1/health-check` → 200 (sem auth)
  - `curl localhost:8000/api/v1/health` → 401 (sem token)
  - `curl -H "Authorization: Bearer 77c7fa54-9b2c-44c1-a7e2-aea881a7797e" localhost:8000/api/v1/health` → 200
  - Response tem header X-Request-Id

### T-04: CLI setup-indices
- [x] Criar `app/cli/main.py` (Typer)
- [x] Comando `iuna setup-indices [--suffix _test] [--recreate]`
- [x] Lê `elastic/*.json`, cria cada índice **apenas se não existir** (verifica antes). Com `--recreate` deleta e recria.
- [x] **Validar**: `python -m app.cli.main setup-indices` → índices criados no ES (verificar via Kibana/curl)

### T-05: PDF Extractor + samples/
- [x] Criar `app/core/pdf_extractor.py` (fallback local: pdfplumber + PyPDF2)
- [x] Estratégia primária: ES Ingest Attachment Pipeline (Apache Tika)
- [x] Criar pasta `samples/` com PDFs de exemplo
- [x] **Validar fallback local**:
  ```
  source .venv/bin/activate
  python samples/test_extractor.py
  ```
- [ ] **Validar pipeline ES** (quando ES estiver online):
  1. Criar pipeline: executar curls de `elastic/setup/20260622_ingest_pipeline.md`
  2. Testar indexação com extração:
  ```
  source .venv/bin/activate
  python samples/test_ingest_pipeline.py samples/edital_selecao.pdf
  ```
  Deve mostrar: texto extraído pelo Tika em `attachment.content`, campo `data` removido.

### T-06: Stubs de TODAS as rotas (retornam 501)
- [x] Criar todos os routers com endpoints stub (HTTP 501 "Not Implemented"):
  - `crud_documentos.py`, `crud_artefatos.py`
  - `search_documentos.py`, `search_artefatos.py`
  - `enrichment_documentos.py`, `enrichment_artefatos.py`
  - `chat.py`, `stats.py`
- [x] Registrar todos em `app/main.py`
- [x] **Validar**: Abrir `/docs` (Swagger) → TODAS as 54 rotas visíveis

---

## Bloco 2 — Ingestão funcional (indexar PDFs via CLI e API)

> **Ao final deste bloco**: PDFs podem ser submetidos e aparecem no ES. Busca por ID/filename funciona.

### T-07: DocumentosCrudService + Router
- [x] Criar `app/services/documentos_crud.py`:
  - `upload(file_bytes, filename, metadados_opcionais)` → extrai texto, indexa
  - `get_by_id`, `get_by_filename`, `delete` (+ chunks)
  - `list_all(page, page_size)`, `update_metadata(id, fields)`
- [x] Substituir stubs em `crud_documentos.py`:
  - `POST /documentos/upload` (multipart)
  - `GET /documentos/{id}`, `GET /documentos/by-filename/{filename}`
  - `GET /documentos` (listagem paginada)
  - `PATCH /documentos/{id}`, `DELETE /documentos/{id}`
- [ ] **Validar**: Upload PDF via Swagger → doc aparece no ES. GET retorna.

### T-08: ArtefatosCrudService + Router
- [x] Criar `app/services/artefatos_crud.py`:
  - `upload(file_bytes, filename, titulo, uploaded_by, tipo, tags)` → extrai texto, indexa
  - `get_by_id`, `get_by_filename`, `delete`, `list_all`, `update_metadata`
  - Re-upload: deleta chunks antigos antes de reindexar
- [x] Substituir stubs em `crud_artefatos.py`
- [ ] **Validar**: Upload PDF artefato via Swagger → aparece no ES

### T-09: CLI ingest
- [x] Comando `iuna ingest --source-type <tipo> --directory <path> [--force] [--concurrency N]`
- [x] Por default: só indexa (ES only, sem LLM)
- [x] Flag `--enrich` (por agora stub: print "enrich not implemented yet")
- [x] `--force` para sobrescrever existentes. Sem `--force` → pula se filename já existe.
- [x] Progresso no terminal.
- [ ] **Validar**: `iuna ingest --source-type artefatos --directory ./samples/` → PDFs indexados. Conferir no ES.

---

## Bloco 3 — LLM Providers + Enriquecimento funcional

> **Ao final deste bloco**: Documentos podem ser enriquecidos (resumo, entidades, keywords, embedding, chunks). Validável via API e CLI.

### T-10: LLM Interface + Factory + primeiro provider
- [ ] Criar `app/providers/base.py` (BaseLLMProvider ABC async):
  - generate_summary, generate_embedding, extract_entities, extract_keywords, generate_response, health_check
- [ ] Criar `app/providers/factory.py`
- [ ] Implementar primeiro provider funcional (Gemini OU Ollama — o que estiver disponível para testar)
- [ ] **Validar**: script que chama `generate_summary("texto de teste")` → retorna string

### T-11: EnrichmentService
- [ ] Criar `app/services/enrichment.py`:
  - `enrich_summary(index, doc_id, root)`
  - `enrich_vector(index, doc_id, root)` — usa resumo como input
  - `enrich_entities(index, doc_id, root)`
  - `enrich_keywords(index, doc_id, root)`
  - `enrich_chunks(index, chunks_index, doc_id, root)` — threshold 10k chars
  - `enrich_all(index, chunks_index, doc_id, root)` — ordem: entidades → keywords → resumo → vetorização → chunking
- [ ] **Validar**: chamar `enrich_all` em um doc já indexado → campos preenchidos no ES

### T-12: Routers de enriquecimento
- [ ] Substituir stubs em `enrichment_documentos.py` e `enrichment_artefatos.py`:
  - POST `/{tipo}/summary/generate`
  - POST `/{tipo}/vectorization/generate`
  - POST `/{tipo}/entities/extract`
  - POST `/{tipo}/keywords/extract`
  - POST `/{tipo}/chunking/generate`
  - POST `/{tipo}/{id}/enrich`
  - GET `/{tipo}/{id}/enrichment-status`
- [ ] **Validar**: POST /artefatos/summary/generate {document_id} → resumo gerado e gravado no ES

### T-13: CLI enrich
- [ ] Comando `iuna enrich --source-type <tipo> --directory/--ids [flags]`
- [ ] Flags: `--summarize`, `--vectorize`, `--entities`, `--keywords`, `--chunk`, `--enrich`
- [ ] `--force`, `--skip-existing`, `--concurrency N`
- [ ] Atualizar `iuna ingest --enrich` para chamar enrich_all após indexar
- [ ] **Validar**: `iuna enrich --source-type artefatos --ids <id> --enrich` → doc totalmente enriquecido

---

## Bloco 4 — Busca funcional

> **Ao final deste bloco**: Busca full-text, filtros, facetas, semelhantes, por entidade, por keyword, chunks e autocomplete funcionando.

### T-14: query_helpers.py
- [ ] Criar `app/core/query_helpers.py` — funções puras:
  - build_match_phrase, build_match_fuzzy, build_nested_entity_query
  - build_highlight, build_term_filter, build_range_filter
- [ ] **Validar**: import e chamar funções → dicts corretos

### T-15: DocumentosSearchService + Router
- [ ] Criar `app/services/documentos_search.py`:
  - search_fulltext (phrase + fuzzy + entidades + keywords + resumo, highlights)
  - search_facets (agregações em requisição separada)
  - search_similar (kNN / more_like_this)
  - search_by_entity (nested query)
  - search_by_keyword
  - suggest (autocomplete)
- [ ] Substituir stubs em `search_documentos.py`
- [ ] **Validar**: buscar termo de um doc indexado via Swagger → retorna com highlights

### T-16: ArtefatosSearchService + Router
- [ ] Criar `app/services/artefatos_search.py`:
  - search_fulltext, search_similar, search_by_entity, search_by_keyword, suggest
- [ ] Substituir stubs em `search_artefatos.py`
- [ ] **Validar**: buscar artefato enriquecido → retorna

### T-17: ChunksSearchService + Router
- [ ] Busca em chunks de ambos os índices
- [ ] Endpoints: `GET /{tipo}/search/chunks`
- [ ] **Validar**: buscar termo presente num chunk → retorna chunk com parent_id

### T-18: Scoring (popularity)
- [ ] Criar `app/core/scoring.py` (constantes SCORE_WEIGHTS)
- [ ] Endpoints: `POST /{tipo}/{id}/score`
- [ ] function_score na busca (boost por popularity_score)
- [ ] **Validar**: score um doc → buscar novamente → ele sobe no ranking

### T-19: Listagem de entidades e keywords
- [ ] `GET /documentos/entities` e `GET /artefatos/entities` — lista com contagem
- [ ] `GET /documentos/keywords` e `GET /artefatos/keywords` — lista com contagem (se aplicável)
- [ ] **Validar**: após enriquecer docs, listar entidades → retorna agregação

---

## Bloco 5 — Chat funcional

> **Ao final deste bloco**: Chat RAG funcionando com busca híbrida, sessões e contexto dinâmico.

### T-20: RasaClient + fallback
- [ ] Criar `app/clients/rasa_client.py`:
  - classify_intent(message) → intent name
  - health_check()
  - Fallback: se Rasa indisponível → retorna "ask_about_document"
- [ ] Atualizar `GET /api/v1/health` para incluir status do Rasa
- [ ] **Validar**: health mostra Rasa status. Fallback funciona sem Rasa rodando.

### T-21: ChatService + Router
- [ ] Criar `app/services/chat.py`:
  - handle_message: Rasa → decisão (chunks vs texto completo) → busca híbrida RRF → LLM → persistir
  - load_history, append_to_session
  - TTL de sessão
- [ ] Substituir stubs em `chat.py`:
  - POST /chat/message
  - GET /chat/sessions/{id}
  - GET /chat/sessions
  - DELETE /chat/sessions/{id}
  - POST /chat/sessions/{id}/add-documento
  - POST /chat/sessions/{id}/add-artefato
  - DELETE /chat/sessions/{id}/context
- [ ] **Validar**: enviar mensagem sobre um doc enriquecido → resposta fundamentada no conteúdo

---

## Bloco 6 — Stats + CLI stats + segundo LLM provider

### T-22: StatsService + Router + CLI
- [ ] Criar `app/services/stats.py`:
  - get_stats() → totais por índice, cobertura de enriquecimento
- [ ] Substituir stub em `stats.py`
- [ ] Comando CLI `iuna stats` (mesma info formatada no terminal)
- [ ] Cache-Control: max-age=60
- [ ] **Validar**: GET /stats → cobertura correta. `iuna stats` → saída no terminal.

### T-23: Segundo LLM provider
- [ ] Implementar o outro provider (Ollama se começou com Gemini, ou vice-versa)
- [ ] Testar troca via `ACTIVE_LLM_PROVIDER`
- [ ] **Validar**: mudar env → enriquecer um doc → funciona com o outro provider

### T-24: ClaudeProvider (se necessário)
- [ ] Implementar ClaudeProvider
- [ ] **Validar**: mesmos testes

---

## Bloco 7 — Frontend de teste (web simples)

> **Ao final deste bloco**: interface web para testar busca e chat sem curl/Swagger.

### T-25: Página de busca
- [ ] Criar `frontend/` (HTML + JS simples, ou Vue/React mínimo)
- [ ] Input de busca → chama `/documentos/search` ou `/artefatos/search`
- [ ] Exibe resultados com highlights
- [ ] Filtros laterais (tipo_doc, ano, etc.)
- [ ] Widget de chat integrado na página (botão que abre sidebar)
- [ ] **Validar**: buscar termo → ver resultados com highlights na web

### T-26: Página de chat (estilo ChatGPT)
- [ ] Área de mensagens (user/assistant)
- [ ] Input de texto + enviar
- [ ] Lista de sessões na sidebar
- [ ] Botão "adicionar documento ao contexto" (abre busca inline)
- [ ] **Validar**: conversar sobre um documento enriquecido via interface web

### T-27: Servir frontend via FastAPI (ou separado)
- [ ] Servir arquivos estáticos via FastAPI (mount /static) OU docker-compose com nginx
- [ ] **Validar**: `docker compose up` → frontend acessível em localhost:3000 (ou :8000/static)

---

## Bloco 8 — Testes obrigatórios (1ª rodada)

### T-28: Testes unitários core
- [ ] test_pdf_extractor.py (PDF válido, corrompido, sem texto)
- [ ] test_query_helpers.py (funções retornam dicts corretos)
- [ ] test_scoring.py (pesos corretos, increment funciona)
- [ ] test_enrichment_service.py (com LLM mock):
  - resumo: busca content, gera, grava + timestamp
  - vetor: usa resumo como input
  - chunking: threshold 10k, split correto

### T-29: Testes integração endpoints
- [ ] Auth: sem token → 401, com token → passa
- [ ] CRUD: POST upload, GET, PATCH, DELETE (ambos tipos)
- [ ] Enrichment: POST com doc_id → grava no ES
- [ ] Search: busca retorna resultados com highlights

### T-30: Testes do ChatService
- [ ] ask_about_document + doc com chunks → busca híbrida
- [ ] ask_about_document + doc sem chunks → texto completo
- [ ] chitchat → direto ao LLM
- [ ] Sessão persistida e recuperável

---

## Bloco 9 — Testes de cobertura (2ª rodada)

### T-31: Edge cases e resiliência
- [ ] ES offline → 503
- [ ] Rasa offline → fallback
- [ ] LLM falha → exceção
- [ ] PDF corrompido → erro controlado
- [ ] chunk_size < 3000 → 422
- [ ] Doc < 10k → chunking retorna 0
- [ ] Re-upload → chunks antigos deletados
- [ ] setup-indices com dados existentes → não sobrescreve (a menos que --recreate)

### T-32: Busca avançada
- [ ] Facetas retornam agregações corretas
- [ ] Similar com embedding → kNN
- [ ] Similar sem embedding → more_like_this
- [ ] by-entity e by-keyword retornam matches corretos
- [ ] Suggest retorna sugestões
- [ ] popularity_score influencia ranking

### T-33: CLI completo
- [ ] `iuna ingest --directory` → indexa N PDFs com progresso
- [ ] `iuna ingest --enrich` → indexa + enriquece
- [ ] `iuna enrich --skip-existing` → pula docs já processados
- [ ] `iuna stats` → output correto
- [ ] `iuna delete` → remove doc + chunks

---

## Bloco 10 — Docker + deploy final

### T-34: docker-compose + Dockerfile
- [ ] Dockerfile multi-stage (build + prod)
- [ ] docker-compose: web + rasa
- [ ] Volume para modelos Rasa treinados
- [ ] **Validar**: `docker compose up` → API + Rasa + frontend rodando

### T-35: Rasa treinamento
- [ ] Criar `rasa/data/nlu.yml` com exemplos de intenções
- [ ] `rasa/config.yml`, `domain.yml`
- [ ] Treinar modelo
- [ ] **Validar**: chat classifica intenções corretamente

---

## Dependências entre Blocos

```
Bloco 1 (esqueleto) → Bloco 2 (ingestão) → Bloco 3 (enriquecimento) → Bloco 4 (busca)
                                                                         ↓
                                                                    Bloco 5 (chat)
                                                                         ↓
                                                                    Bloco 6 (stats + providers)
                                                                         ↓
                                                                    Bloco 7 (frontend)
                                                                         ↓
                                                              Bloco 8 (testes obrigatórios)
                                                                         ↓
                                                              Bloco 9 (testes cobertura)
                                                                         ↓
                                                              Bloco 10 (docker + deploy)
```

---

## Notas

- **Bloco 2 é o ponto de virada**: ao final dele, você já pode submeter PDFs e ver no ES. A API já está "útil".
- **Bloco 3 torna a busca rica**: sem enriquecimento, a busca é só BM25 básico. Com ele, ganha semelhantes, entidades, keywords.
- **Frontend (Bloco 7)**: pode ser movido para antes do Bloco 8 se preferir testar visualmente antes de escrever testes automatizados. Depois migra para projeto separado.
- **setup-indices**: NUNCA recria índices com dados a menos que `--recreate` seja passado explicitamente.
- **Samples**: a pasta `samples/` com PDFs de exemplo é essencial para validação rápida em cada bloco.
