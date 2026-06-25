#!/usr/bin/env bash
# T-19 — Listagem de entidades e keywords.
# Requer: servidor local rodando + docs enriquecidos no ES.
#
# Uso:
#   bash tests/manual/t19_entities_keywords.sh

set -euo pipefail

BASE="http://localhost:8000/api/v1"
TOKEN="77c7fa54-9b2c-44c1-a7e2-aea881a7797e"
H_AUTH="Authorization: Bearer $TOKEN"

ok()  { echo "  ✅  $1"; }
fail(){ echo "  ❌  $1"; }
sep() { echo; echo "─────────────────────────────────────"; echo "$1"; }
check() { [ "$3" -eq "$2" ] && ok "$1 — HTTP $3" || fail "$1 — esperado $2, recebeu $3"; }

sep "1. Entidades de documentos (todas)"
CODE=$(curl -s -o /tmp/t19_resp.json -w "%{http_code}" \
  "$BASE/documentos/entities" -H "$H_AUTH")
check "entidades documentos" 200 "$CODE"
python3 -c "
import json
d = json.load(open('/tmp/t19_resp.json'))
items = d.get('data', [])
print(f'  total retornado: {len(items)}')
for e in items[:5]:
    print(f'    {e}')
"

sep "2. Entidades de documentos filtradas por tipo ORGANIZACAO"
CODE=$(curl -s -o /tmp/t19_resp.json -w "%{http_code}" \
  "$BASE/documentos/entities?entity_type=ORGANIZACAO" -H "$H_AUTH")
check "entidades por tipo" 200 "$CODE"
python3 -c "import json; d=json.load(open('/tmp/t19_resp.json')); print('  itens:', len(d.get('data', [])))"

sep "3. Entidades de artefatos"
CODE=$(curl -s -o /tmp/t19_resp.json -w "%{http_code}" \
  "$BASE/artefatos/entities" -H "$H_AUTH")
check "entidades artefatos" 200 "$CODE"
python3 -c "import json; d=json.load(open('/tmp/t19_resp.json')); print('  itens:', len(d.get('data', [])))"

sep "4. Keywords de documentos"
CODE=$(curl -s -o /tmp/t19_resp.json -w "%{http_code}" \
  "$BASE/documentos/keywords" -H "$H_AUTH")
check "keywords documentos" 200 "$CODE"
python3 -c "
import json
d = json.load(open('/tmp/t19_resp.json'))
items = d.get('data', [])
print(f'  total: {len(items)}')
for k in items[:8]:
    print(f'    {k}')
"

sep "5. Keywords de artefatos"
CODE=$(curl -s -o /tmp/t19_resp.json -w "%{http_code}" \
  "$BASE/artefatos/keywords" -H "$H_AUTH")
check "keywords artefatos" 200 "$CODE"
python3 -c "import json; d=json.load(open('/tmp/t19_resp.json')); print('  itens:', len(d.get('data', [])))"

sep "6. min_count filtra resultados raros"
CODE=$(curl -s -o /tmp/t19_resp.json -w "%{http_code}" \
  "$BASE/documentos/entities?min_count=5" -H "$H_AUTH")
check "min_count=5" 200 "$CODE"
python3 -c "import json; d=json.load(open('/tmp/t19_resp.json')); print('  itens com count>=5:', len(d.get('data', [])))"

echo
echo "═════════════════════════════════════════"
echo "T-19 concluído."
