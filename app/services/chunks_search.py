"""
ChunksSearchService — busca full-text nos índices de chunks.
"""

import logging
from typing import Any, Optional

from app.clients.es_client import ESClient

logger = logging.getLogger(__name__)


class ChunksSearchService:
    def __init__(self, es_client: ESClient) -> None:
        self.es = es_client

    async def search(
        self,
        index: str,
        q: str,
        page: int = 1,
        page_size: int = 20,
        document_id: Optional[str] = None,
    ) -> dict[str, Any]:
        filter_clauses: list[dict] = []
        if document_id:
            filter_clauses.append({"term": {"parent_document_id": document_id}})

        body: dict = {
            "query": {
                "bool": {
                    "must": [{"match": {"content": {"query": q, "fuzziness": "AUTO"}}}],
                    "filter": filter_clauses,
                }
            },
            "highlight": {
                "fields": {"content": {"fragment_size": 200, "number_of_fragments": 2}},
                "pre_tags": ["<em>"],
                "post_tags": ["</em>"],
            },
            "from": (page - 1) * page_size,
            "size": page_size,
        }
        resp = await self.es.search(index=index, body=body)
        hits_raw = resp.get("hits", {})
        total = hits_raw.get("total", {}).get("value", 0)
        results = [
            {
                "id": h["_id"],
                "score": h.get("_score"),
                "source": h.get("_source", {}),
                "highlights": h.get("highlight", {}),
            }
            for h in hits_raw.get("hits", [])
        ]
        return {"results": results, "total": total}
