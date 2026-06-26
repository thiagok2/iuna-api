"""
RasaClient — classificação de intenção via Rasa NLU HTTP API.

Fallback automático para "ask_about_document" se:
- Rasa estiver indisponível (timeout / conexão recusada)
- confidence da intent for inferior a CONFIDENCE_THRESHOLD
"""

import logging

import httpx

from app.config import settings

logger = logging.getLogger(__name__)

CONFIDENCE_THRESHOLD = 0.6
FALLBACK_INTENT = "ask_about_document"


class RasaClient:
    async def parse(self, message: str) -> dict:
        """Classifica a intenção da mensagem via Rasa NLU.

        Returns:
            dict com intent.name e intent.confidence.
            Em caso de falha ou baixa confidence retorna fallback.
        """
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.post(
                    f"{settings.RASA_API_URL}/model/parse",
                    json={"text": message},
                )
                response.raise_for_status()
                data = response.json()

                confidence = data.get("intent", {}).get("confidence", 0)
                if confidence < CONFIDENCE_THRESHOLD:
                    return {"intent": {"name": FALLBACK_INTENT, "confidence": 1.0}}
                return data
        except Exception as exc:
            logger.warning("Rasa parse falhou, usando fallback: %s", exc)
            return {"intent": {"name": FALLBACK_INTENT, "confidence": 1.0}}

    async def health_check(self) -> bool:
        """Retorna True se o servidor Rasa estiver acessível."""
        try:
            async with httpx.AsyncClient(timeout=3.0) as client:
                response = await client.get(f"{settings.RASA_API_URL}/")
                return response.status_code == 200
        except Exception:
            return False


rasa_client = RasaClient()
