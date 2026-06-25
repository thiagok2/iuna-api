"""
DocumentosSearchService — busca no índice documentos_ifal_v2.
"""

from app.clients.es_client import ESClient
from app.services._search_base import BaseSearchService


class DocumentosSearchService(BaseSearchService):
    root = "ato"
    entity_path = "ato.entidades"
    title_field = "ato.titulo"
    search_fields = ["attachment.content", "ato.titulo^2", "ato.resumo"]
    keyword_field = "ato.keywords.keyword"
    score_field = "ato.popularity_score"
    facet_fields = {
        "tipo_doc": "ato.tipo_doc.keyword",
        "orgao": "ato.fonte.orgao.keyword",
        "esfera": "ato.fonte.esfera.keyword",
        "ano": "ato.ano",
    }

    def __init__(self, es_client: ESClient) -> None:
        super().__init__(es_client)
