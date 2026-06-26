#!/usr/bin/env bash
# T-18 — Scoring de popularidade.
# Requer: servidor local rodando + docs enriquecidos no ES.
#
# Uso:
#   bash tests/manual/t18_scoring.sh

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
check() { [ "$3" -eq "$2" ] && ok "$1 — HTTP $3" || fail "$1 — esperado $2, recebeu $3"; }

sep "1. Score click em documento"
CODE=$(curl -s -o /tmp/t18_resp.json -w "%{http_code}" -X POST \
  "$BASE/documentos/$DOCUMENTO_ID/score" \
  -H "$H_AUTH" -H "$H_JSON" -d '{"action": "click"}')
check "score click" 200 "$CODE"
python3 -c "import json; d=json.load(open('/tmp/t18_resp.json')); print('  novo score:', d.get('data', {}).get('popularity_score', d))"

sep "2. Score download em documento (peso maior que click)"
CODE=$(curl -s -o /tmp/t18_resp.json -w "%{http_code}" -X POST \
  "$BASE/documentos/$DOCUMENTO_ID/score" \
  -H "$H_AUTH" -H "$H_JSON" -d '{"action": "download"}')
check "score download" 200 "$CODE"
python3 -c "import json; d=json.load(open('/tmp/t18_resp.json')); print('  novo score:', d.get('data', {}).get('popularity_score', d))"

sep "3. Score add_to_chat em artefato"
CODE=$(curl -s -o /tmp/t18_resp.json -w "%{http_code}" -X POST \
  "$BASE/artefatos/$ARTEFATO_ID/score" \
  -H "$H_AUTH" -H "$H_JSON" -d '{"action": "add_to_chat"}')
check "score add_to_chat artefato" 200 "$CODE"

sep "4. Ação inválida → 422"
CODE=$(curl -s -o /dev/null -w "%{http_code}" -X POST \
  "$BASE/documentos/$DOCUMENTO_ID/score" \
  -H "$H_AUTH" -H "$H_JSON" -d '{"action": "acao-invalida"}')
check "ação inválida" 422 "$CODE"

sep "5. Verificar popularity_score no ES após incrementos"
curl -s -H "Authorization: Basic ZWxhc3RpYzpTWFR0NHJrMDV1RHE=" \
  "https://elastic.pnld-avaliacao-dev.nees.ufal.br/documentos_ifal_v2/_doc/$DOCUMENTO_ID?pretty" \
  | python3 -c "
import sys, json
d = json.load(sys.stdin)
score = d['_source'].get('ato', {}).get('popularity_score', 'campo não encontrado')
print(f'  popularity_score no ES: {score}')
"

sep "6. Score influencia ranking — buscar antes e depois de 3 clicks"
echo "  Busca ANTES dos clicks:"
curl -s "$BASE/documentos/search/?q=edital&page_size=5" -H "$H_AUTH" \
  | python3 -c "import json,sys; d=json.load(sys.stdin); [print(f'    {i+1}. {h.get(\"_id\",h.get(\"id\"))} score={h.get(\"_score\")}') for i,h in enumerate((d.get('hits') or d.get('results', []))[:3])]"

for _ in 1 2 3; do
  curl -s -o /dev/null -X POST "$BASE/documentos/$DOCUMENTO_ID/score" \
    -H "$H_AUTH" -H "$H_JSON" -d '{"action": "click"}'
done

echo "  Busca DEPOIS dos 3 clicks:"
curl -s "$BASE/documentos/search/?q=edital&page_size=5" -H "$H_AUTH" \
  | python3 -c "import json,sys; d=json.load(sys.stdin); [print(f'    {i+1}. {h.get(\"_id\",h.get(\"id\"))} score={h.get(\"_score\")}') for i,h in enumerate((d.get('hits') or d.get('results', []))[:3])]"
echo "  Esperado: $DOCUMENTO_ID subiu no ranking"

echo
echo "═════════════════════════════════════════"
echo "T-18 concluído."
