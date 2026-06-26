#!/usr/bin/env bash
# T-19b — Busca legado (documentos_ifal).
# Requer: servidor local rodando.
#
# Uso:
#   bash tests/manual/t19b_busca_legado.sh

set -euo pipefail

BASE="http://localhost:8000/api/v1"
TOKEN="77c7fa54-9b2c-44c1-a7e2-aea881a7797e"
DOCUMENTO_ID="ejcC7psBL-x_8ArHVaKJ"
H_AUTH="Authorization: Bearer $TOKEN"

ok()   { echo "  ✅  $1"; }
fail() { echo "  ❌  $1"; }
sep()  { echo; echo "─────────────────────────────────────"; echo "$1"; }
check(){ [ "$3" -eq "$2" ] && ok "$1 — HTTP $3" || fail "$1 — esperado $2, recebeu $3"; }

# ── T-19b.1 — Busca full-text ─────────────────────────────────────────────────

sep "T-19b.1 — Busca full-text no legado"
CODE=$(curl -s -o /tmp/t19b_resp.json -w "%{http_code}" \
  "$BASE/legado/documentos/search?q=edital&page_size=5" -H "$H_AUTH")
check "legado search fulltext" 200 "$CODE"
python3 -c "
import json
d = json.load(open('/tmp/t19b_resp.json'))
total = (d.get('meta') or {}).get('total', '?')
ids = [h.get('id', h.get('_id')) for h in (d.get('data') or [])[:2]]
print('  total:', total, '| primeiros:', ids)
"

# ── T-19b.2 — Busca com exact_phrase ─────────────────────────────────────────

sep "T-19b.2 — Busca exact_phrase"
CODE=$(curl -s -o /tmp/t19b_resp.json -w "%{http_code}" \
  "$BASE/legado/documentos/search?q=processo+seletivo&exact_phrase=true&page_size=3" -H "$H_AUTH")
check "legado exact_phrase" 200 "$CODE"
python3 -c "
import json
d = json.load(open('/tmp/t19b_resp.json'))
total = (d.get('meta') or {}).get('total', '?')
print('  total exact_phrase:', total)
"

# ── T-19b.3 — Busca com with_aggregations ────────────────────────────────────

sep "T-19b.3 — Busca com aggregations"
CODE=$(curl -s -o /tmp/t19b_resp.json -w "%{http_code}" \
  "$BASE/legado/documentos/search?q=edital&with_aggregations=true&page_size=3" -H "$H_AUTH")
check "legado with_aggregations" 200 "$CODE"
python3 -c "
import json
d = json.load(open('/tmp/t19b_resp.json'))
facets = list((d.get('facets') or {}).keys())
print('  facets:', facets)
"

# ── T-19b.4 — Busca com filtros ──────────────────────────────────────────────

sep "T-19b.4 — Busca com filtros (tipo_doc + ano)"
CODE=$(curl -s -o /tmp/t19b_resp.json -w "%{http_code}" \
  "$BASE/legado/documentos/search?q=edital&tipo_doc=edital&ano=2022" -H "$H_AUTH")
check "legado search com filtros" 200 "$CODE"
python3 -c "
import json
d = json.load(open('/tmp/t19b_resp.json'))
total = (d.get('meta') or {}).get('total', '?')
print('  total filtrado:', total)
"

# ── T-19b.5 — Get por ID ─────────────────────────────────────────────────────

sep "T-19b.5 — GET /legado/documentos/{id}"
CODE=$(curl -s -o /tmp/t19b_resp.json -w "%{http_code}" \
  "$BASE/legado/documentos/$DOCUMENTO_ID" -H "$H_AUTH")
check "legado get by id" 200 "$CODE"
python3 -c "
import json
d = json.load(open('/tmp/t19b_resp.json'))
doc = d.get('data') or {}
titulo = (doc.get('ato') or {}).get('titulo', doc.get('id', '?'))
print('  titulo:', titulo[:80])
"

# ── T-19b.6 — Similar ────────────────────────────────────────────────────────

sep "T-19b.6 — GET /legado/documentos/{id}/similar"
CODE=$(curl -s -o /tmp/t19b_resp.json -w "%{http_code}" \
  "$BASE/legado/documentos/$DOCUMENTO_ID/similar?page_size=4" -H "$H_AUTH")
check "legado similar" 200 "$CODE"
python3 -c "
import json
d = json.load(open('/tmp/t19b_resp.json'))
total = (d.get('meta') or {}).get('total', '?')
ids = [h.get('id', h.get('_id')) for h in (d.get('data') or [])[:3]]
print('  similares:', total, '| primeiros:', ids)
"

# ── T-19b.7 — ID inexistente → 404 ───────────────────────────────────────────

sep "T-19b.7 — ID inexistente → 404"
CODE=$(curl -s -o /dev/null -w "%{http_code}" \
  "$BASE/legado/documentos/ID-QUE-NAO-EXISTE" -H "$H_AUTH")
check "legado 404" 404 "$CODE"

echo
echo "═════════════════════════════════════════"
echo "T-19b concluído."
