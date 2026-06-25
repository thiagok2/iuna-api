"""
Async Elasticsearch client singleton for the IUNA API.
"""

from typing import Optional

from elasticsearch import AsyncElasticsearch

from app.config import settings


class ESClient:
    """Singleton wrapper around AsyncElasticsearch."""

    _instance: Optional[AsyncElasticsearch] = None

    async def connect(self) -> None:
        """Create the AsyncElasticsearch client instance."""
        if self._instance is not None:
            return

        hosts = [h.strip() for h in settings.ELASTICSEARCH_HOSTS.split(",")]

        kwargs: dict = {
            "hosts": hosts,
            "verify_certs": False,
            "ssl_show_warn": False,
        }

        if settings.ELASTICSEARCH_USER and settings.ELASTICSEARCH_PASSWORD:
            kwargs["basic_auth"] = (
                settings.ELASTICSEARCH_USER,
                settings.ELASTICSEARCH_PASSWORD,
            )

        self._instance = AsyncElasticsearch(
            **kwargs,
            request_timeout=60,
            retry_on_timeout=True,
            max_retries=3,
        )

    async def close(self) -> None:
        """Close the Elasticsearch connection."""
        if self._instance is not None:
            await self._instance.close()
            self._instance = None

    async def reconnect(self) -> None:
        """Force close and reopen the connection."""
        await self.close()
        await self.connect()

    @property
    def client(self) -> AsyncElasticsearch:
        """Return the underlying client. Raises if not connected."""
        if self._instance is None:
            raise RuntimeError("ESClient is not connected. Call connect() first.")
        return self._instance

    # ------------------------------------------------------------------
    # Convenience methods
    # ------------------------------------------------------------------

    async def ping(self) -> bool:
        """Check connectivity with Elasticsearch."""
        try:
            return await self.client.ping()
        except Exception:
            return False

    async def search(self, index: str, body: dict) -> dict:
        """Execute a search query."""
        response = await self.client.search(index=index, body=body)
        return response.body

    async def get(self, index: str, id: str) -> dict:
        """Get a document by ID."""
        response = await self.client.get(index=index, id=id)
        return response.body

    async def index(self, index: str, body: dict, id: Optional[str] = None) -> dict:
        """Index (create/replace) a document."""
        kwargs: dict = {"index": index, "document": body}
        if id is not None:
            kwargs["id"] = id
        response = await self.client.index(**kwargs)
        return response.body

    async def index_with_pipeline(
        self, index: str, body: dict, pipeline: str, id: str | None = None
    ) -> dict:
        """Index a document using a specific ingest pipeline.

        Used primarily for the attachment_pipeline which extracts text
        from base64-encoded PDFs via Apache Tika (ES Ingest Attachment plugin).

        Args:
            index: Target index name.
            body: Document body (must include the field expected by the pipeline).
            pipeline: Name of the ingest pipeline (e.g. "attachment_pipeline").
            id: Optional document ID.

        Returns:
            Elasticsearch index response body.
        """
        kwargs: dict = {"index": index, "document": body, "pipeline": pipeline}
        if id:
            kwargs["id"] = id
        response = await self.client.index(**kwargs)
        return response.body

    async def update(self, index: str, id: str, body: dict) -> dict:
        """Partially update a document."""
        response = await self.client.update(index=index, id=id, doc=body)
        return response.body

    async def delete(self, index: str, id: str) -> dict:
        """Delete a document by ID."""
        response = await self.client.delete(index=index, id=id)
        return response.body

    async def delete_by_query(self, index: str, body: dict) -> dict:
        """Delete documents matching a query."""
        response = await self.client.delete_by_query(index=index, body=body)
        return response.body

    async def bulk_index(self, index: str, documents: list) -> dict:
        """Bulk-index a list of documents."""
        operations: list = []
        for doc in documents:
            operations.append({"index": {"_index": index}})
            operations.append(doc)
        response = await self.client.bulk(operations=operations)
        return response.body

    async def create_index(self, index: str, body: dict) -> None:
        """Create an index with the given mapping/settings."""
        await self.client.indices.create(index=index, body=body)

    async def delete_index(self, index: str) -> None:
        """Delete an index."""
        await self.client.indices.delete(index=index)


# Module-level singleton
es_client = ESClient()
