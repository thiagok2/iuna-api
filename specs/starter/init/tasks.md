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
- [x] **Validar** (ES online):
  ```
  source .venv/bin/activate
  python -m app.cli.main setup-indices
  ```
  Saída esperada (se índices já existem):
  ```
  🔌 Conectado ao Elasticsearch
  ⏭  documentos_ifal_v2 — Already exists
  ⏭  documentos_ifal_v2_chunks — Already exists
  ⏭  artefatos — Already exists
  ⏭  artefatos_chunks — Already exists
  ⏭  chat_sessions — Already exists
  🏁 setup-indices finalizado.
  ```
  Testar criação de índices de teste:
  ```
  python -m app.cli.main setup-indices --suffix _test
  ```
  Deve criar 5 índices com sufixo `_test`. Verificar:
  ```
  curl -H "Authorization: Basic ZWxhc3RpYzpTWFR0NHJrMDV1RHE=" "https://elastic.pnld-avaliacao-dev.nees.ufal.br/_cat/indices?v" | grep _test
  ```

### T-05: PDF Extractor + samples/
- [x] Criar `app/core/pdf_extractor_local.py` (fallback local: pdfplumber + PyPDF2)
- [x] Estratégia primária: ES Ingest Attachment Pipeline (Apache Tika)
- [x] Criar pasta `samples/` com PDFs de exemplo
- [x] **Validar fallback local**:
  ```
  source .venv/bin/activate
  python samples/test_extractor.py
  ```
- [x] **Validar pipeline ES** (quando ES estiver online):
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
- [x] **Validar** (ES online):
  1. Upload via curl:
  ```
  curl -X POST -H "Authorization: Bearer 77c7fa54-9b2c-44c1-a7e2-aea881a7797e" \
    -F "file=@samples/edital_selecao.pdf" \
    -F "titulo=Edital Seleção 2024" \
    -F "tipo_doc=edital" \
    -F "ano=2024" \
    -F "orgao=IFAL" \
    http://localhost:8000/api/v1/documentos/upload
  ```
  Resposta esperada: `{"success": true, "data": {"_id": "...", "ato_id": "...", "filename": "edital_selecao.pdf"}}`

  2. Verificar que o doc existe no ES:
  ```
  curl -H "Authorization: Bearer 77c7fa54-9b2c-44c1-a7e2-aea881a7797e" \
    http://localhost:8000/api/v1/documentos/by-filename/edital_selecao.pdf
  ```
  Deve retornar o doc com `attachment.content` preenchido (texto extraído pelo Tika).

  3. Listar documentos:
  ```
  curl -H "Authorization: Bearer 77c7fa54-9b2c-44c1-a7e2-aea881a7797e" \
    "http://localhost:8000/api/v1/documentos/?page=1&page_size=5"
  ```

  4. Atualizar metadados:
  ```
  curl -X PATCH -H "Authorization: Bearer 77c7fa54-9b2c-44c1-a7e2-aea881a7797e" \
    -H "Content-Type: application/json" \
    -d '{"tags": ["educação", "seleção"]}' \
    http://localhost:8000/api/v1/documentos/<ID_RETORNADO>
  ```

  5. Deletar:
  ```
  curl -X DELETE -H "Authorization: Bearer 77c7fa54-9b2c-44c1-a7e2-aea881a7797e" \
    http://localhost:8000/api/v1/documentos/<ID_RETORNADO>
  ```

### T-08: ArtefatosCrudService + Router
- [x] Criar `app/services/artefatos_crud.py`:
  - `upload(file_bytes, filename, titulo, uploaded_by, tipo, tags)` → extrai texto, indexa
  - `get_by_id`, `get_by_filename`, `delete`, `list_all`, `update_metadata`
  - Re-upload: deleta chunks antigos antes de reindexar
- [x] Substituir stubs em `crud_artefatos.py`
- [x] **Validar** (ES online):
  1. Upload artefato:
  ```
  curl -X POST -H "Authorization: Bearer 77c7fa54-9b2c-44c1-a7e2-aea881a7797e" \
    -F "file=@samples/plano_ensino_programacao.pdf" \
    -F "titulo=Plano de Ensino - Programação I" \
    -F "tipo=plano_ensino" \
    -F "tags=programação,python" \
    -F "uploaded_by=admin" \
    http://localhost:8000/api/v1/artefatos/upload
  ```
  Resposta esperada: `{"success": true, "data": {"_id": "...", "artefato_id": "...", "filename": "plano_ensino_programacao.pdf"}}`

  2. Buscar por filename:
  ```
  curl -H "Authorization: Bearer 77c7fa54-9b2c-44c1-a7e2-aea881a7797e" \
    http://localhost:8000/api/v1/artefatos/by-filename/plano_ensino_programacao.pdf
  ```

  3. Re-upload com force (deve sobrescrever):
  ```
  curl -X POST -H "Authorization: Bearer 77c7fa54-9b2c-44c1-a7e2-aea881a7797e" \
    -F "file=@samples/plano_ensino_programacao.pdf" \
    -F "titulo=Plano de Ensino - Programação I (v2)" \
    -F "force=true" \
    -F "uploaded_by=admin" \
    http://localhost:8000/api/v1/artefatos/upload
  ```

  4. Re-upload SEM force (deve dar 409):
  ```
  curl -X POST -H "Authorization: Bearer 77c7fa54-9b2c-44c1-a7e2-aea881a7797e" \
    -F "file=@samples/plano_ensino_programacao.pdf" \
    -F "titulo=Teste conflito" \
    -F "uploaded_by=admin" \
    http://localhost:8000/api/v1/artefatos/upload
  ```
  Resposta esperada: HTTP 409 `{"success": false, "error": "Artefato já existe: ..."}`

### T-09: CLI ingest
- [x] Comando `iuna ingest --source-type <tipo> --directory <path> [--force] [--concurrency N]`
- [x] Por default: só indexa (ES only, sem LLM)
- [x] Flag `--enrich` (por agora stub: print "enrich not implemented yet")
- [x] `--force` para sobrescrever existentes. Sem `--force` → pula se filename já existe.
- [x] Progresso no terminal.
- [x] **Validar** (ES online):
  1. Ingestar artefatos do diretório samples:
  ```
  source .venv/bin/activate
  python -m app.cli.main ingest --source-type artefatos --directory ./samples/
  ```
  Saída esperada:
  ```
  📂 Encontrados 3 arquivos PDF em: ./samples/
  📌 Tipo: artefatos | Force: False | Concurrency: 3
  
    ✅ [1/3] documento_institucional.pdf
    ✅ [2/3] edital_selecao.pdf
    ✅ [3/3] plano_ensino_programacao.pdf
  
  🏁 Ingestão finalizada: 3 sucesso, 0 erro(s)
  ```

  2. Rodar de novo SEM --force (deve pular por conflito):
  ```
  python -m app.cli.main ingest --source-type artefatos --directory ./samples/
  ```
  Saída esperada: erros de conflito (409) para cada arquivo.

  3. Rodar com --force (deve sobrescrever):
  ```
  python -m app.cli.main ingest --source-type artefatos --directory ./samples/ --force
  ```
  Saída esperada: 3 sucesso.

  4. Verificar no ES que os docs existem:
  ```
  curl -H "Authorization: Basic ZWxhc3RpYzpTWFR0NHJrMDV1RHE=" \
    "https://elastic.pnld-avaliacao-dev.nees.ufal.br/artefatos/_count"
  ```

  5. Testar com documentos_ifal_v2:
  ```
  python -m app.cli.main ingest --source-type documentos_ifal_v2 --directory ./samples/ --force
  ```

---

## Bloco 3 — LLM Providers + Enriquecimento funcional

> **Ao final deste bloco**: Documentos podem ser enriquecidos (resumo, entidades, keywords, embedding, chunks). Validável via API e CLI.

### T-10: LLM Interface + Factory + primeiro provider
- [x] Criar `app/providers/base.py` (BaseLLMProvider ABC async)
- [x] Criar `app/providers/factory.py`
- [x] Implementar GeminiProvider e ClaudeProvider (Ollama em aberto)
- [x] Modelos configuráveis via `.env` (`GEMINI_TEXT_MODEL`, `GEMINI_EMBED_MODEL`, `CLAUDE_MODEL`)
- [x] **Validar**: `PYTHONPATH=. python tests/manual/t10_provider_smoke.py`

### T-11: EnrichmentService
- [x] Criar `app/services/enrichment.py` com todos os métodos
- [x] **Validar**: `PYTHONPATH=. python tests/manual/t11_enrichment_service.py`

### T-12: Routers de enriquecimento
- [x] `app/api/routers/enrichment.py` com todos os endpoints implementados
- [x] **Validar**: `bash tests/manual/t12_enrichment_api.sh` (servidor local rodando)

### T-13: CLI enrich
- [x] Comando `iuna enrich` com todas as flags
- [x] `iuna ingest --enrich` integrado
- [x] **Validar**: `bash tests/manual/t13_cli_enrich.sh`

---

## Bloco 4 — Busca funcional

> **Ao final deste bloco**: Busca full-text, filtros, facetas, semelhantes, por entidade, por keyword, chunks e autocomplete funcionando.

### T-14: query_helpers.py
- [x] Criar `app/core/query_helpers.py` — funções puras
- [ ] **Validar**: `PYTHONPATH=. python tests/manual/t14_query_helpers.py`

### T-15: DocumentosSearchService + Router
- [x] Criar `app/services/documentos_search.py` (estende `_search_base.py`)
- [x] Substituir stubs em `search_documentos.py`
- [ ] **Validar**: `bash tests/manual/t15_t16_t17_search_api.sh`

### T-16: ArtefatosSearchService + Router
- [x] Criar `app/services/artefatos_search.py`
- [x] Substituir stubs em `search_artefatos.py`
- [ ] **Validar**: `bash tests/manual/t15_t16_t17_search_api.sh`

### T-17: ChunksSearchService + Router
- [x] Criar `app/services/chunks_search.py`
- [x] Endpoints: `GET /{tipo}/search/chunks`
- [ ] **Validar**: `bash tests/manual/t15_t16_t17_search_api.sh`

### T-18: Scoring (popularity)
- [x] Criar `app/core/scoring.py` (constantes `SCORE_WEIGHTS`)
- [x] Criar `app/services/scoring_service.py` (`increment_score`)
- [x] Substituir stubs em `scoring.py`; `function_score` na busca
- [ ] **Validar**: `bash tests/manual/t18_scoring.sh`

### T-19: Listagem de entidades e keywords
- [x] `GET /documentos/entities`, `GET /artefatos/entities`
- [x] `GET /documentos/keywords`, `GET /artefatos/keywords`
- [ ] **Validar**: `bash tests/manual/t19_entities_keywords.sh`

### T-19b: Busca Legado (documentos_ifal)
- [x] Criar `app/services/legado_search_service.py`:
  - `search(index, q, page, page_size, exact_phrase, tipo_doc, esfera, ano, orgao, publico, periodo, with_aggregations)`
  - `get_by_id(index, doc_id)` — equivalente ao `viewNormativa` do Laravel
  - `similar(index, doc_id, page_size)` — MLT em `ato.ementa` + `ato.tags`
  - `_periodo_to_range(periodo)` — converte `"2024"` ou `"2020-2024"` para filtro range ES
- [x] Criar `app/api/routers/search_legado.py` (prefixo `/legado/documentos`, tag `legado - documentos_ifal`):
  - `GET /search` com filtros legados + `exact_phrase` + `with_aggregations` (default `True`)
  - `GET /{doc_id}/similar` registrado **antes** de `/{doc_id}` (evitar conflito FastAPI)
  - `GET /{doc_id}` (viewNormativa)
- [x] Adicionar `index_documentos_ifal` (property) em `app/config.py`
- [x] Registrar `search_legado_router` em `app/main.py`
- [x] Propagar `exact_phrase` e `with_aggregations` para `search_documentos.py` e `search_artefatos.py` (v2)
- [ ] **Validar**: `bash tests/manual/t19b_busca_legado.sh`

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
- [ ] test_pdf_extractor_local.py (PDF válido, corrompido, sem texto)
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
- [ ] Ingestão em lote:
  ```
  python -m app.cli.main ingest --source-type artefatos --directory ./samples/
  ```
  Verificar: progresso exibido, PDFs indexados, contagem correta no ES.

- [ ] Ingestão com --force:
  ```
  python -m app.cli.main ingest --source-type artefatos --directory ./samples/ --force
  ```
  Verificar: sobrescreve existentes sem erro.

- [ ] Ingestão + enriquecimento (após T-13 implementado):
  ```
  python -m app.cli.main ingest --source-type artefatos --directory ./samples/ --force --enrich
  ```
  Verificar: após indexar, cada doc é enriquecido (entidades, keywords, resumo, vector, chunks).

- [ ] Enriquecimento seletivo:
  ```
  python -m app.cli.main enrich --source-type artefatos --ids <ID1>,<ID2> --summarize --entities
  ```
  Verificar: só resumo e entidades gerados, demais campos inalterados.

- [ ] Skip existing:
  ```
  python -m app.cli.main enrich --source-type artefatos --directory ./samples/ --enrich --skip-existing
  ```
  Verificar: docs já enriquecidos são pulados (verifica `*_at`).

- [ ] Stats:
  ```
  python -m app.cli.main stats
  ```
  Saída esperada:
  ```
  📊 Estatísticas IUNA API
  
  documentos_ifal_v2: 2512 docs | sem_resumo: 2512 | sem_entidades: 2512 | sem_embedding: 2512 | sem_chunking: 2512
  artefatos: 3 docs | sem_resumo: 3 | sem_entidades: 3 | sem_embedding: 3 | sem_chunking: 3
  chunks: documentos_ifal_v2_chunks: 0 | artefatos_chunks: 0
  ```

- [ ] Delete:
  ```
  python -m app.cli.main delete --source-type artefatos --id <ARTEFATO_ID>
  ```
  Verificar: doc removido + chunks removidos.

- [ ] Setup-indices com sufixo:
  ```
  python -m app.cli.main setup-indices --suffix _test
  ```
  Verificar: 5 índices `*_test` criados. Depois limpar:
  ```
  python -m app.cli.main setup-indices --suffix _test --recreate
  ```

- [ ] **Testes de borda — CLI**:
  ```
  # Diretório inexistente
  python -m app.cli.main ingest --source-type artefatos --directory ./nao_existe/
  # Esperado: ❌ Diretório não encontrado (exit code 1)

  # Diretório sem PDFs
  mkdir -p /tmp/vazio && python -m app.cli.main ingest --source-type artefatos --directory /tmp/vazio/
  # Esperado: ⚠️ Nenhum arquivo PDF encontrado (exit code 0)

  # source-type inválido
  python -m app.cli.main ingest --source-type invalido --directory ./samples/
  # Esperado: ❌ source-type inválido (exit code 1)

  # ES offline → erro de conexão
  # (temporariamente alterar ELASTICSEARCH_HOSTS no .env para host errado)
  python -m app.cli.main ingest --source-type artefatos --directory ./samples/
  # Esperado: ❌ Erro ao conectar ao Elasticsearch (exit code 1)

  # ID inexistente no enrich
  python -m app.cli.main enrich --source-type artefatos --ids id-fantasma --enrich
  # Esperado: ❌ NotFoundError

  # --recreate com confirmação 'n' → cancela
  python -m app.cli.main setup-indices --recreate
  # Digitar: n → Esperado: Operação cancelada.

  # Enrich sem flags de operação
  python -m app.cli.main enrich --source-type artefatos --ids <ID>
  # Esperado: ⚠️ Nenhuma operação selecionada (ou erro)

  # Doc pequeno → chunking pulado
  python -m app.cli.main enrich --source-type artefatos --ids <ID_PEQUENO> --chunk
  # Esperado: ⏭ content < 10000 chars, chunking pulado
  ```

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
