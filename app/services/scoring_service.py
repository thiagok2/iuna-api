"""
ScoringService — incrementa popularity_score no ES com read-modify-write.
"""

import logging

from elasticsearch import NotFoundError as ESNotFoundError

from app.clients.es_client import ESClient
from app.core.exceptions import NotFoundError
from app.core.scoring import SCORE_WEIGHTS

logger = logging.getLogger(__name__)


class ScoringService:
    def __init__(self, es_client: ESClient) -> None:
        self.es = es_client

    async def increment_score(
        self,
        index: str,
        doc_id: str,
        action: str,
        root: str = "ato",
    ) -> float:
        delta = SCORE_WEIGHTS[action]  # raises KeyError for invalid action

        try:
            doc = await self.es.get(index, doc_id)
        except ESNotFoundError:
            raise NotFoundError(f"Documento não encontrado: {doc_id}")

        current: float = doc["_source"].get(root, {}).get("popularity_score") or 0.0
        new_score = current + delta

        await self.es.update(index, doc_id, {root: {"popularity_score": new_score}})
        return new_score
