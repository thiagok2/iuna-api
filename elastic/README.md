# Elasticsearch no IUNA API

## O que é o Elasticsearch?

Elasticsearch (ES) é um motor de busca e banco de dados distribuído baseado em índices invertidos, capaz de fazer buscas full-text, buscas vetoriais (kNN) e combinações dos dois. No IUNA, ele não é só um "banco de dados" — é o núcleo que viabiliza todas as funcionalidades de busca, enriquecimento e chat.

---

## Papel no projeto

O ES cumpre **quatro papéis simultâneos**:

| Papel | Como | Onde |
|---|---|---|
| **Document store** | Armazena PDFs (texto extraído via Tika) + metadados | `documentos_ifal_v2`, `artefatos` |
| **Vector store** | Armazena embeddings de 768 dims para busca semântica | Campo `embedding_vector` nos mesmos índices + chunks |
| **Search engine** | Full-text BM25 + kNN + RRF + facetas + autocomplete | Todos os índices de busca |
| **Session store** | Persiste histórico e contexto de conversas do chat | `chat_sessions` |

---

## Variáveis de ambiente

```bash
export ES_HOST="https://elastic.pnld-avaliacao-dev.nees.ufal.br"
export ES_USER="elastic"
export ES_PASS="<sua-senha>"
```

> Defina essas variáveis antes de rodar qualquer curl deste README.

---

## Índices do projeto

| Índice | Propósito | Mapping |
|---|---|---|
| `documentos_ifal` | Legado — mantido por outra aplicação, não alterar | `documentos_ifal_mapping_original.json` |
| `documentos_ifal_v2` | Documentos institucionais com campos de enriquecimento IA | `documentos_ifal_v2_mapping.json` |
| `documentos_ifal_v2_chunks` | Fragmentos vetorizados dos documentos v2 para RAG | `documentos_ifal_v2_mapping_chunks.json` |
| `artefatos` | Materiais didáticos (livros, planos, apostilas) | `artefatos_mapping.json` |
| `artefatos_chunks` | Fragmentos vetorizados de artefatos para RAG | `artefatos_chunks_mapping.json` |
| `chat_sessions` | Histórico e contexto de sessões de chat | `chat_sessions_mapping.json` |

O sufixo do índice é configurável via `ES_INDEX_SUFFIX` no `.env` — útil para isolar ambientes de teste (`_test`, `_dev`).

---

## Estrutura dos índices

### `documentos_ifal_v2` — documento institucional

```
documentos_ifal_v2/
├── ato/                       ← metadados e enriquecimento IA
│   ├── ato_id                 (keyword) — UUID próprio
│   ├── titulo                 (text + keyword)
│   ├── ementa                 (text + keyword)
│   ├── numero                 (text + keyword)
│   ├── tipo_doc               (text + keyword)
│   ├── tags                   (text + keyword)
│   ├── ano                    (long)
│   ├── data_publicacao        (date)
│   ├── publico                (boolean)
│   ├── fonte/
│   │   ├── orgao              (text + keyword)
│   │   ├── esfera             (text + keyword)
│   │   ├── sigla, uf, url     ...
│   ├── [Enriquecimento IA]
│   ├── resumo                 (text)       — gerado pelo LLM
│   ├── resumo_at              (date)       — timestamp da geração
│   ├── embedding_vector       (dense_vector, dims=768, cosine) — embedding do resumo ou início do doc
│   ├── embedding_vector_at    (date)
│   ├── entidades              (nested)     — [{texto, categoria, confianca}]
│   ├── entidades_at           (date)
│   ├── keywords               (text + keyword)
│   ├── keywords_at            (date)
│   ├── chunking_at            (date)
│   ├── total_chunks           (integer)   — 0 se doc < 10k chars
│   └── popularity_score       (integer)   — ranking por interações
├── attachment/
│   ├── content                (text)      — texto extraído pelo Tika (Ingest Pipeline)
│   ├── title                  (text)
│   └── content_length         (long)
├── filename                   (text + keyword)
└── data                       (text)      — PDF em base64 (campo transitório da pipeline)
```

**Campos de enriquecimento `*_at`**: timestamps que indicam quando cada operação foi executada pela última vez. Usados pelo CLI para detectar documentos não enriquecidos (`must_not: exists: {root}.resumo_at`).

---

### `documentos_ifal_v2_chunks` — fragmentos para RAG

```
documentos_ifal_v2_chunks/
├── parent_document_id   (keyword)          — FK para documentos_ifal_v2._id
├── parent_filename      (keyword)
├── chunk_index          (integer)          — posição do chunk no documento (0-based)
├── content              (text)             — texto do fragmento (~3000 chars)
├── total_chunks         (integer)          — total de chunks do doc pai
└── embedding_vector     (dense_vector, dims=768, cosine)
```

Cada chunk é um documento ES independente. A relação com o pai é via `parent_document_id`. O campo `embedding_vector` aqui é o que alimenta a busca kNN no chat RAG.

---

### `artefatos` — material didático

Estrutura idêntica a `documentos_ifal_v2`, mas com root `artefato` em vez de `ato`:

```
artefatos/
├── artefato/
│   ├── artefato_id, titulo, tipo, tags, uploaded_by
│   ├── created_at, updated_at
│   └── [mesmos campos de enriquecimento: resumo, embedding_vector, entidades, keywords, ...]
├── attachment/ { content, title, content_length }
└── filename
```

Diferença principal: artefatos têm `uploaded_by` (quem fez upload) e `tipo` livre (livro, plano\_ensino, apostila...). Documentos institucionais têm `fonte`, `orgao`, `esfera`, `tipo_doc` padronizados.

---

### `artefatos_chunks`

```
artefatos_chunks/
├── parent_document_id   (keyword)   — FK para artefatos._id
├── parent_filename      (keyword)
├── chunk_index          (integer)
├── content              (text)
├── total_chunks         (integer)
├── chunk_size           (integer)   — tamanho configurado no momento do chunking
├── embedding_vector     (dense_vector, dims=768, cosine)
└── created_at           (date)
```

---

### `chat_sessions` — sessões de chat

```
chat_sessions/
├── session_id               (keyword)
├── messages                 (nested)
│   ├── role                 (keyword)   — "user" | "assistant"
│   ├── content              (text)
│   └── timestamp            (date)
├── context_document_ids     (keyword[]) — IDs de docs no contexto da sessão
├── context_artefato_ids     (keyword[]) — IDs de artefatos no contexto
├── created_at               (date)
├── last_activity_at         (date)
└── expires_at               (date)      — TTL: filtrado em GET /chat/sessions
```

Sessões com `expires_at < now` são consideradas expiradas — o serviço as recria automaticamente ao receber nova mensagem (histórico zerado). O TTL é configurado via `CHAT_SESSION_TTL_HOURS` (padrão: 24h).

---

## Setup dos índices

### Via CLI da API (recomendado)

```bash
# Cria todos os índices de uma vez
source .venv/bin/activate
python -m app.cli.main setup-indices

# Com sufixo para isolar ambiente
python -m app.cli.main setup-indices --suffix _test

# Recriar (apaga e cria de novo — CUIDADO em produção)
python -m app.cli.main setup-indices --recreate
```

### Via curl diretamente no ES

```bash
# Listar todos os índices existentes
curl -u $ES_USER:$ES_PASS "$ES_HOST/_cat/indices?v&s=index"

# Criar documentos_ifal_v2
curl -X PUT -u $ES_USER:$ES_PASS "$ES_HOST/documentos_ifal_v2" \
  -H "Content-Type: application/json" \
  -d @elastic/documentos_ifal_v2_mapping.json

# Criar documentos_ifal_v2_chunks
curl -X PUT -u $ES_USER:$ES_PASS "$ES_HOST/documentos_ifal_v2_chunks" \
  -H "Content-Type: application/json" \
  -d @elastic/documentos_ifal_v2_mapping_chunks.json

# Criar artefatos
curl -X PUT -u $ES_USER:$ES_PASS "$ES_HOST/artefatos" \
  -H "Content-Type: application/json" \
  -d @elastic/artefatos_mapping.json

# Criar artefatos_chunks
curl -X PUT -u $ES_USER:$ES_PASS "$ES_HOST/artefatos_chunks" \
  -H "Content-Type: application/json" \
  -d @elastic/artefatos_chunks_mapping.json

# Criar chat_sessions
curl -X PUT -u $ES_USER:$ES_PASS "$ES_HOST/chat_sessions" \
  -H "Content-Type: application/json" \
  -d @elastic/chat_sessions_mapping.json
```

### Verificar mapping de um índice

```bash
curl -u $ES_USER:$ES_PASS "$ES_HOST/documentos_ifal_v2/_mapping?pretty"
curl -u $ES_USER:$ES_PASS "$ES_HOST/artefatos_chunks/_mapping?pretty"
```

---

## Ingest Pipeline — extração de texto via Tika

O ES tem um plugin chamado **Ingest Attachment Processor** que usa o Apache Tika para extrair texto de arquivos binários (PDF, DOCX, etc.). O IUNA usa isso para preencher `attachment.content` sem precisar de um serviço externo separado.

### Como funciona

```
Upload PDF
    │
    ▼
API converte PDF → base64 → salva em campo "data"
    │
    ▼
ES executa pipeline "attachment" no documento
    │
    ▼
Tika extrai texto do base64
    │
    ▼
Resultado salvo em "attachment.content" (campo indexado para busca)
    │
    ▼
Campo "data" (base64 bruto) é removido do _source para economizar espaço
```

### Verificar se o plugin está instalado

```bash
curl -u $ES_USER:$ES_PASS "$ES_HOST/_ingest/pipeline/attachment?pretty"
```

Resposta esperada: JSON com a pipeline `attachment`. Se retornar 404, o plugin não está ativo.

### Verificar pipeline

```bash
# Listar todas as pipelines
curl -u $ES_USER:$ES_PASS "$ES_HOST/_ingest/pipeline?pretty"

# Testar a pipeline com um PDF em base64 (exemplo)
curl -X POST -u $ES_USER:$ES_PASS "$ES_HOST/_ingest/pipeline/attachment/_simulate" \
  -H "Content-Type: application/json" \
  -d '{
    "docs": [{
      "_source": {
        "data": "<BASE64_DO_PDF>"
      }
    }]
  }'
```

---

## Estratégias de busca implementadas

### 1. Full-text com BM25 + popularity score

Endpoint: `GET /api/v1/documentos/search?q=edital&tipo_doc=edital&ano=2024`

O ranking combina o score BM25 do ES com o `popularity_score` do documento:

```
score_final = bm25_score + log1p(popularity_score * 0.5)
```

A função `log1p` amortece documentos muito populares para não sufocar a relevância textual.

```bash
# Full-text simples
curl -u $ES_USER:$ES_PASS "$ES_HOST/documentos_ifal_v2/_search?pretty" \
  -H "Content-Type: application/json" \
  -d '{
    "query": {
      "function_score": {
        "query": {
          "bool": {
            "must": [{
              "multi_match": {
                "query": "edital seleção 2024",
                "fields": ["ato.titulo^2", "ato.ementa", "attachment.content"],
                "type": "best_fields",
                "fuzziness": "AUTO"
              }
            }]
          }
        },
        "functions": [{
          "field_value_factor": {
            "field": "ato.popularity_score",
            "missing": 0,
            "modifier": "log1p",
            "factor": 0.5
          }
        }],
        "boost_mode": "sum"
      }
    },
    "highlight": {
      "fields": { "attachment.content": {}, "ato.titulo": {} }
    },
    "size": 10
  }'
```

### 2. Busca com frase exata

```bash
curl -u $ES_USER:$ES_PASS "$ES_HOST/documentos_ifal_v2/_search?pretty" \
  -H "Content-Type: application/json" \
  -d '{
    "query": {
      "multi_match": {
        "query": "progressão funcional por titulação",
        "fields": ["ato.titulo^2", "ato.ementa", "attachment.content"],
        "type": "phrase"
      }
    }
  }'
```

### 3. Facetas / Agregações

Para filtros laterais (tipo_doc, esfera, orgao...):

```bash
curl -u $ES_USER:$ES_PASS "$ES_HOST/documentos_ifal_v2/_search?pretty" \
  -H "Content-Type: application/json" \
  -d '{
    "query": { "match": { "ato.titulo": "resolução" } },
    "aggs": {
      "por_tipo": { "terms": { "field": "ato.tipo_doc.keyword", "size": 20 } },
      "por_orgao": { "terms": { "field": "ato.fonte.orgao.keyword", "size": 20 } },
      "por_esfera": { "terms": { "field": "ato.fonte.esfera.keyword", "size": 10 } },
      "por_ano": { "terms": { "field": "ato.ano", "size": 10 } }
    },
    "size": 0
  }'
```

### 4. More Like This (MLT) — documentos similares simples

```bash
curl -u $ES_USER:$ES_PASS "$ES_HOST/documentos_ifal_v2/_search?pretty" \
  -H "Content-Type: application/json" \
  -d '{
    "query": {
      "more_like_this": {
        "fields": ["ato.titulo", "ato.ementa", "attachment.content"],
        "like": [{ "_index": "documentos_ifal_v2", "_id": "TjcA7psBL-x_8ArHDqI6" }],
        "min_term_freq": 1,
        "max_query_terms": 12,
        "min_doc_freq": 1
      }
    },
    "size": 10
  }'
```

### 5. Busca relacionada com RRF — o algoritmo completo (search_related)

Endpoint: `GET /api/v1/documentos/search/related/{id}?limit=10`

Combina até **4 sinais** de relevância em um único request via **Reciprocal Rank Fusion (RRF)**:

| Sinal | Disponível quando | Boost |
|---|---|---|
| MLT (ementa + título + conteúdo) | Sempre | 0.5 |
| Nested match em entidades | `entidades` preenchido | 1.5 |
| Terms em keywords | `keywords` preenchido | 1.2 |
| kNN no embedding_vector | `embedding_vector` preenchido | via RRF |

```bash
# Busca relacionada com todos os sinais (doc com enriquecimento completo)
curl -u $ES_USER:$ES_PASS "$ES_HOST/documentos_ifal_v2/_search?pretty" \
  -H "Content-Type: application/json" \
  -d '{
    "query": {
      "bool": {
        "should": [
          {
            "more_like_this": {
              "fields": ["ato.ementa", "ato.titulo", "attachment.content"],
              "like": [{ "_index": "documentos_ifal_v2", "_id": "TjcA7psBL-x_8ArHDqI6" }],
              "boost": 0.5
            }
          },
          {
            "nested": {
              "path": "ato.entidades",
              "query": {
                "bool": {
                  "should": [
                    { "match": { "ato.entidades.texto": "auditoria" } },
                    { "match": { "ato.entidades.texto": "controle interno" } }
                  ]
                }
              },
              "boost": 1.5
            }
          },
          {
            "terms": {
              "ato.keywords.keyword": ["auditoria", "ifal", "controle"],
              "boost": 1.2
            }
          }
        ],
        "must_not": [{ "term": { "_id": "TjcA7psBL-x_8ArHDqI6" } }]
      }
    },
    "knn": {
      "field": "ato.embedding_vector",
      "query_vector": [0.01, -0.02, 0.03],
      "k": 10,
      "num_candidates": 20,
      "filter": { "bool": { "must_not": [{ "term": { "_id": "TjcA7psBL-x_8ArHDqI6" } }] } }
    },
    "rank": { "rrf": { "window_size": 20 } },
    "size": 10
  }'
```

> **Nota sobre licença**: RRF + kNN juntos exigem licença Platinum/Enterprise. Em licença Basic o serviço cai automaticamente para BM25 + bool query sem perda de dados.

### 6. Busca por entidade

```bash
# Todos os documentos que mencionam a entidade "IFAL"
curl -u $ES_USER:$ES_PASS "$ES_HOST/documentos_ifal_v2/_search?pretty" \
  -H "Content-Type: application/json" \
  -d '{
    "query": {
      "nested": {
        "path": "ato.entidades",
        "query": {
          "bool": {
            "must": [
              { "match": { "ato.entidades.texto": "IFAL" } }
            ]
          }
        }
      }
    }
  }'

# Com filtro por categoria (ex: ORG, PER, LOC)
curl -u $ES_USER:$ES_PASS "$ES_HOST/documentos_ifal_v2/_search?pretty" \
  -H "Content-Type: application/json" \
  -d '{
    "query": {
      "nested": {
        "path": "ato.entidades",
        "query": {
          "bool": {
            "must": [
              { "match": { "ato.entidades.texto": "IFAL" } },
              { "term": { "ato.entidades.categoria": "ORG" } }
            ]
          }
        }
      }
    }
  }'
```

### 7. Busca por keyword

```bash
# Todos os docs com keyword "educação"
curl -u $ES_USER:$ES_PASS "$ES_HOST/documentos_ifal_v2/_search?pretty" \
  -H "Content-Type: application/json" \
  -d '{
    "query": {
      "term": { "ato.keywords.keyword": "educação" }
    }
  }'
```

### 8. Autocomplete / Suggest

```bash
# Sugestões de título que começam com "edital de"
curl -u $ES_USER:$ES_PASS "$ES_HOST/documentos_ifal_v2/_search?pretty" \
  -H "Content-Type: application/json" \
  -d '{
    "query": {
      "match_phrase_prefix": {
        "ato.titulo": { "query": "edital de", "max_expansions": 10 }
      }
    },
    "_source": ["ato.titulo"],
    "size": 5
  }'
```

### 9. Busca full-text nos chunks (para RAG)

```bash
# Busca dentro dos chunks de um documento específico
curl -u $ES_USER:$ES_PASS "$ES_HOST/documentos_ifal_v2_chunks/_search?pretty" \
  -H "Content-Type: application/json" \
  -d '{
    "query": {
      "bool": {
        "must": [{ "match": { "content": { "query": "prazo de inscrição", "fuzziness": "AUTO" } } }],
        "filter": [{ "term": { "parent_document_id": "TjcA7psBL-x_8ArHDqI6" } }]
      }
    },
    "highlight": {
      "fields": { "content": { "fragment_size": 200, "number_of_fragments": 2 } }
    }
  }'

# Busca em todos os chunks (sem filtrar por documento)
curl -u $ES_USER:$ES_PASS "$ES_HOST/documentos_ifal_v2_chunks,artefatos_chunks/_search?pretty" \
  -H "Content-Type: application/json" \
  -d '{
    "query": { "match": { "content": "progressão funcional" } },
    "size": 5
  }'
```

### 10. Busca híbrida nos chunks — kNN + BM25 + RRF (chat RAG)

É a query que o `ChatService` executa ao buscar contexto para o LLM:

```bash
curl -u $ES_USER:$ES_PASS "$ES_HOST/documentos_ifal_v2_chunks/_search?pretty" \
  -H "Content-Type: application/json" \
  -d '{
    "query": {
      "bool": {
        "must": [{ "match": { "content": "responsabilidades do auditor" } }],
        "filter": [{ "term": { "parent_document_id": "TjcA7psBL-x_8ArHDqI6" } }]
      }
    },
    "knn": {
      "field": "embedding_vector",
      "query_vector": [0.01, -0.02, 0.03],
      "k": 5,
      "num_candidates": 50,
      "filter": { "term": { "parent_document_id": "TjcA7psBL-x_8ArHDqI6" } }
    },
    "rank": { "rrf": { "window_size": 10 } },
    "size": 5
  }'
```

---

## Estratégia de embedding

Cada documento pode ter `embedding_vector` gerado de duas formas, registradas em `embedding_source`:

| Estado | O que é embedado | `embedding_source` |
|---|---|---|
| Resumo existe | `{root}.resumo` | `"resumo"` |
| Sem resumo | Primeiros 5000 chars de `attachment.content` | `"inicio_documento"` |

`--vectorize` é independente de `--summarize`. Não gera resumo automaticamente. Quando o resumo for gerado depois, basta rodar `--vectorize` de novo para atualizar o embedding.

---

## Scoring de popularidade

Cada documento tem `ato.popularity_score` (documentos) ou `artefato.popularity_score` (artefatos), incrementado por ações do usuário:

| Ação | Pontos | Quando acontece |
|---|---|---|
| `click` | +1 | Usuário clica no resultado na busca |
| `download` | +2 | Usuário baixa o documento |
| `share` | +2 | Usuário compartilha |
| `add_to_chat` | +3 | Documento é adicionado ao contexto do chat |

O score influencia o ranking via `function_score` (seção "Full-text" acima). Não substitui a relevância textual — é somado a ela com amortecimento logarítmico.

```bash
# Ver popularity_score de um documento
curl -u $ES_USER:$ES_PASS \
  "$ES_HOST/documentos_ifal_v2/TjcA7psBL-x_8ArHDqI6/_source?_source_includes=ato.popularity_score"
```

---

## Sessões de chat — TTL e contexto

As sessões têm **TTL automático** via campo `expires_at`. A API:
- **Ao receber mensagem**: verifica se `expires_at > now`. Se não, recria a sessão com histórico zerado.
- **Ao processar mensagem com sucesso**: renova `expires_at = now + CHAT_SESSION_TTL_HOURS`.

Para listar sessões ativas:

```bash
# Sessões que não expiraram ainda
curl -u $ES_USER:$ES_PASS "$ES_HOST/chat_sessions/_search?pretty" \
  -H "Content-Type: application/json" \
  -d '{
    "query": {
      "range": { "expires_at": { "gt": "now" } }
    },
    "sort": [{ "last_activity_at": { "order": "desc" } }]
  }'

# Ver uma sessão específica com contexto
curl -u $ES_USER:$ES_PASS "$ES_HOST/chat_sessions/test-session-001?pretty"
```

---

## Comandos de diagnóstico

```bash
# Contar documentos por índice
curl -u $ES_USER:$ES_PASS "$ES_HOST/documentos_ifal_v2/_count"
curl -u $ES_USER:$ES_PASS "$ES_HOST/artefatos/_count"
curl -u $ES_USER:$ES_PASS "$ES_HOST/documentos_ifal_v2_chunks/_count"
curl -u $ES_USER:$ES_PASS "$ES_HOST/artefatos_chunks/_count"
curl -u $ES_USER:$ES_PASS "$ES_HOST/chat_sessions/_count"

# Documentos SEM resumo (não enriquecidos)
curl -u $ES_USER:$ES_PASS "$ES_HOST/documentos_ifal_v2/_count?pretty" \
  -H "Content-Type: application/json" \
  -d '{ "query": { "bool": { "must_not": [{ "exists": { "field": "ato.resumo_at" } }] } } }'

# Documentos SEM embedding
curl -u $ES_USER:$ES_PASS "$ES_HOST/documentos_ifal_v2/_count?pretty" \
  -H "Content-Type: application/json" \
  -d '{ "query": { "bool": { "must_not": [{ "exists": { "field": "ato.embedding_vector_at" } }] } } }'

# Cobertura de enriquecimento completa (todos os campos)
curl -u $ES_USER:$ES_PASS "$ES_HOST/documentos_ifal_v2/_search?pretty&size=0" \
  -H "Content-Type: application/json" \
  -d '{
    "aggs": {
      "com_resumo":    { "filter": { "exists": { "field": "ato.resumo_at" } } },
      "com_embedding": { "filter": { "exists": { "field": "ato.embedding_vector_at" } } },
      "com_entidades": { "filter": { "exists": { "field": "ato.entidades_at" } } },
      "com_keywords":  { "filter": { "exists": { "field": "ato.keywords_at" } } },
      "com_chunks":    { "filter": { "exists": { "field": "ato.chunking_at" } } }
    }
  }'

# Ver um documento completo (sem attachment.content para legibilidade)
curl -u $ES_USER:$ES_PASS "$ES_HOST/documentos_ifal_v2/TjcA7psBL-x_8ArHDqI6?pretty" \
  -H "Content-Type: application/json" \
  -d '{ "_source_excludes": ["attachment.content", "data", "ato.embedding_vector"] }'

# Verificar saúde do cluster
curl -u $ES_USER:$ES_PASS "$ES_HOST/_cluster/health?pretty"

# Ver versão do ES e licença
curl -u $ES_USER:$ES_PASS "$ES_HOST/?pretty"
curl -u $ES_USER:$ES_PASS "$ES_HOST/_license?pretty"
```

---

## Migração do legado (documentos_ifal → documentos_ifal_v2)

O índice `documentos_ifal` (original) é mantido por outra aplicação. O `documentos_ifal_v2` é a evolução com campos de enriquecimento.

```bash
# Copia todos os documentos preservando _id
curl -X POST -u $ES_USER:$ES_PASS "$ES_HOST/_reindex?pretty" \
  -H "Content-Type: application/json" \
  -d '{
    "source": { "index": "documentos_ifal" },
    "dest":   { "index": "documentos_ifal_v2", "op_type": "create" }
  }'

# Verificar contagem após migração
curl -u $ES_USER:$ES_PASS "$ES_HOST/documentos_ifal/_count"
curl -u $ES_USER:$ES_PASS "$ES_HOST/documentos_ifal_v2/_count"
```

Após a migração, os campos de enriquecimento (`resumo`, `embedding_vector`, etc.) estarão vazios. Use o CLI para preenchê-los:

```bash
python -m app.cli.main enrich \
  --source-type documentos_ifal_v2 \
  --from-es \
  --summarize --entities --keywords --vectorize --chunk
```

---

## Deletar índice (CUIDADO)

```bash
# Deletar índice de teste
curl -X DELETE -u $ES_USER:$ES_PASS "$ES_HOST/artefatos_test"

# Deletar todos os chunks de um documento específico
curl -X POST -u $ES_USER:$ES_PASS "$ES_HOST/documentos_ifal_v2_chunks/_delete_by_query" \
  -H "Content-Type: application/json" \
  -d '{
    "query": { "term": { "parent_document_id": "ID_DO_DOCUMENTO" } }
  }'
```

---

## Arquivos nesta pasta

| Arquivo | Propósito |
|---|---|
| `documentos_ifal_v2_mapping.json` | Mapping de `documentos_ifal_v2` |
| `documentos_ifal_v2_mapping_chunks.json` | Mapping de `documentos_ifal_v2_chunks` |
| `artefatos_mapping.json` | Mapping de `artefatos` |
| `artefatos_chunks_mapping.json` | Mapping de `artefatos_chunks` |
| `chat_sessions_mapping.json` | Mapping de `chat_sessions` |
| `documentos_ifal_mapping_original.json` | Referência do índice legado (não alterar) |
| `setup/` | Scripts de setup e configuração das pipelines |
| `README.md` | Este arquivo |
