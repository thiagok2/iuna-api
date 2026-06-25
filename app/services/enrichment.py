"""
EnrichmentService — gera resumo, embedding, entidades, keywords e chunks.

Recebe (index, doc_id, root) para operar em qualquer tipo de documento:
- documentos_ifal_v2 → root="ato"
- artefatos          → root="artefato"
"""

import logging
from datetime import datetime, timezone

from app.clients.es_client import ESClient
from app.core.exceptions import NotFoundError, ServiceUnavailableError, ValidationError
from app.providers.base import BaseLLMProvider

logger = logging.getLogger(__name__)

_CHUNK_THRESHOLD = 10_000


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


class EnrichmentService:
    def __init__(self, es_client: ESClient, llm_provider: BaseLLMProvider):
        self.es = es_client
        self.llm = llm_provider

    async def enrich_summary(self, index: str, doc_id: str, root: str) -> str:
        """Gera resumo e grava em {root}.resumo + {root}.resumo_at."""
        doc = await self._get_doc(index, doc_id)
        content = self._get_content(doc)

        summary = await self.llm.generate_summary(content)

        await self._update(index, doc_id, root, {"resumo": summary, "resumo_at": _now()})
        return summary

    async def enrich_vector(self, index: str, doc_id: str, root: str) -> list[float]:
        """Gera embedding a partir do resumo. Se resumo não existe, gera primeiro."""
        doc = await self._get_doc(index, doc_id)
        resumo = doc["_source"].get(root, {}).get("resumo")

        if not resumo:
            resumo = await self.enrich_summary(index, doc_id, root)

        vector = await self.llm.generate_embedding(resumo)

        await self._update(index, doc_id, root, {"embedding_vector": vector, "embedding_vector_at": _now()})
        return vector

    async def enrich_entities(self, index: str, doc_id: str, root: str) -> list[dict]:
        """Extrai entidades do conteúdo e grava em {root}.entidades."""
        doc = await self._get_doc(index, doc_id)
        content = self._get_content(doc)

        entities = await self.llm.extract_entities(content)

        await self._update(index, doc_id, root, {"entidades": entities, "entidades_at": _now()})
        return entities

    async def enrich_keywords(self, index: str, doc_id: str, root: str) -> list[str]:
        """Extrai keywords e grava em {root}.keywords."""
        doc = await self._get_doc(index, doc_id)
        content = self._get_content(doc)

        keywords = await self.llm.extract_keywords(content)

        await self._update(index, doc_id, root, {"keywords": keywords, "keywords_at": _now()})
        return keywords

    async def enrich_chunks(
        self,
        index: str,
        chunks_index: str,
        doc_id: str,
        root: str,
        chunk_size: int = 3000,
        overlap: int = 500,
    ) -> int:
        """
        Segmenta em chunks se conteúdo >= 10.000 chars.
        Vetoriza cada chunk e indexa no chunks_index.
        Retorna 0 se documento pequeno demais (não foi segmentado).
        """
        if chunk_size < 3000:
            raise ValidationError("chunk_size mínimo é 3000")

        doc = await self._get_doc(index, doc_id)
        content = self._get_content(doc)
        filename = doc["_source"].get("filename", "")

        if len(content) < _CHUNK_THRESHOLD:
            return 0

        # Deleta chunks anteriores
        await self.es.delete_by_query(
            index=chunks_index,
            body={"query": {"term": {"parent_document_id": doc_id}}},
        )

        chunks = self._split_text(content, chunk_size, overlap)

        actions = []
        for i, chunk_content in enumerate(chunks):
            vector = await self.llm.generate_embedding(chunk_content)
            actions.append({
                "parent_document_id": doc_id,
                "parent_filename": filename,
                "chunk_index": i,
                "content": chunk_content,
                "total_chunks": len(chunks),
                "chunk_size": len(chunk_content),
                "embedding_vector": vector,
                "created_at": _now(),
            })

        await self.es.bulk_index(index=chunks_index, documents=actions)

        await self._update(index, doc_id, root, {
            "chunking_at": _now(),
            "total_chunks": len(chunks),
        })
        return len(chunks)

    async def enrich_all(
        self, index: str, chunks_index: str, doc_id: str, root: str
    ) -> dict:
        """Executa todo o enriquecimento na ordem: entidades → keywords → resumo → vetorização → chunking."""
        entities = await self.enrich_entities(index, doc_id, root)
        keywords = await self.enrich_keywords(index, doc_id, root)
        summary = await self.enrich_summary(index, doc_id, root)
        vector = await self.enrich_vector(index, doc_id, root)
        total_chunks = await self.enrich_chunks(index, chunks_index, doc_id, root)

        return {
            "entities_count": len(entities),
            "keywords_count": len(keywords),
            "summary_length": len(summary),
            "vector_dims": len(vector),
            "total_chunks": total_chunks,
        }

    async def get_enrichment_status(self, index: str, doc_id: str, root: str) -> dict:
        """Retorna status de cada operação de enriquecimento."""
        doc = await self._get_doc(index, doc_id)
        src = doc["_source"].get(root, {})
        return {
            "resumo_at": src.get("resumo_at"),
            "entidades_at": src.get("entidades_at"),
            "keywords_at": src.get("keywords_at"),
            "embedding_vector_at": src.get("embedding_vector_at"),
            "chunking_at": src.get("chunking_at"),
            "total_chunks": src.get("total_chunks", 0),
        }

    # ------------------------------------------------------------------
    # Helpers internos
    # ------------------------------------------------------------------

    async def _get_doc(self, index: str, doc_id: str) -> dict:
        try:
            return await self.es.get(index=index, id=doc_id)
        except NotFoundError:
            raise
        except Exception as exc:
            raise ServiceUnavailableError(f"Elasticsearch indisponível: {exc}")

    async def _update(self, index: str, doc_id: str, root: str, fields: dict) -> None:
        try:
            await self.es.update(index=index, id=doc_id, body={root: fields})
        except Exception as exc:
            raise ServiceUnavailableError(f"Elasticsearch indisponível: {exc}")

    @staticmethod
    def _get_content(doc: dict) -> str:
        content = doc.get("_source", {}).get("attachment", {}).get("content", "")
        if not content:
            raise ValidationError("Documento não possui conteúdo extraído (attachment.content vazio)")
        return content

    @staticmethod
    def _split_text(text: str, chunk_size: int, overlap: int) -> list[str]:
        step = max(chunk_size - overlap, chunk_size // 2)
        chunks = []
        start = 0
        while start < len(text):
            chunks.append(text[start : start + chunk_size])
            start += step
        return chunks
