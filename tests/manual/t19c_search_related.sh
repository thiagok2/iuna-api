#!/usr/bin/env bash
# T-19c — search_related (RRF multi-sinal).
# Requer: servidor local rodando.
#
# Cenários:
#   1. Artefato com todos os sinais   → enrichment_used: [entities, keywords, embedding]
#   2. Artefato sem enriquecimento    → enrichment_used: [] (MLT puro)
#   3. Documento sem enriquecimento   → enrichment_used: [] (MLT puro)
#   4. ID inexistente                 → 404
#   5. O próprio doc não aparece nos resultados
#
# Nota: documentos_ifal_v2 não possui docs enriquecidos no ambiente de dev.
# O cenário de documento com sinais completos será validado após enriquecimento.

set -euo pipefail

BASE="http://localhost:8000/api/v1"
TOKEN="77c7fa54-9b2c-44c1-a7e2-aea881a7797e"
H_AUTH="Authorization: Bearer $TOKEN"

# IDs reais verificados no ES (2026-06-25)
ARTEFATO_ENRIQUECIDO="13e17202-2843-4827-be0d-1e8b62e7d4a9"   # entities + keywords + embedding
ARTEFATO_SEM_ENRICH="1cdb6c68-9016-4d0a-99ee-d87d7b4099e5"    # sem sinais
DOCUMENTO_SEM_ENRICH="ejcC7psBL-x_8ArHVaKJ"                   # sem sinais (v2 sem enriquecimento)

ok()   { echo "  ✅  $1"; }
fail() { echo "  ❌  $1"; }
sep()  { echo; echo "─────────────────────────────────────"; echo "$1"; }
check(){ [ "$3" -eq "$2" ] && ok "$1 — HTTP $3" || fail "$1 — esperado $2, recebeu $3"; }

# ── Cenário 1 — Artefato com todos os sinais ─────────────────────────────────

sep "1. Artefato enriquecido → enrichment_used com os 3 sinais"
CODE=$(curl -s -o /tmp/t19c_resp.json -w "%{http_code}" \
  "$BASE/artefatos/search/related/$ARTEFATO_ENRIQUECIDO?limit=5" -H "$H_AUTH")
check "artefato enriquecido" 200 "$CODE"
python3 -c "
import json
d = json.load(open('/tmp/t19c_resp.json'))
meta = d.get('meta', {})
eu = set(meta.get('enrichment_used', []))
total = meta.get('total', '?')
ids = [r.get('id') for r in d.get('data', [])[:3]]
print('  enrichment_used:', sorted(eu))
print('  total:', total, '| primeiros ids:', ids)
required = {'entities', 'keywords'}
missing = required - eu
if missing:
    print('  ❌  sinais obrigatórios ausentes:', missing)
else:
    print('  ✅  entities + keywords presentes')
    if 'embedding' in eu:
        print('  ✅  embedding via RRF ativo')
    else:
        print('  ⚠️   embedding ausente (fallback de licença ES — esperado neste ambiente)')
"

# ── Cenário 2 — Artefato sem enriquecimento ──────────────────────────────────

sep "2. Artefato sem enriquecimento → enrichment_used vazio (MLT puro)"
CODE=$(curl -s -o /tmp/t19c_resp.json -w "%{http_code}" \
  "$BASE/artefatos/search/related/$ARTEFATO_SEM_ENRICH?limit=5" -H "$H_AUTH")
check "artefato sem enrich" 200 "$CODE"
python3 -c "
import json
d = json.load(open('/tmp/t19c_resp.json'))
eu = d.get('meta', {}).get('enrichment_used', [])
print('  enrichment_used:', eu)
if eu == []:
    print('  ✅  MLT puro — sem sinais extras (esperado)')
else:
    print('  ❌  esperado [], recebeu:', eu)
"

# ── Cenário 3 — Documento sem enriquecimento ─────────────────────────────────

sep "3. Documento sem enriquecimento → enrichment_used vazio"
CODE=$(curl -s -o /tmp/t19c_resp.json -w "%{http_code}" \
  "$BASE/documentos/search/related/$DOCUMENTO_SEM_ENRICH?limit=5" -H "$H_AUTH")
check "documento sem enrich" 200 "$CODE"
python3 -c "
import json
d = json.load(open('/tmp/t19c_resp.json'))
eu = d.get('meta', {}).get('enrichment_used', [])
total = d.get('meta', {}).get('total', '?')
print('  enrichment_used:', eu, '| total:', total)
if eu == []:
    print('  ✅  MLT puro (esperado — v2 sem enriquecimento no ambiente de dev)')
else:
    print('  ❌  esperado []')
"

# ── Cenário 4 — ID inexistente → 404 ─────────────────────────────────────────

sep "4. ID inexistente → 404"
CODE=$(curl -s -o /dev/null -w "%{http_code}" \
  "$BASE/documentos/search/related/ID-QUE-NAO-EXISTE" -H "$H_AUTH")
check "doc 404" 404 "$CODE"

CODE=$(curl -s -o /dev/null -w "%{http_code}" \
  "$BASE/artefatos/search/related/ID-QUE-NAO-EXISTE" -H "$H_AUTH")
check "artefato 404" 404 "$CODE"

# ── Cenário 5 — O próprio doc não aparece nos resultados ─────────────────────

sep "5. O próprio artefato enriquecido não aparece nos resultados"
curl -s -o /tmp/t19c_resp.json \
  "$BASE/artefatos/search/related/$ARTEFATO_ENRIQUECIDO?limit=10" -H "$H_AUTH"
python3 -c "
import json
d = json.load(open('/tmp/t19c_resp.json'))
ref_id = '$ARTEFATO_ENRIQUECIDO'
ids = [r.get('id') for r in d.get('data', [])]
if ref_id in ids:
    print('  ❌  o próprio doc apareceu nos resultados:', ref_id)
else:
    print('  ✅  o próprio doc NÃO aparece nos resultados')
print('  ids retornados:', ids)
"

echo
echo "═════════════════════════════════════════"
echo "T-19c concluído."
