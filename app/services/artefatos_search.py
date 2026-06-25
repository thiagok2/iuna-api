"""
ArtefatosSearchService — busca no índice artefatos.
"""

from app.clients.es_client import ESClient
from app.services._search_base import BaseSearchService


class ArtefatosSearchService(BaseSearchService):
    root = "artefato"
    entity_path = "artefato.entidades"
    title_field = "artefato.titulo"
    search_fields = ["attachment.content", "artefato.titulo^2", "artefato.resumo"]
    keyword_field = "artefato.keywords.keyword"
    score_field = "artefato.popularity_score"
    facet_fields = {
        "tipo": "artefato.tipo",
        "disciplina": "artefato.disciplina.keyword",
    }

    def __init__(self, es_client: ESClient) -> None:
        super().__init__(es_client)
