"""
T-11 — Validação do EnrichmentService contra ES real.
Requer: ES acessível + GEMINI_API_KEY no .env.

Uso:
    source .venv/bin/activate
    python tests/manual/t11_enrichment_service.py
"""

import asyncio
import json
import subprocess
from app.clients.es_client import es_client
from app.providers.factory import get_llm_provider
from app.services.enrichment import EnrichmentService

ARTEFATO_ID = "13e17202-2843-4827-be0d-1e8b62e7d4a9"
ARTEFATO_INDEX = "artefatos"
ARTEFATO_ROOT = "artefato"

ES_AUTH = "ZWxhc3RpYzpTWFR0NHJrMDV1RHE="
ES_HOST = "https://elastic.pnld-avaliacao-dev.nees.ufal.br"


def _check_es(doc_id: str) -> dict:
    result = subprocess.run(
        ["curl", "-s", "-H", f"Authorization: Basic {ES_AUTH}",
         f"{ES_HOST}/{ARTEFATO_INDEX}/{doc_id}?pretty"],
        capture_output=True, text=True,
    )
    doc = json.loads(result.stdout)
    return doc.get("_source", {}).get(ARTEFATO_ROOT, {})


async def main() -> None:
    print(f"Documento: {ARTEFATO_ID}\n")

    await es_client.connect()
    svc = EnrichmentService(es_client, get_llm_provider())

    print("→ enrich_summary")
    summary = await svc.enrich_summary(ARTEFATO_INDEX, ARTEFATO_ID, ARTEFATO_ROOT)
    print(f"  {summary[:200]}\n")

    print("→ enrich_entities")
    entities = await svc.enrich_entities(ARTEFATO_INDEX, ARTEFATO_ID, ARTEFATO_ROOT)
    for e in entities[:5]:
        print(f"  {e}")
    print()

    print("→ enrich_keywords")
    keywords = await svc.enrich_keywords(ARTEFATO_INDEX, ARTEFATO_ID, ARTEFATO_ROOT)
    print(f"  {keywords}\n")

    print("→ enrich_vector (usa resumo gerado acima)")
    vector = await svc.enrich_vector(ARTEFATO_INDEX, ARTEFATO_ID, ARTEFATO_ROOT)
    print(f"  dims={len(vector)}, primeiros valores={vector[:3]}\n")

    print("→ enrich_chunks")
    n = await svc.enrich_chunks(ARTEFATO_INDEX, f"{ARTEFATO_INDEX}_chunks", ARTEFATO_ID, ARTEFATO_ROOT)
    if n == 0:
        print("  doc < 10.000 chars — chunking ignorado\n")
    else:
        print(f"  {n} chunks criados\n")

    await es_client.close()

    print("─" * 50)
    print("Verificando campos gravados no ES...")
    artefato = _check_es(ARTEFATO_ID)
    print(f"  resumo_at:         {artefato.get('resumo_at')}")
    print(f"  entidades:         {len(artefato.get('entidades', []))} itens")
    print(f"  keywords:          {len(artefato.get('keywords', []))} itens")
    print(f"  embedding_vector:  {len(artefato.get('embedding_vector') or [])} dims")
    print(f"  total_chunks:      {artefato.get('total_chunks', 0)}")


if __name__ == "__main__":
    asyncio.run(main())
