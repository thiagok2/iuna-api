"""
T-14 — Unit tests for app/core/query_helpers.py.
Funções puras — sem mocks, sem IO.
Ficam SKIPPED até o módulo ser criado.
"""

import pytest

query_helpers = pytest.importorskip(
    "app.core.query_helpers",
    reason="T-14 não implementado: app/core/query_helpers.py não existe",
)

build_match_phrase = query_helpers.build_match_phrase
build_match_fuzzy = query_helpers.build_match_fuzzy
build_nested_entity_query = query_helpers.build_nested_entity_query
build_highlight = query_helpers.build_highlight
build_term_filter = query_helpers.build_term_filter
build_range_filter = query_helpers.build_range_filter


# ---------------------------------------------------------------------------
# build_match_phrase
# ---------------------------------------------------------------------------


def test_build_match_phrase_estrutura():
    result = build_match_phrase("attachment.content", "edital processo seletivo")
    assert "match_phrase" in result
    assert "attachment.content" in result["match_phrase"]


def test_build_match_phrase_query_correta():
    result = build_match_phrase("attachment.content", "edital")
    inner = result["match_phrase"]["attachment.content"]
    query_val = inner if isinstance(inner, str) else inner.get("query")
    assert query_val == "edital"


# ---------------------------------------------------------------------------
# build_match_fuzzy
# ---------------------------------------------------------------------------


def test_build_match_fuzzy_estrutura():
    result = build_match_fuzzy("attachment.content", "edital")
    assert "match" in result or "fuzzy" in result


def test_build_match_fuzzy_fuzziness_auto():
    result = build_match_fuzzy("attachment.content", "edital", fuzziness="AUTO")
    raw = str(result)
    assert "AUTO" in raw or "auto" in raw


def test_build_match_fuzzy_fuzziness_custom():
    result = build_match_fuzzy("attachment.content", "edital", fuzziness=1)
    assert result is not None


# ---------------------------------------------------------------------------
# build_nested_entity_query
# ---------------------------------------------------------------------------


def test_build_nested_entity_query_estrutura():
    result = build_nested_entity_query("IFAL")
    assert "nested" in result
    assert result["nested"]["path"] in ("entidades", "ato.entidades", "artefato.entidades")


def test_build_nested_entity_query_sem_tipo():
    result = build_nested_entity_query("IFAL")
    assert result is not None


def test_build_nested_entity_query_com_tipo():
    result = build_nested_entity_query("IFAL", entity_type="ORGANIZACAO")
    raw = str(result)
    assert "ORGANIZACAO" in raw


# ---------------------------------------------------------------------------
# build_highlight
# ---------------------------------------------------------------------------


def test_build_highlight_estrutura():
    result = build_highlight(["attachment.content", "ato.resumo"])
    assert "fields" in result
    assert "attachment.content" in result["fields"]


def test_build_highlight_multiplos_fields():
    result = build_highlight(["field1", "field2", "field3"])
    assert len(result["fields"]) == 3


# ---------------------------------------------------------------------------
# build_term_filter
# ---------------------------------------------------------------------------


def test_build_term_filter_estrutura():
    result = build_term_filter("ato.tipo_doc.keyword", "edital")
    assert "term" in result
    assert result["term"]["ato.tipo_doc.keyword"] == "edital"


def test_build_term_filter_valor_inteiro():
    result = build_term_filter("ato.ano", 2024)
    assert result["term"]["ato.ano"] == 2024


# ---------------------------------------------------------------------------
# build_range_filter
# ---------------------------------------------------------------------------


def test_build_range_filter_gte_e_lte():
    result = build_range_filter("ato.data_publicacao", gte="2024-01-01", lte="2024-12-31")
    assert "range" in result
    inner = list(result["range"].values())[0]
    assert inner["gte"] == "2024-01-01"
    assert inner["lte"] == "2024-12-31"


def test_build_range_filter_apenas_gte():
    result = build_range_filter("ato.ano", gte=2020)
    inner = list(result["range"].values())[0]
    assert "gte" in inner
    assert "lte" not in inner


def test_build_range_filter_apenas_lte():
    result = build_range_filter("ato.ano", lte=2024)
    inner = list(result["range"].values())[0]
    assert "lte" in inner
    assert "gte" not in inner
