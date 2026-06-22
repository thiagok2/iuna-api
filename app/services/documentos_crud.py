"""
Service layer for CRUD operations on institutional documents (documentos_ifal_v2).
"""

import base64
import logging
import uuid
from datetime import datetime, timezone

from app.clients.es_client import ESClient
from app.config import settings
from app.core.exceptions import ConflictError, NotFoundError, ServiceUnavailableError, ValidationError

logger = logging.getLogger(__name__)


class DocumentosCrudService:
    """Handles CRUD operations for documentos_ifal_v2 index."""

    def __init__(self, es_client: ESClient):
        self.es = es_client
        self.index = settings.index_documentos_ifal_v2
        self.chunks_index = settings.index_documentos_ifal_v2_chunks

    async def upload(self, file_content: bytes, filename: str, metadata: dict, force: bool = False) -> dict:
        """
        Upload PDF: encode base64, index with pipeline.

        - Checks if filename already exists → 409 if not force
        - Indexes with pipeline=attachment_pipeline (ES extracts text via Tika)
        - Returns the indexed document info

        Args:
            file_content: Raw bytes of the PDF file.
            filename: Original filename.
            metadata: Dict with optional fields (titulo, ementa, tipo_doc, ano, publico, tags, orgao, esfera, fonte).
            force: If True, overwrite existing document with same filename.

        Returns:
            Dict with _id, ato_id, and filename.

        Raises:
            ConflictError: If document with same filename exists and force=False.
            ServiceUnavailableError: If Elasticsearch is not available.
        """
        # Check duplicate
        if not force:
            existing = await self._find_by_filename(filename)
            if existing:
                raise ConflictError(f"Documento já existe: {filename}")

        # If force and existing, delete old document + chunks
        if force:
            existing = await self._find_by_filename(filename)
            if existing:
                old_id = existing["_id"]
                try:
                    await self.es.delete_by_query(index=self.chunks_index, body={
                        "query": {"term": {"parent_document_id": old_id}}
                    })
                    await self.es.delete(index=self.index, id=old_id)
                except Exception as exc:
                    logger.warning("Error deleting old document %s: %s", old_id, exc)

        # Build doc body
        ato_id = metadata.get("ato_id") or str(uuid.uuid4())
        body = {
            "data": base64.b64encode(file_content).decode("utf-8"),
            "filename": filename,
            "ato": {
                "ato_id": ato_id,
                "titulo": metadata.get("titulo", filename),
                "ementa": metadata.get("ementa"),
                "tipo_doc": metadata.get("tipo_doc"),
                "ano": metadata.get("ano"),
                "publico": metadata.get("publico", True),
                "tags": metadata.get("tags", []),
                "fonte": {
                    "orgao": metadata.get("orgao"),
                    "esfera": metadata.get("esfera"),
                    "sigla": metadata.get("fonte"),
                },
            },
        }
        # Remove None values from ato
        body["ato"] = {k: v for k, v in body["ato"].items() if v is not None}
        if "fonte" in body["ato"]:
            body["ato"]["fonte"] = {k: v for k, v in body["ato"]["fonte"].items() if v is not None}
            if not body["ato"]["fonte"]:
                del body["ato"]["fonte"]

        try:
            result = await self.es.index_with_pipeline(
                index=self.index, body=body, pipeline=settings.ES_INGEST_PIPELINE, id=ato_id
            )
        except Exception as exc:
            logger.error("ES index_with_pipeline failed: %s", exc)
            raise ServiceUnavailableError(f"Elasticsearch indisponível: {exc}")

        return {"_id": result["_id"], "ato_id": ato_id, "filename": filename}

    async def get_by_id(self, document_id: str) -> dict:
        """Get a document by its Elasticsearch ID."""
        try:
            doc = await self.es.get(index=self.index, id=document_id)
            return doc
        except Exception as exc:
            logger.debug("Document not found by ID %s: %s", document_id, exc)
            raise NotFoundError(f"Documento não encontrado: {document_id}")

    async def get_by_filename(self, filename: str) -> dict:
        """Get a document by its original filename."""
        try:
            result = await self.es.search(index=self.index, body={
                "query": {"term": {"filename.keyword": filename}}, "size": 1
            })
        except Exception as exc:
            logger.error("ES search failed: %s", exc)
            raise ServiceUnavailableError(f"Elasticsearch indisponível: {exc}")

        hits = result.get("hits", {}).get("hits", [])
        if not hits:
            raise NotFoundError(f"Documento não encontrado: {filename}")
        return hits[0]

    async def list_all(self, page: int = 1, page_size: int = 20, filters: dict | None = None) -> dict:
        """List documents with pagination and optional filters."""
        body: dict = {
            "from": (page - 1) * page_size,
            "size": page_size,
            "_source": {"excludes": ["data", "attachment.content"]},
            "query": {"match_all": {}},
            "sort": [{"_score": "desc"}],
        }

        # Add filters if provided
        if filters:
            must = []
            for k, v in filters.items():
                if v is not None:
                    must.append({"term": {f"ato.{k}": v}})
            if must:
                body["query"] = {"bool": {"must": must}}

        try:
            result = await self.es.search(index=self.index, body=body)
        except Exception as exc:
            logger.error("ES search failed: %s", exc)
            raise ServiceUnavailableError(f"Elasticsearch indisponível: {exc}")

        return result

    async def update_metadata(self, document_id: str, fields: dict) -> dict:
        """Update metadata fields of a document (partial update under ato.*)."""
        # Build partial update for ato.* fields
        ato_update = {k: v for k, v in fields.items() if v is not None}
        if not ato_update:
            raise ValidationError("Nenhum campo para atualizar")

        # Ensure the document exists
        await self.get_by_id(document_id)

        try:
            await self.es.update(index=self.index, id=document_id, body={"ato": ato_update})
        except Exception as exc:
            logger.error("ES update failed: %s", exc)
            raise ServiceUnavailableError(f"Elasticsearch indisponível: {exc}")

        return {"updated": list(ato_update.keys())}

    async def delete(self, document_id: str) -> dict:
        """Delete a document and all its associated chunks."""
        # Ensure the document exists
        await self.get_by_id(document_id)

        try:
            # Delete chunks first
            await self.es.delete_by_query(index=self.chunks_index, body={
                "query": {"term": {"parent_document_id": document_id}}
            })
            await self.es.delete(index=self.index, id=document_id)
        except Exception as exc:
            logger.error("ES delete failed: %s", exc)
            raise ServiceUnavailableError(f"Elasticsearch indisponível: {exc}")

        return {"deleted": True}

    async def _find_by_filename(self, filename: str) -> dict | None:
        """Find a document by filename, returns None if not found."""
        try:
            return await self.get_by_filename(filename)
        except (NotFoundError, ServiceUnavailableError):
            return None
