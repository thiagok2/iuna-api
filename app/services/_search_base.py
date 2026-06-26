"""
BaseSearchService — shared search logic for documentos and artefatos.
"""

import logging
from typing import Any, Optional

from elasticsearch import AuthorizationException as ESAuthorizationException

from app.clients.es_client import ESClient
from app.core.query_helpers import (
    build_highlight,
    build_nested_entity_query,
    build_range_filter,
    build_term_filter,
)

logger = logging.getLogger(__name__)


class BaseSearchService:
    root: str
    entity_path: str
    title_field: str
    search_fields: list[str]
    facet_fields: dict[str, str]
    keyword_field: str
    score_field: str

    def __init__(self, es_client: ESClient) -> None:
        self.es = es_client

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _format_hits(self, hits: list[dict]) -> list[dict]:
        return [
            {
                "id": h["_id"],
                "score": h.get("_score"),
                "source": h.get("_source", {}),
                "highlights": h.get("highlight", {}),
            }
            for h in hits
        ]

    def _build_filters(self, filters: Optional[dict]) -> list[dict]:
        clauses: list[dict] = []
        if not filters:
            return clauses
        for field, value in filters.items():
            if value is None:
                continue
            clauses.append(build_term_filter(field, value))
        return clauses

    def _base_query(
        self, q: str, extra_filters: list[dict], exact_phrase: bool = False
    ) -> dict:
        if exact_phrase:
            match_clause: dict = {
                "multi_match": {
                    "query": q,
                    "fields": self.search_fields,
                    "type": "phrase",
                }
            }
        else:
            match_clause = {
                "multi_match": {
                    "query": q,
                    "fields": self.search_fields,
                    "type": "best_fields",
                    "fuzziness": "AUTO",
                }
            }
        return {
            "function_score": {
                "query": {
                    "bool": {
                        "must": [match_clause],
                        "filter": extra_filters,
                    }
                },
                "functions": [
                    {
                        "field_value_factor": {
                            "field": self.score_field,
                            "missing": 0,
                            "modifier": "log1p",
                            "factor": 0.5,
                        }
                    }
                ],
                "boost_mode": "sum",
            }
        }

    # ------------------------------------------------------------------
    # Public search methods
    # ------------------------------------------------------------------

    async def search_fulltext(
        self,
        index: str,
        q: str,
        page: int = 1,
        page_size: int = 20,
        filters: Optional[dict] = None,
        exact_phrase: bool = False,
        with_aggregations: bool = False,
    ) -> dict[str, Any]:
        extra_filters = self._build_filters(filters)
        body = {
            "query": self._base_query(q, extra_filters, exact_phrase),
            "highlight": build_highlight([self.title_field, "attachment.content"]),
            "from": (page - 1) * page_size,
            "size": page_size,
        }
        if with_aggregations:
            body["aggs"] = {
                name: {"terms": {"field": field, "size": 30}}
                for name, field in self.facet_fields.items()
            }
        resp = await self.es.search(index=index, body=body)
        hits_raw = resp.get("hits", {})
        total = hits_raw.get("total", {}).get("value", 0)
        result: dict[str, Any] = {
            "results": self._format_hits(hits_raw.get("hits", [])),
            "total": total,
        }
        if with_aggregations:
            result["aggregations"] = {
                name: resp.get("aggregations", {}).get(name, {})
                for name in self.facet_fields
            }
        return result

    async def search_facets(
        self,
        index: str,
        q: str = "",
        filters: Optional[dict] = None,
    ) -> dict[str, Any]:
        extra_filters = self._build_filters(filters)
        query: dict
        if q:
            query = self._base_query(q, extra_filters)
        else:
            query = {"bool": {"filter": extra_filters}} if extra_filters else {"match_all": {}}

        aggs = {
            name: {"terms": {"field": field, "size": 30}}
            for name, field in self.facet_fields.items()
        }
        body = {"query": query, "size": 0, "aggs": aggs}
        resp = await self.es.search(index=index, body=body)
        aggregations = {
            name: resp.get("aggregations", {}).get(name, {})
            for name in self.facet_fields
        }
        total = resp.get("hits", {}).get("total", {}).get("value", 0)
        return {"aggregations": aggregations, "total": total}

    async def search_similar(
        self,
        index: str,
        doc_id: str,
        page_size: int = 10,
    ) -> dict[str, Any]:
        body = {
            "query": {
                "more_like_this": {
                    "fields": [self.title_field, "attachment.content"],
                    "like": [{"_index": index, "_id": doc_id}],
                    "min_term_freq": 1,
                    "max_query_terms": 12,
                    "min_doc_freq": 1,
                }
            },
            "size": page_size,
        }
        resp = await self.es.search(index=index, body=body)
        hits_raw = resp.get("hits", {})
        total = hits_raw.get("total", {}).get("value", 0)
        return {
            "results": self._format_hits(hits_raw.get("hits", [])),
            "total": total,
        }

    async def search_related(
        self,
        index: str,
        doc_id: str,
        limit: int = 10,
    ) -> dict[str, Any]:
        # dense_vector é excluído do _source padrão no ES 8.x; source_includes força a inclusão
        source_includes = [
            f"{self.root}.embedding_vector",
            f"{self.root}.entidades",
            f"{self.root}.keywords",
        ]
        doc = await self.es.get(index=index, id=doc_id, source_includes=source_includes)
        root_data = doc.get("_source", {}).get(self.root, {})

        embedding: list[float] | None = root_data.get("embedding_vector")
        entidades: list[dict] = root_data.get("entidades") or []
        keywords: list[str] = root_data.get("keywords") or []

        enrichment_used: list[str] = []
        must_not = [{"term": {"_id": doc_id}}]

        mlt_fields = [f"{self.root}.ementa", self.title_field, "attachment.content"]
        should: list[dict] = [
            {
                "more_like_this": {
                    "fields": mlt_fields,
                    "like": [{"_index": index, "_id": doc_id}],
                    "min_term_freq": 1,
                    "max_query_terms": 12,
                    "min_doc_freq": 1,
                    "boost": 0.5,
                }
            }
        ]

        entity_texts = [e["texto"] for e in entidades if e.get("texto")][:10]
        if entity_texts:
            enrichment_used.append("entities")
            should.append({
                "nested": {
                    "path": self.entity_path,
                    "query": {
                        "bool": {
                            "should": [
                                {"match": {f"{self.entity_path}.texto": t}}
                                for t in entity_texts
                            ]
                        }
                    },
                    "boost": 1.5,
                }
            })

        if keywords:
            enrichment_used.append("keywords")
            should.append({
                "terms": {
                    self.keyword_field: keywords[:20],
                    "boost": 1.2,
                }
            })

        body: dict = {
            "query": {"bool": {"should": should, "must_not": must_not}},
            "size": limit,
        }

        if embedding:
            enrichment_used.append("embedding")
            body_rrf = {
                **body,
                "knn": {
                    "field": f"{self.root}.embedding_vector",
                    "query_vector": embedding,
                    "k": limit,
                    "num_candidates": limit * 2,
                    "filter": {"bool": {"must_not": must_not}},
                },
                "rank": {"rrf": {"window_size": limit * 2}},
            }
            try:
                resp = await self.es.search(index=index, body=body_rrf)
            except ESAuthorizationException:
                # licença sem RRF — fallback para bool query sem kNN
                logger.warning("RRF não disponível nesta licença ES; usando fallback sem kNN")
                enrichment_used.remove("embedding")
                resp = await self.es.search(index=index, body=body)
        else:
            resp = await self.es.search(index=index, body=body)
        hits_raw = resp.get("hits", {})
        total = hits_raw.get("total", {}).get("value", 0)
        return {
            "results": self._format_hits(hits_raw.get("hits", [])),
            "total": total,
            "enrichment_used": enrichment_used,
        }

    async def search_by_entity(
        self,
        index: str,
        entity: str,
        entity_type: Optional[str] = None,
        page: int = 1,
        page_size: int = 20,
    ) -> dict[str, Any]:
        body = {
            "query": build_nested_entity_query(entity, entity_type, path=self.entity_path),
            "from": (page - 1) * page_size,
            "size": page_size,
        }
        resp = await self.es.search(index=index, body=body)
        hits_raw = resp.get("hits", {})
        total = hits_raw.get("total", {}).get("value", 0)
        return {
            "results": self._format_hits(hits_raw.get("hits", [])),
            "total": total,
        }

    async def search_by_keyword(
        self,
        index: str,
        keyword: str,
        page: int = 1,
        page_size: int = 20,
    ) -> dict[str, Any]:
        body = {
            "query": build_term_filter(self.keyword_field, keyword),
            "from": (page - 1) * page_size,
            "size": page_size,
        }
        resp = await self.es.search(index=index, body=body)
        hits_raw = resp.get("hits", {})
        total = hits_raw.get("total", {}).get("value", 0)
        return {
            "results": self._format_hits(hits_raw.get("hits", [])),
            "total": total,
        }

    async def suggest(
        self,
        index: str,
        q: str,
        size: int = 5,
    ) -> list[str]:
        body = {
            "query": {
                "match_phrase_prefix": {
                    self.title_field: {"query": q, "max_expansions": 10}
                }
            },
            "size": size,
            "_source": [self.title_field],
        }
        resp = await self.es.search(index=index, body=body)
        suggestions: list[str] = []
        for hit in resp.get("hits", {}).get("hits", []):
            root_data = hit.get("_source", {}).get(self.root, {})
            title = root_data.get("titulo", "")
            if title and title not in suggestions:
                suggestions.append(title)
        return suggestions[:size]
