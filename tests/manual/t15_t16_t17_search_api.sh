#!/usr/bin/env bash
# T-15, T-16, T-17 — Busca full-text, similar, por entidade/keyword, chunks.
# Requer: servidor local rodando + docs enriquecidos no ES.
#
# Uso:
#   source .venv/bin/activate
#   .venv/bin/uvicorn app.main:app --reload &
#   bash tests/manual/t15_t16_t17_search_api.sh

set -euo pipefail

BASE="http://localhost:8000/api/v1"
TOKEN="77c7fa54-9b2c-44c1-a7e2-aea881a7797e"
ARTEFATO_ID="13e17202-2843-4827-be0d-1e8b62e7d4a9"
DOCUMENTO_ID="ejcC7psBL-x_8ArHVaKJ"
H_AUTH="Authorization: Bearer $TOKEN"

ok()  { echo "  ✅  $1"; }
fail(){ echo "  ❌  $1"; }
sep() { echo; echo "─────────────────────────────────────"; echo "$1"; }

check() {
  local label=$1 expected=$2 actual=$3
  [ "$actual" -eq "$expected" ] && ok "$label — HTTP $actual" || fail "$label — esperado $expected, recebeu $actual"
}

# ── T-15: Documentos ─────────────────────────────────────────────────────────

sep "T-15.1 — Busca full-text em documentos"
CODE=$(curl -s -o /tmp/s_resp.json -w "%{http_code}" \
  "$BASE/documentos/search/?q=edital&page_size=5" -H "$H_AUTH")
check "search fulltext" 200 "$CODE"
python3 -c "import json; d=json.load(open('/tmp/s_resp.json')); print('  total:', d.get('total', d.get('hits',{}).get('total',{}).get('value','?')), '| primeiros:', [h.get('_id',h.get('id')) for h in (d.get('hits') or d.get('results', []))[:2]])"

sep "T-15.2 — Busca com filtros (tipo_doc + ano)"
CODE=$(curl -s -o /tmp/s_resp.json -w "%{http_code}" \
  "$BASE/documentos/search/?q=edital&tipo_doc=edital&ano=2022" -H "$H_AUTH")
check "search com filtros" 200 "$CODE"

sep "T-15.3 — Facets"
CODE=$(curl -s -o /tmp/s_resp.json -w "%{http_code}" \
  "$BASE/documentos/search/facets?q=edital" -H "$H_AUTH")
check "search facets" 200 "$CODE"
python3 -c "import json; d=json.load(open('/tmp/s_resp.json')); print('  agregações:', list((d.get('data') or d.get('aggregations', {})).keys())[:5])"

sep "T-15.4 — Similar"
CODE=$(curl -s -o /tmp/s_resp.json -w "%{http_code}" \
  "$BASE/documentos/search/similar/$DOCUMENTO_ID" -H "$H_AUTH")
check "search similar" 200 "$CODE"

sep "T-15.5 — Por entidade"
CODE=$(curl -s -o /tmp/s_resp.json -w "%{http_code}" \
  "$BASE/documentos/search/by-entity?entity=IFAL" -H "$H_AUTH")
check "search by-entity" 200 "$CODE"

sep "T-15.6 — Por keyword"
CODE=$(curl -s -o /tmp/s_resp.json -w "%{http_code}" \
  "$BASE/documentos/search/by-keyword?keyword=edital" -H "$H_AUTH")
check "search by-keyword" 200 "$CODE"

sep "T-15.7 — Autocomplete"
CODE=$(curl -s -o /tmp/s_resp.json -w "%{http_code}" \
  "$BASE/documentos/search/suggest?q=edi" -H "$H_AUTH")
check "suggest" 200 "$CODE"
python3 -c "import json; d=json.load(open('/tmp/s_resp.json')); print('  sugestões:', (d.get('data') or [])[:5])"

# ── T-16: Artefatos ──────────────────────────────────────────────────────────

sep "T-16.1 — Busca full-text em artefatos"
CODE=$(curl -s -o /tmp/s_resp.json -w "%{http_code}" \
  "$BASE/artefatos/search/?q=edital&page_size=5" -H "$H_AUTH")
check "artefatos search fulltext" 200 "$CODE"

sep "T-16.2 — Similar em artefatos"
CODE=$(curl -s -o /tmp/s_resp.json -w "%{http_code}" \
  "$BASE/artefatos/search/similar/$ARTEFATO_ID" -H "$H_AUTH")
check "artefatos search similar" 200 "$CODE"

sep "T-16.3 — Por entidade em artefatos"
CODE=$(curl -s -o /tmp/s_resp.json -w "%{http_code}" \
  "$BASE/artefatos/search/by-entity?entity=IFAL" -H "$H_AUTH")
check "artefatos by-entity" 200 "$CODE"

# ── T-17: Chunks ─────────────────────────────────────────────────────────────

sep "T-17.1 — Busca em chunks de documentos"
CODE=$(curl -s -o /tmp/s_resp.json -w "%{http_code}" \
  "$BASE/documentos/search/chunks?q=prazo+de+inscri%C3%A7%C3%A3o" -H "$H_AUTH")
check "chunks search" 200 "$CODE"
python3 -c "import json; d=json.load(open('/tmp/s_resp.json')); hits=d.get('hits',d.get('results',[])); print('  chunks encontrados:', len(hits) if isinstance(hits,list) else hits)"

sep "T-17.2 — Chunks filtrado por document_id"
CODE=$(curl -s -o /tmp/s_resp.json -w "%{http_code}" \
  "$BASE/documentos/search/chunks?q=edital&document_id=$DOCUMENTO_ID" -H "$H_AUTH")
check "chunks filtrado" 200 "$CODE"

echo
echo "═════════════════════════════════════════"
echo "T-15, T-16, T-17 concluídos."
