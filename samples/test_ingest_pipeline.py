"""
Testa a indexação de um PDF via ES Ingest Attachment Pipeline.

Pré-requisitos:
  1. ES online
  2. Pipeline criado (ver elastic/setup/20260622_ingest_pipeline.md)
  3. Índice artefatos criado

Uso:
  source .venv/bin/activate
  python samples/test_ingest_pipeline.py samples/edital_selecao.pdf
"""

import asyncio
import base64
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.clients.es_client import es_client
from app.config import settings


async def test_pipeline(pdf_path: str):
    await es_client.connect()

    # 1. Verificar conexão
    if not await es_client.ping():
        print("❌ ES não acessível")
        return

    # 2. Ler PDF e codificar em base64
    with open(pdf_path, "rb") as f:
        pdf_bytes = f.read()

    pdf_base64 = base64.b64encode(pdf_bytes).decode("utf-8")
    filename = os.path.basename(pdf_path)

    print(f"📄 Arquivo: {filename} ({len(pdf_bytes)} bytes)")
    print(f"📦 Base64: {len(pdf_base64)} chars")

    # 3. Indexar com pipeline
    body = {
        "data": pdf_base64,
        "filename": filename,
        "artefato": {
            "artefato_id": f"test-{filename}",
            "titulo": f"Teste: {filename}",
            "tipo": "teste",
            "uploaded_by": "test_script",
        },
    }

    try:
        result = await es_client.index_with_pipeline(
            index=settings.index_artefatos,
            body=body,
            pipeline=settings.ES_INGEST_PIPELINE,
            id=f"test-{filename}",
        )
        doc_id = result.get("_id", "?")
        print(f"✅ Indexado com sucesso! _id: {doc_id}")
    except Exception as e:
        print(f"❌ Erro ao indexar: {e}")
        await es_client.close()
        return

    # 4. Buscar o documento para verificar que attachment.content foi preenchido
    import asyncio
    await asyncio.sleep(1)  # esperar indexação

    try:
        doc = await es_client.get(index=settings.index_artefatos, id=f"test-{filename}")
        source = doc.get("_source", {})
        content = source.get("attachment", {}).get("content", "")
        has_data = "data" in source

        print(f"\n--- Resultado ---")
        print(f"attachment.content: {len(content)} chars")
        print(f"Campo 'data' removido: {'✅ Sim' if not has_data else '❌ Não (pipeline falhou?)'}")
        print(f"Primeiros 300 chars do texto extraído:")
        print(f"---")
        print(content[:300] if content else "(vazio)")
        print(f"---")
    except Exception as e:
        print(f"❌ Erro ao buscar doc: {e}")

    await es_client.close()


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Uso: python samples/test_ingest_pipeline.py <caminho_do_pdf>")
        print("Ex:  python samples/test_ingest_pipeline.py samples/edital_selecao.pdf")
        sys.exit(1)

    asyncio.run(test_pipeline(sys.argv[1]))
