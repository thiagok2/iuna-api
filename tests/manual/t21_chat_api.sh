#!/usr/bin/env bash
# T-21: Validação do ChatService + Router
# Pré-requisito: API rodando em localhost:8000 com ES conectado
# Uso: bash tests/manual/t21_chat_api.sh

set -euo pipefail

BASE="http://localhost:8000/api/v1"
TOKEN="77c7fa54-9b2c-44c1-a7e2-aea881a7797e"
AUTH="-H 'Authorization: Bearer $TOKEN'"
CT="-H 'Content-Type: application/json'"
DOC_ID="TjcA7psBL-x_8ArHDqI6"
SESSION="test-session-001"
SESSION_CHITCHAT="test-session-002"

echo "============================================================"
echo "T-21 — Chat RAG: validação dos endpoints"
echo "============================================================"
echo ""

echo "--- [1/7] Mensagem sem contexto (busca livre nos chunks) ---"
curl -s -X POST \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d "{\"message\": \"o que é um edital?\", \"session_id\": \"$SESSION\"}" \
  "$BASE/chat/message" | python3 -m json.tool
echo ""

echo "--- [2/7] Adicionar documento ao contexto (Manual de Auditoria) ---"
curl -s -X POST \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d "{\"document_id\": \"$DOC_ID\"}" \
  "$BASE/chat/sessions/$SESSION/add-documento" | python3 -m json.tool
echo ""

echo "--- [3/7] Mensagem com contexto (deve usar chunks do doc) ---"
curl -s -X POST \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d "{\"message\": \"quais são as responsabilidades do auditor?\", \"session_id\": \"$SESSION\"}" \
  "$BASE/chat/message" | python3 -m json.tool
echo ""

echo "--- [4/7] Limpar contexto ---"
curl -s -X DELETE \
  -H "Authorization: Bearer $TOKEN" \
  "$BASE/chat/sessions/$SESSION/context" | python3 -m json.tool
echo ""

echo "--- [5/7] Chitchat (intent chitchat, context_used: false) ---"
curl -s -X POST \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d "{\"message\": \"bom dia, tudo bem?\", \"session_id\": \"$SESSION_CHITCHAT\"}" \
  "$BASE/chat/message" | python3 -m json.tool
echo ""

echo "--- [6/7] add-documento com ID inexistente → espera 404 ---"
HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" \
  -X POST \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"document_id": "id-fantasma"}' \
  "$BASE/chat/sessions/$SESSION/add-documento")
echo "HTTP status: $HTTP_CODE (esperado: 404)"
echo ""

echo "--- [7/7] Obter sessão (inclui context_document_ids, expires_at) ---"
curl -s \
  -H "Authorization: Bearer $TOKEN" \
  "$BASE/chat/sessions/$SESSION" | python3 -m json.tool
echo ""

echo "============================================================"
echo "Validação concluída."
echo "============================================================"
