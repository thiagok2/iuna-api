"""
T-14 — Smoke test de app/core/query_helpers.py.
Não requer ES nem LLM — apenas importa e chama as funções.

Uso:
    source .venv/bin/activate
    python tests/manual/t14_query_helpers.py
"""

import json
from app.core.query_helpers import (
    build_match_phrase,
    build_match_fuzzy,
    build_nested_entity_query,
    build_highlight,
    build_term_filter,
    build_range_filter,
)


def show(label: str, result: dict) -> None:
    print(f"\n→ {label}")
    print(f"  {json.dumps(result, ensure_ascii=False, indent=2)}")


show("build_match_phrase", build_match_phrase("attachment.content", "prazo de inscrição"))
show("build_match_fuzzy", build_match_fuzzy("attachment.content", "edictal", fuzziness="AUTO"))
show("build_nested_entity_query (sem tipo)", build_nested_entity_query("IFAL"))
show("build_nested_entity_query (com tipo)", build_nested_entity_query("IFAL", entity_type="ORGANIZACAO"))
show("build_highlight", build_highlight(["attachment.content", "ato.resumo"]))
show("build_term_filter (string)", build_term_filter("ato.tipo_doc.keyword", "edital"))
show("build_term_filter (int)", build_term_filter("ato.ano", 2024))
show("build_range_filter (gte+lte)", build_range_filter("ato.data_publicacao", gte="2024-01-01", lte="2024-12-31"))
show("build_range_filter (apenas gte)", build_range_filter("ato.ano", gte=2020))

print("\nT-14 OK — todas as funções retornaram sem erro.")
