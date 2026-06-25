"""
Query builder helpers — pure functions returning ES DSL dicts.
"""

from typing import Any


def build_match_phrase(field: str, query: str) -> dict:
    return {"match_phrase": {field: query}}


def build_match_fuzzy(field: str, query: str, fuzziness: Any = "AUTO") -> dict:
    return {"match": {field: {"query": query, "fuzziness": fuzziness}}}


def build_nested_entity_query(
    entity: str,
    entity_type: str | None = None,
    path: str = "ato.entidades",
) -> dict:
    must: list[dict] = [{"match": {f"{path}.texto": entity}}]
    if entity_type:
        must.append({"term": {f"{path}.categoria": entity_type}})
    return {"nested": {"path": path, "query": {"bool": {"must": must}}}}


def build_highlight(fields: list[str]) -> dict:
    return {
        "fields": {f: {} for f in fields},
        "pre_tags": ["<em>"],
        "post_tags": ["</em>"],
    }


def build_term_filter(field: str, value: Any) -> dict:
    return {"term": {field: value}}


def build_range_filter(
    field: str,
    gte: Any = None,
    lte: Any = None,
) -> dict:
    clause: dict = {}
    if gte is not None:
        clause["gte"] = gte
    if lte is not None:
        clause["lte"] = lte
    return {"range": {field: clause}}
