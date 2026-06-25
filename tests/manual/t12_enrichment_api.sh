#!/usr/bin/env bash
# T-12 — Validação dos endpoints de enriquecimento via HTTP.
# Requer: servidor local rodando + ES acessível.
#
# Uso:
#   source .venv/bin/activate
#   .venv/bin/uvicorn app.main:app --reload &
#   bash tests/manual/t12_enrichment_api.sh

set -euo pipefail

BASE="http://localhost:8000/api/v1"
TOKEN="77c7fa54-9b2c-44c1-a7e2-aea881a7797e"
ARTEFATO_ID="13e17202-2843-4827-be0d-1e8b62e7d4a9"
DOCUMENTO_ID="ejcC7psBL-x_8ArHVaKJ"

H_AUTH="Authorization: Bearer $TOKEN"
H_JSON="Content-Type: application/json"

ok()  { echo "  ✅  $1"; }
fail(){ echo "  ❌  $1"; }
sep() { echo; echo "─────────────────────────────────────"; echo "$1"; }

check_status() {
  local label=$1 expected=$2 actual=$3
  if [ "$actual" -eq "$expected" ]; then ok "$label — HTTP $actual"
  else fail "$label — esperado $expected, recebeu $actual"; fi
}

# ── 1. Resumo de texto direto (sem ES) ──────────────────────────────────────
sep "1. POST /artefatos/summary/generate  [text]"
CODE=$(curl -s -o /tmp/t12_resp.json -w "%{http_code}" -X POST "$BASE/artefatos/summary/generate" \
  -H "$H_AUTH" -H "$H_JSON" \
  -d '{"text": "O IFAL oferece cursos técnicos e superiores em todo o estado de Alagoas."}')
check_status "summary/generate (text)" 200 "$CODE"
python3 -c "import json; d=json.load(open('/tmp/t12_resp.json')); print('  resumo:', d['data']['resumo'][:120])"

# ── 2. Resumo de artefato real (ES + LLM) ───────────────────────────────────
sep "2. POST /artefatos/summary/generate  [document_id]"
CODE=$(curl -s -o /tmp/t12_resp.json -w "%{http_code}" -X POST "$BASE/artefatos/summary/generate" \
  -H "$H_AUTH" -H "$H_JSON" \
  -d "{\"document_id\": \"$ARTEFATO_ID\"}")
check_status "summary/generate (document_id)" 200 "$CODE"
python3 -c "import json; d=json.load(open('/tmp/t12_resp.json')); print('  resumo:', d['data']['resumo'][:120])"

# ── 3. Entidades de texto direto ─────────────────────────────────────────────
sep "3. POST /artefatos/entities/extract  [text]"
CODE=$(curl -s -o /tmp/t12_resp.json -w "%{http_code}" -X POST "$BASE/artefatos/entities/extract" \
  -H "$H_AUTH" -H "$H_JSON" \
  -d '{"text": "O reitor Sérgio Rocha assinou o edital em Maceió, Alagoas, em 10/06/2026."}')
check_status "entities/extract (text)" 200 "$CODE"
python3 -c "import json; d=json.load(open('/tmp/t12_resp.json')); [print('  ', e) for e in d['data']['entidades'][:4]]"

# ── 4. Keywords de documento real ────────────────────────────────────────────
sep "4. POST /documentos/keywords/extract  [document_id]"
CODE=$(curl -s -o /tmp/t12_resp.json -w "%{http_code}" -X POST "$BASE/documentos/keywords/extract" \
  -H "$H_AUTH" -H "$H_JSON" \
  -d "{\"document_id\": \"$DOCUMENTO_ID\"}")
check_status "keywords/extract (document_id)" 200 "$CODE"
python3 -c "import json; d=json.load(open('/tmp/t12_resp.json')); print('  keywords:', d['data']['keywords'][:8])"

# ── 5. Pipeline completo de artefato ─────────────────────────────────────────
sep "5. POST /artefatos/{id}/enrich  [all operations]"
CODE=$(curl -s -o /tmp/t12_resp.json -w "%{http_code}" -X POST "$BASE/artefatos/$ARTEFATO_ID/enrich" \
  -H "$H_AUTH" -H "$H_JSON" -d '{}')
check_status "enrich completo" 200 "$CODE"
python3 -c "import json; d=json.load(open('/tmp/t12_resp.json')); [print('  ', k, '=', v) for k,v in d['data'].items()]"

# ── 6. Operações selecionadas ─────────────────────────────────────────────────
sep "6. POST /artefatos/{id}/enrich  [summary + entities only]"
CODE=$(curl -s -o /tmp/t12_resp.json -w "%{http_code}" -X POST "$BASE/artefatos/$ARTEFATO_ID/enrich" \
  -H "$H_AUTH" -H "$H_JSON" \
  -d '{"operations": ["summary", "entities"]}')
check_status "enrich selecionado" 200 "$CODE"
python3 -c "import json; d=json.load(open('/tmp/t12_resp.json')); [print('  ', k, '=', v) for k,v in d['data'].items()]"

# ── 7. Status de enriquecimento ───────────────────────────────────────────────
sep "7. GET /artefatos/{id}/enrichment-status"
CODE=$(curl -s -o /tmp/t12_resp.json -w "%{http_code}" \
  "$BASE/artefatos/$ARTEFATO_ID/enrichment-status" -H "$H_AUTH")
check_status "enrichment-status" 200 "$CODE"
python3 -c "import json; d=json.load(open('/tmp/t12_resp.json')); [print('  ', k, '=', v) for k,v in d['data'].items()]"

# ── 8. chunk_size inválido → 422 ─────────────────────────────────────────────
sep "8. POST /artefatos/chunking/generate  [chunk_size inválido]"
CODE=$(curl -s -o /dev/null -w "%{http_code}" -X POST "$BASE/artefatos/chunking/generate" \
  -H "$H_AUTH" -H "$H_JSON" \
  -d "{\"document_id\": \"$ARTEFATO_ID\", \"chunk_size\": 500}")
check_status "chunking (chunk_size < 3000)" 422 "$CODE"

# ── 9. Sem token → 401 ───────────────────────────────────────────────────────
sep "9. POST /artefatos/summary/generate  [sem token]"
CODE=$(curl -s -o /dev/null -w "%{http_code}" -X POST "$BASE/artefatos/summary/generate" \
  -H "$H_JSON" -d '{"text": "teste"}')
check_status "sem token" 401 "$CODE"

echo
echo "═════════════════════════════════════════"
echo "T-12 concluído."
