"""
LegadoSearchService — busca no índice legado `documentos_ifal`.

O índice legado não possui enriquecimento (sem resumo, keywords, entidades,
embedding_vector ou popularity_score). Os campos de busca são:
  attachment.content, ato.titulo, ato.ementa, ato.tags

Diferenças do DocumentosSearchService (v2):
  - exact_phrase: bool — usa match_phrase em vez de multi_match fuzzy
  - periodo: str — filtro por período (ex.: "2020", "2020-2024")
  - orgao: str — filtro direto por ato.fonte.orgao.keyword
  - publico: bool — filtra ato.publico
  - Sem function_score (sem popularity_score no índice legado)
  - MLT usa ato.ementa + ato.tags (não attachment.content)
  - Fallback automático: se 0 resultados com tipo_doc, retenta sem ele
"""

import logging
import re
from typing import Any, Optional

from app.clients.es_client import ESClient

logger = logging.getLogger(__name__)

_SEARCH_FIELDS = ["attachment.content", "ato.titulo^2", "ato.ementa^1.5", "ato.tags"]
_FACET_FIELDS = {
    "tipo_doc": "ato.tipo_doc.keyword",
    "esfera": "ato.fonte.esfera.keyword",
    "ano": "ato.ano",
}


def _periodo_to_range(periodo: str) -> Optional[dict]:
    """Converte string de período em filtro de range ES.

    Formatos aceitos:
      "2024"       → {gte: "2024-01-01", lte: "2024-12-31"}
      "2020-2024"  → {gte: "2020-01-01", lte: "2024-12-31"}
    """
    if not periodo or periodo == "all":
        return None
    single = re.fullmatch(r"(\d{4})", periodo)
    if single:
        y = single.group(1)
        return {"gte": f"{y}-01-01", "lte": f"{y}-12-31"}
    span = re.fullmatch(r"(\d{4})-(\d{4})", periodo)
    if span:
        return {"gte": f"{span.group(1)}-01-01", "lte": f"{span.group(2)}-12-31"}
    return None


class LegadoSearchService:
    def __init__(self, es_client: ESClient) -> None:
        self.es = es_client

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _build_query(
        self,
        q: str,
        exact_phrase: bool,
        filters: list[dict],
    ) -> dict:
        if exact_phrase:
            base: dict = {
                "multi_match": {
                    "query": q,
                    "fields": _SEARCH_FIELDS,
                    "type": "phrase",
                }
            }
        else:
            base = {
                "multi_match": {
                    "query": q,
                    "fields": _SEARCH_FIELDS,
                    "type": "best_fields",
                    "fuzziness": "AUTO",
                }
            }
        if not filters:
            return base
        return {"bool": {"must": [base], "filter": filters}}

    def _build_filters(
        self,
        tipo_doc: Optional[str],
        esfera: Optional[str],
        ano: Optional[int],
        orgao: Optional[str],
        publico: Optional[bool],
        periodo: Optional[str],
    ) -> list[dict]:
        clauses: list[dict] = []
        if tipo_doc:
            clauses.append({"term": {"ato.tipo_doc.keyword": tipo_doc}})
        if esfera:
            clauses.append({"term": {"ato.fonte.esfera.keyword": esfera}})
        if ano:
            clauses.append({"term": {"ato.ano": ano}})
        if orgao:
            clauses.append({"term": {"ato.fonte.orgao.keyword": orgao}})
        if publico is not None:
            clauses.append({"term": {"ato.publico": publico}})
        if periodo:
            range_val = _periodo_to_range(periodo)
            if range_val:
                clauses.append({"range": {"ato.data_publicacao": range_val}})
        return clauses

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

    # ------------------------------------------------------------------
    # Public methods
    # ------------------------------------------------------------------

    async def search(
        self,
        index: str,
        q: str,
        page: int = 1,
        page_size: int = 10,
        exact_phrase: bool = False,
        tipo_doc: Optional[str] = None,
        esfera: Optional[str] = None,
        ano: Optional[int] = None,
        orgao: Optional[str] = None,
        publico: Optional[bool] = None,
        periodo: Optional[str] = None,
        with_aggregations: bool = True,
    ) -> dict[str, Any]:
        filters = self._build_filters(tipo_doc, esfera, ano, orgao, publico, periodo)
        body: dict = {
            "query": self._build_query(q, exact_phrase, filters),
            "highlight": {
                "fields": {
                    "attachment.content": {"fragment_size": 200, "number_of_fragments": 2},
                    "ato.ementa": {},
                    "ato.titulo": {},
                },
                "pre_tags": ["<em>"],
                "post_tags": ["</em>"],
            },
            "from": (page - 1) * page_size,
            "size": page_size,
        }
        if with_aggregations:
            body["aggs"] = {
                name: {"terms": {"field": field, "size": 30}}
                for name, field in _FACET_FIELDS.items()
            }

        resp = await self.es.search(index=index, body=body)
        hits_raw = resp.get("hits", {})
        total = hits_raw.get("total", {}).get("value", 0)
        result: dict[str, Any] = {
            "results": self._format_hits(hits_raw.get("hits", [])),
            "total": total,
        }

        # Fallback: sem tipo_doc se zero resultados
        if total == 0 and tipo_doc:
            return await self.search(
                index=index,
                q=q,
                page=page,
                page_size=page_size,
                exact_phrase=exact_phrase,
                tipo_doc=None,
                esfera=esfera,
                ano=ano,
                orgao=orgao,
                publico=publico,
                periodo=periodo,
                with_aggregations=with_aggregations,
            )

        if with_aggregations:
            result["aggregations"] = {
                name: resp.get("aggregations", {}).get(name, {})
                for name in _FACET_FIELDS
            }
        return result

    async def get_by_id(self, index: str, doc_id: str) -> dict[str, Any]:
        """Recupera documento pelo ES _id (equivalente ao viewNormativa do Laravel).

        No índice legado, o _id é o próprio ato.arquivo (caminho do arquivo).
        Retorna o _source completo incluindo ato.*, attachment.content, filename.
        """
        doc = await self.es.get(index=index, id=doc_id)
        source = doc.get("_source", {})
        return {
            "id": doc["_id"],
            "arquivo_id": doc["_id"],  # alias legado (ato.arquivo == _id)
            "source": source,
            "ato": source.get("ato", {}),
            "filename": source.get("filename"),
        }

    async def similar(
        self, index: str, doc_id: str, page_size: int = 6
    ) -> dict[str, Any]:
        body: dict = {
            "query": {
                "more_like_this": {
                    "fields": ["ato.ementa", "ato.tags"],
                    "like": [{"_index": index, "_id": doc_id}],
                    "min_term_freq": 1,
                    "max_query_terms": 15,
                    "min_doc_freq": 1,
                }
            },
            "_source": {"includes": ["ato.*", "filename"]},
            "size": page_size,
        }
        resp = await self.es.search(index=index, body=body)
        hits_raw = resp.get("hits", {})
        return {
            "results": self._format_hits(hits_raw.get("hits", [])),
            "total": hits_raw.get("total", {}).get("value", 0),
        }
