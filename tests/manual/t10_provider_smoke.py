"""
T-10 — Smoke test do LLM provider ativo.
Requer: GEMINI_API_KEY (ou CLAUDE_API_KEY) configurado no .env.

Uso:
    source .venv/bin/activate
    python tests/manual/t10_provider_smoke.py
"""

import asyncio
from app.providers.factory import get_llm_provider

TEXT = (
    "O Instituto Federal de Alagoas foi criado pela Lei 11.892/2008 "
    "e oferece cursos técnicos e superiores em todo o estado de Alagoas, "
    "com campi em Maceió, Palmeira dos Índios, Penedo, Piranhas, Satuba, "
    "Marechal Deodoro, São Miguel dos Campos e outros municípios."
)


async def main() -> None:
    llm = get_llm_provider()
    print(f"Provider ativo: {type(llm).__name__}\n")

    print("→ generate_summary")
    summary = await llm.generate_summary(TEXT)
    print(f"  {summary[:300]}\n")

    print("→ extract_entities")
    entities = await llm.extract_entities(TEXT)
    for e in entities[:5]:
        print(f"  {e}")
    print()

    print("→ extract_keywords")
    keywords = await llm.extract_keywords(TEXT)
    print(f"  {keywords}\n")

    print("→ generate_embedding")
    try:
        vector = await llm.generate_embedding(TEXT[:500])
        print(f"  dims={len(vector)}, primeiros valores={vector[:3]}\n")
    except Exception as exc:
        print(f"  ERRO: {exc}\n")

    print("→ health_check")
    ok = await llm.health_check()
    print(f"  {'OK' if ok else 'FALHOU'}\n")


if __name__ == "__main__":
    asyncio.run(main())
