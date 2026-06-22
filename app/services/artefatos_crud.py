"""
Service layer for CRUD operations on artefatos (didactic artifacts).
"""

import base64
import logging
import uuid
from datetime import datetime, timezone

from app.clients.es_client import ESClient
from app.config import settings
from app.core.exceptions import ConflictError, NotFoundError, ServiceUnavailableError, ValidationError

logger = logging.getLogger(__name__)


class ArtefatosCrudService:
    """Handles CRUD operations for the artefatos index."""

    def __init__(self, es_client: ESClient):
        self.es = es_client
        self.index = settings.index_artefatos
        self.chunks_index = settings.index_artefatos_chunks

    async def upload(self, file_content: bytes, filename: str, metadata: dict, force: bool = False) -> dict:
        """
        Upload PDF artefato: encode base64, index with pipeline.

        - If filename already exists and force=False → 409
        - If filename already exists and force=True → delete old + chunks, then reindex
        - Indexes with pipeline=attachment_pipeline (ES extracts text via Tika)

        Args:
            file_content: Raw bytes of the PDF file.
            filename: Original filename.
            metadata: Dict with fields (titulo, tipo, tags, disciplina, curso, autor, ano, publico, uploaded_by).
            force: If True, overwrite existing artefato with same filename.

        Returns:
            Dict with _id, artefato_id, and filename.

        Raises:
            ConflictError: If artefato with same filename exists and force=False.
            ValidationError: If required fields are missing.
            ServiceUnavailableError: If Elasticsearch is not available.
        """
        # Validate required fields
        uploaded_by = metadata.get("uploaded_by", "system")
        titulo = metadata.get("titulo") or filename

        # Check duplicate — if exists and force, delete old
        existing = await self._find_by_filename(filename)
        if existing and not force:
            raise ConflictError(f"Artefato já existe: {filename}")

        if existing and force:
            old_id = existing["_id"]
            try:
                await self.es.delete_by_query(index=self.chunks_index, body={
                    "query": {"term": {"parent_document_id": old_id}}
                })
                await self.es.delete(index=self.index, id=old_id)
            except Exception as exc:
                logger.warning("Error deleting old artefato %s: %s", old_id, exc)

        # Build doc body
        artefato_id = metadata.get("artefato_id") or str(uuid.uuid4())
        now = datetime.now(timezone.utc).isoformat()

        body = {
            "data": base64.b64encode(file_content).decode("utf-8"),
            "filename": filename,
            "artefato": {
                "artefato_id": artefato_id,
                "titulo": titulo,
                "tipo": metadata.get("tipo"),
                "tags": metadata.get("tags", []),
                "uploaded_by": uploaded_by,
                "created_at": now,
                "updated_at": now,
                "disciplina": metadata.get("disciplina"),
                "curso": metadata.get("curso"),
                "autor": metadata.get("autor"),
                "ano": metadata.get("ano"),
                "publico": metadata.get("publico", True),
            },
        }
        # Remove None values from artefato
        body["artefato"] = {k: v for k, v in body["artefato"].items() if v is not None}

        try:
            result = await self.es.index_with_pipeline(
                index=self.index, body=body, pipeline=settings.ES_INGEST_PIPELINE, id=artefato_id
            )
        except Exception as exc:
            logger.error("ES index_with_pipeline failed: %s", exc)
            raise ServiceUnavailableError(f"Elasticsearch indisponível: {exc}")

        return {"_id": result["_id"], "artefato_id": artefato_id, "filename": filename}

    async def get_by_id(self, artefato_id: str) -> dict:
        """Get an artefato by its Elasticsearch ID."""
        try:
            doc = await self.es.get(index=self.index, id=artefato_id)
            return doc
        except Exception as exc:
            logger.debug("Artefato not found by ID %s: %s", artefato_id, exc)
            raise NotFoundError(f"Artefato não encontrado: {artefato_id}")

    async def get_by_filename(self, filename: str) -> dict:
        """Get an artefato by its original filename."""
        try:
            result = await self.es.search(index=self.index, body={
                "query": {"term": {"filename.keyword": filename}}, "size": 1
            })
        except Exception as exc:
            logger.error("ES search failed: %s", exc)
            raise ServiceUnavailableError(f"Elasticsearch indisponível: {exc}")

        hits = result.get("hits", {}).get("hits", [])
        if not hits:
            raise NotFoundError(f"Artefato não encontrado: {filename}")
        return hits[0]

    async def list_all(self, page: int = 1, page_size: int = 20, filters: dict | None = None) -> dict:
        """List artefatos with pagination and optional filters."""
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
                    must.append({"term": {f"artefato.{k}": v}})
            if must:
                body["query"] = {"bool": {"must": must}}

        try:
            result = await self.es.search(index=self.index, body=body)
        except Exception as exc:
            logger.error("ES search failed: %s", exc)
            raise ServiceUnavailableError(f"Elasticsearch indisponível: {exc}")

        return result

    async def update_metadata(self, artefato_id: str, fields: dict) -> dict:
        """Update metadata fields of an artefato (partial update under artefato.*)."""
        artefato_update = {k: v for k, v in fields.items() if v is not None}
        if not artefato_update:
            raise ValidationError("Nenhum campo para atualizar")

        # Add updated_at timestamp
        artefato_update["updated_at"] = datetime.now(timezone.utc).isoformat()

        # Ensure the artefato exists
        await self.get_by_id(artefato_id)

        try:
            await self.es.update(index=self.index, id=artefato_id, body={"artefato": artefato_update})
        except Exception as exc:
            logger.error("ES update failed: %s", exc)
            raise ServiceUnavailableError(f"Elasticsearch indisponível: {exc}")

        return {"updated": list(artefato_update.keys())}

    async def delete(self, artefato_id: str) -> dict:
        """Delete an artefato and all its associated chunks."""
        # Ensure the artefato exists
        await self.get_by_id(artefato_id)

        try:
            # Delete chunks first
            await self.es.delete_by_query(index=self.chunks_index, body={
                "query": {"term": {"parent_document_id": artefato_id}}
            })
            await self.es.delete(index=self.index, id=artefato_id)
        except Exception as exc:
            logger.error("ES delete failed: %s", exc)
            raise ServiceUnavailableError(f"Elasticsearch indisponível: {exc}")

        return {"deleted": True}

    async def _find_by_filename(self, filename: str) -> dict | None:
        """Find an artefato by filename, returns None if not found."""
        try:
            return await self.get_by_filename(filename)
        except (NotFoundError, ServiceUnavailableError):
            return None
