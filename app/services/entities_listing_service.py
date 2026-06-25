"""
EntitiesListingService — agrega entidades e keywords via ES terms aggregation.
"""

import logging
from typing import Any, Optional

from app.clients.es_client import ESClient

logger = logging.getLogger(__name__)

_AGG_SIZE = 1000


class EntitiesListingService:
    def __init__(self, es_client: ESClient) -> None:
        self.es = es_client

    async def list_entities(
        self,
        index: str,
        root: str,
        entity_type: Optional[str] = None,
        min_count: int = 1,
        page: int = 1,
        page_size: int = 50,
    ) -> list[dict[str, Any]]:
        path = f"{root}.entidades"
        inner_agg: dict
        if entity_type:
            inner_agg = {
                "filtered": {
                    "filter": {"term": {f"{path}.categoria": entity_type}},
                    "aggs": {
                        "by_texto": {
                            "terms": {
                                "field": f"{path}.texto.keyword",
                                "size": _AGG_SIZE,
                                "min_doc_count": min_count,
                            }
                        }
                    },
                }
            }
        else:
            inner_agg = {
                "by_texto": {
                    "terms": {
                        "field": f"{path}.texto.keyword",
                        "size": _AGG_SIZE,
                        "min_doc_count": min_count,
                    }
                }
            }

        body: dict = {
            "size": 0,
            "aggs": {"entities_agg": {"nested": {"path": path}, "aggs": inner_agg}},
        }
        resp = await self.es.search(index, body)
        agg = resp.get("aggregations", {}).get("entities_agg", {})
        if entity_type:
            buckets = agg.get("filtered", {}).get("by_texto", {}).get("buckets", [])
        else:
            buckets = agg.get("by_texto", {}).get("buckets", [])

        items = [{"texto": b["key"], "count": b["doc_count"]} for b in buckets]
        start = (page - 1) * page_size
        return items[start : start + page_size]

    async def list_keywords(
        self,
        index: str,
        root: str,
        min_count: int = 1,
        page: int = 1,
        page_size: int = 50,
    ) -> list[dict[str, Any]]:
        body: dict = {
            "size": 0,
            "aggs": {
                "all_keywords": {
                    "terms": {
                        "field": f"{root}.keywords.keyword",
                        "size": _AGG_SIZE,
                        "min_doc_count": min_count,
                    }
                }
            },
        }
        resp = await self.es.search(index, body)
        buckets = resp.get("aggregations", {}).get("all_keywords", {}).get("buckets", [])
        items = [{"keyword": b["key"], "count": b["doc_count"]} for b in buckets]
        start = (page - 1) * page_size
        return items[start : start + page_size]
