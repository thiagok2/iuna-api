#!/usr/bin/env bash
# T-13 — Validação do comando CLI `iuna enrich`.
# Requer: ES acessível + GEMINI_API_KEY no .env.
#
# Uso:
#   source .venv/bin/activate
#   bash tests/manual/t13_cli_enrich.sh

set -uo pipefail

ARTEFATO_ID="13e17202-2843-4827-be0d-1e8b62e7d4a9"
ARTEFATO_ID2="5bd3851a-0e55-45cc-9b05-9bfe7a69a1fe"
ES_AUTH="ZWxhc3RpYzpTWFR0NHJrMDV1RHE="
ES_HOST="https://elastic.pnld-avaliacao-dev.nees.ufal.br"
CLI="python -m app.cli.main"

sep() { echo; echo "─────────────────────────────────────"; echo "$1"; }

# ── 1. Apenas resumo ─────────────────────────────────────────────────────────
sep "1. enrich --summarize"
$CLI enrich --source-type artefatos --ids "$ARTEFATO_ID" --summarize
# Esperado: ✅ [1/1] 13e17202-...

# ── 2. Apenas entidades + keywords ───────────────────────────────────────────
sep "2. enrich --entities --keywords"
$CLI enrich --source-type artefatos --ids "$ARTEFATO_ID" --entities --keywords
# Esperado: ✅ [1/1] 13e17202-...

# ── 3. Pipeline completo ──────────────────────────────────────────────────────
sep "3. enrich --enrich (todas as operações)"
$CLI enrich --source-type artefatos --ids "$ARTEFATO_ID" --enrich
# Esperado: ✅ [1/1] 13e17202-...

# ── 4. Dois docs, concorrência 1 (sequencial) ────────────────────────────────
sep "4. dois docs, --concurrency 1"
$CLI enrich --source-type artefatos \
  --ids "$ARTEFATO_ID,$ARTEFATO_ID2" --summarize --concurrency 1
# Esperado: [1/2] ... [2/2] ... (sequencialmente)

# ── 5. --skip-existing (pula já enriquecidos) ────────────────────────────────
sep "5. --skip-existing"
$CLI enrich --source-type artefatos --ids "$ARTEFATO_ID" --enrich --skip-existing
# Esperado: ⏭ [1/1] 13e17202-... — já enriquecido, pulando

# ── 6. --force (re-enriquece mesmo que exista) ───────────────────────────────
sep "6. --force"
$CLI enrich --source-type artefatos --ids "$ARTEFATO_ID" --summarize --force
# Esperado: ✅ [1/1] 13e17202-... (sobrescreve)

# ── 7. Verificar campos gravados no ES ───────────────────────────────────────
sep "7. Verificar resultado no ES"
curl -s -H "Authorization: Basic $ES_AUTH" \
  "$ES_HOST/artefatos/_doc/$ARTEFATO_ID?pretty" \
  | python3 -c "
import sys, json
d = json.load(sys.stdin)
a = d['_source']['artefato']
print('  resumo_at:        ', a.get('resumo_at'))
print('  entidades:        ', len(a.get('entidades', [])), 'itens')
print('  keywords:         ', len(a.get('keywords', [])), 'itens')
print('  embedding_vector: ', len(a.get('embedding_vector') or []), 'dims')
print('  total_chunks:     ', a.get('total_chunks', 0))
"

# ── 8. Verificar chunks criados ──────────────────────────────────────────────
sep "8. Verificar chunks no índice artefatos_chunks"
curl -s -H "Authorization: Basic $ES_AUTH" \
  -H "Content-Type: application/json" \
  -d "{\"query\": {\"term\": {\"parent_document_id\": \"$ARTEFATO_ID\"}}, \"size\": 3}" \
  "$ES_HOST/artefatos_chunks/_search?pretty" \
  | python3 -c "
import sys, json
d = json.load(sys.stdin)
hits = d['hits']['hits']
print(f'  chunks encontrados: {len(hits)}')
for h in hits:
    s = h['_source']
    print(f'    chunk {s[\"chunk_index\"]}: {len(s[\"content\"])} chars, {len(s.get(\"embedding_vector\") or [])} dims')
"

echo
echo "═════════════════════════════════════════"
echo "T-13 concluído."
