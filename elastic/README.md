# Elasticsearch — Setup e Comandos

## Índices do Projeto

| Índice | Arquivo de Mapping | Propósito |
|--------|-------------------|-----------|
| `documentos` | `documentos_mapping.json` | Documentos institucionais (novo, com enriquecimento) |
| `documentos_chunks` | `documentos_chunks_mapping.json` | Chunks de documentos |
| `artefatos` | `artefatos_mapping.json` | PDFs genéricos (livros, materiais) |
| `artefatos_chunks` | `artefatos_chunks_mapping.json` | Chunks de artefatos |
| `chat_sessions` | `chat_sessions_mapping.json` | Histórico de conversas |

> **Nota**: O índice `documentos_ifal` (original) continua existindo e é usado por outra aplicação. O novo índice `documentos` é uma evolução com campos de enriquecimento. Os dados podem ser migrados via reindex.

---

## Variáveis de Ambiente

```bash
export ES_HOST="http://elastic.pnld-avaliacao-dev.nees.ufal.br"
export ES_USER="elastic"
export ES_PASS="<sua-senha>"
```

---

## 1. Verificar Conexão

```bash
curl -u $ES_USER:$ES_PASS "$ES_HOST"
```

---

## 2. Listar Índices Existentes

```bash
curl -u $ES_USER:$ES_PASS "$ES_HOST/_cat/indices?v"
```

---

## 3. Criar Índices

> ⚠️ Só cria se o índice NÃO existir. Verifique antes com o comando acima.

### Criar índice `documentos`
```bash
curl -X PUT -u $ES_USER:$ES_PASS "$ES_HOST/documentos" \
  -H "Content-Type: application/json" \
  -d @elastic/documentos_mapping.json
```

### Criar índice `documentos_chunks`
```bash
curl -X PUT -u $ES_USER:$ES_PASS "$ES_HOST/documentos_chunks" \
  -H "Content-Type: application/json" \
  -d @elastic/documentos_chunks_mapping.json
```

### Criar índice `artefatos`
```bash
curl -X PUT -u $ES_USER:$ES_PASS "$ES_HOST/artefatos" \
  -H "Content-Type: application/json" \
  -d @elastic/artefatos_mapping.json
```

### Criar índice `artefatos_chunks`
```bash
curl -X PUT -u $ES_USER:$ES_PASS "$ES_HOST/artefatos_chunks" \
  -H "Content-Type: application/json" \
  -d @elastic/artefatos_chunks_mapping.json
```

### Criar índice `chat_sessions`
```bash
curl -X PUT -u $ES_USER:$ES_PASS "$ES_HOST/chat_sessions" \
  -H "Content-Type: application/json" \
  -d @elastic/chat_sessions_mapping.json
```

---

## 4. Verificar Mapping de um Índice

```bash
curl -u $ES_USER:$ES_PASS "$ES_HOST/documentos/_mapping?pretty"
curl -u $ES_USER:$ES_PASS "$ES_HOST/artefatos/_mapping?pretty"
```

---

## 5. Migrar Dados de `documentos_ifal` → `documentos`

> Copia todos os documentos do índice original para o novo. Os campos de enriquecimento ficarão vazios (serão preenchidos pelo `iuna enrich`).

```bash
curl -X POST -u $ES_USER:$ES_PASS "$ES_HOST/_reindex" \
  -H "Content-Type: application/json" \
  -d '{
    "source": { "index": "documentos_ifal" },
    "dest": { "index": "documentos" }
  }'
```

### Verificar contagem após migração
```bash
curl -u $ES_USER:$ES_PASS "$ES_HOST/documentos/_count"
curl -u $ES_USER:$ES_PASS "$ES_HOST/documentos_ifal/_count"
```

---

## 6. Deletar Índice (CUIDADO)

> ⚠️ Só usar em ambiente de teste ou se tiver certeza. Irreversível.

```bash
curl -X DELETE -u $ES_USER:$ES_PASS "$ES_HOST/documentos"
curl -X DELETE -u $ES_USER:$ES_PASS "$ES_HOST/artefatos"
```

---

## 7. Criar Índices de Teste (sufixo _test)

```bash
curl -X PUT -u $ES_USER:$ES_PASS "$ES_HOST/documentos_test" \
  -H "Content-Type: application/json" \
  -d @elastic/documentos_mapping.json

curl -X PUT -u $ES_USER:$ES_PASS "$ES_HOST/artefatos_test" \
  -H "Content-Type: application/json" \
  -d @elastic/artefatos_mapping.json

curl -X PUT -u $ES_USER:$ES_PASS "$ES_HOST/artefatos_chunks_test" \
  -H "Content-Type: application/json" \
  -d @elastic/artefatos_chunks_mapping.json

curl -X PUT -u $ES_USER:$ES_PASS "$ES_HOST/documentos_chunks_test" \
  -H "Content-Type: application/json" \
  -d @elastic/documentos_chunks_mapping.json

curl -X PUT -u $ES_USER:$ES_PASS "$ES_HOST/chat_sessions_test" \
  -H "Content-Type: application/json" \
  -d @elastic/chat_sessions_mapping.json
```

---

## 8. Consultar Documentos

### Ver primeiros 5 documentos de um índice
```bash
curl -u $ES_USER:$ES_PASS "$ES_HOST/documentos/_search?size=5&pretty"
```

### Buscar por termo
```bash
curl -u $ES_USER:$ES_PASS "$ES_HOST/documentos/_search?pretty" \
  -H "Content-Type: application/json" \
  -d '{
    "query": { "match": { "ato.titulo": "edital" } }
  }'
```

---

## Arquivos nesta pasta

| Arquivo | Propósito |
|---------|-----------|
| `documentos_mapping.json` | Mapping do índice `documentos` (com enriquecimento) |
| `documentos_chunks_mapping.json` | Mapping dos chunks de documentos |
| `artefatos_mapping.json` | Mapping do índice `artefatos` |
| `artefatos_chunks_mapping.json` | Mapping dos chunks de artefatos |
| `chat_sessions_mapping.json` | Mapping das sessões de chat |
| `documentos_ifal_mapping_original.json` | Referência do mapping original (não alterar) |
| `README.md` | Este arquivo |
