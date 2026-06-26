"""
ChatService — chat RAG com sessões persistidas no Elasticsearch.

Fluxo de handle_message:
  1. Busca/cria sessão (verifica TTL)
  2. Classifica intenção via Rasa (fallback: ask_about_document)
  3. Chitchat → LLM sem contexto de documentos
  4. ask_about_document → monta contexto a partir da sessão e faz RAG
  5. Persiste mensagens + renova expires_at
"""

import logging
from datetime import datetime, timedelta, timezone

from elasticsearch import NotFoundError as ESNotFoundError

from app.clients.es_client import ESClient
from app.clients.rasa_client import RasaClient
from app.config import settings
from app.core.exceptions import NotFoundError
from app.providers.base import BaseLLMProvider
from app.services.scoring_service import ScoringService

logger = logging.getLogger(__name__)


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _iso(dt: datetime) -> str:
    return dt.isoformat()


class ChatService:
    def __init__(
        self,
        es_client: ESClient,
        llm_provider: BaseLLMProvider,
        embedding_provider: BaseLLMProvider,
        rasa_client: RasaClient,
    ) -> None:
        self.es = es_client
        self.llm = llm_provider
        self.embed = embedding_provider
        self.rasa = rasa_client
        self.scoring = ScoringService(es_client)
        self.sessions_index = settings.index_chat_sessions
        self._all_chunks_indices = [
            settings.index_documentos_ifal_v2_chunks,
            settings.index_artefatos_chunks,
        ]

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def handle_message(
        self, message: str, session_id: str, source_type: str | None = None
    ) -> dict:
        """Processa mensagem e retorna resposta RAG."""
        session = await self._get_or_create_session(session_id)
        intent = await self._classify_intent(message)

        history = session.get("messages", [])[-settings.CHAT_HISTORY_MAX_MESSAGES:]
        context_used = bool(
            session.get("context_document_ids") or session.get("context_artefato_ids")
        )

        if intent == "chitchat":
            response = await self.llm.generate_response(
                context="", question=message, history=history
            )
        else:
            context = await self._build_context(message, session, source_type)
            response = await self.llm.generate_response(
                context=context, question=message, history=history
            )

        await self._append_and_renew(session_id, message, response)

        return {
            "response": response,
            "intent": intent,
            "session_id": session_id,
            "context_used": context_used,
            "context_document_ids": session.get("context_document_ids", []),
            "context_artefato_ids": session.get("context_artefato_ids", []),
        }

    async def get_session(self, session_id: str) -> dict:
        """Retorna dados da sessão. Lança NotFoundError se não existir."""
        try:
            doc = await self.es.get(index=self.sessions_index, id=session_id)
            return doc["_source"]
        except ESNotFoundError:
            raise NotFoundError(f"Sessão não encontrada: {session_id}")

    async def list_sessions(self, page: int = 1, page_size: int = 20) -> dict:
        """Lista sessões ativas (expires_at > now), ordenadas por last_activity_at desc."""
        now = _iso(_now())
        body = {
            "query": {"range": {"expires_at": {"gt": now}}},
            "sort": [{"last_activity_at": {"order": "desc"}}],
            "from": (page - 1) * page_size,
            "size": page_size,
        }
        resp = await self.es.search(index=self.sessions_index, body=body)
        hits = resp.get("hits", {})
        total = hits.get("total", {}).get("value", 0)
        sessions = [
            {
                "session_id": h["_source"].get("session_id"),
                "last_activity_at": h["_source"].get("last_activity_at"),
                "message_count": len(h["_source"].get("messages", [])),
                "context_document_ids": h["_source"].get("context_document_ids", []),
                "context_artefato_ids": h["_source"].get("context_artefato_ids", []),
                "expires_at": h["_source"].get("expires_at"),
            }
            for h in hits.get("hits", [])
        ]
        return {
            "sessions": sessions,
            "total": total,
            "page": page,
            "page_size": page_size,
        }

    async def delete_session(self, session_id: str) -> None:
        """Remove a sessão permanentemente. Lança NotFoundError se não existir."""
        try:
            await self.es.delete(index=self.sessions_index, id=session_id)
        except ESNotFoundError:
            raise NotFoundError(f"Sessão não encontrada: {session_id}")

    async def add_document_to_context(self, session_id: str, document_id: str) -> dict:
        """Adiciona document_id ao contexto da sessão (sem duplicar).

        Valida que o documento existe no índice de documentos.
        Incrementa popularity_score do documento (+3, add_to_chat).
        """
        try:
            await self.es.get(index=settings.index_documentos_ifal_v2, id=document_id)
        except ESNotFoundError:
            raise NotFoundError(f"Documento não encontrado: {document_id}")

        session = await self._get_or_create_session(session_id)
        ids = list(session.get("context_document_ids", []))
        if document_id not in ids:
            ids.append(document_id)
            await self.es.update(
                index=self.sessions_index,
                id=session_id,
                body={"context_document_ids": ids},
            )

        try:
            await self.scoring.increment_score(
                index=settings.index_documentos_ifal_v2,
                doc_id=document_id,
                action="add_to_chat",
                root="ato",
            )
        except Exception as exc:
            logger.warning("Scoring increment falhou para %s: %s", document_id, exc)

        return {
            "session_id": session_id,
            "context_document_ids": ids,
            "context_artefato_ids": session.get("context_artefato_ids", []),
        }

    async def add_artefato_to_context(self, session_id: str, artefato_id: str) -> dict:
        """Adiciona artefato_id ao contexto da sessão (sem duplicar).

        Valida que o artefato existe. Incrementa popularity_score (+3, add_to_chat).
        """
        try:
            await self.es.get(index=settings.index_artefatos, id=artefato_id)
        except ESNotFoundError:
            raise NotFoundError(f"Artefato não encontrado: {artefato_id}")

        session = await self._get_or_create_session(session_id)
        ids = list(session.get("context_artefato_ids", []))
        if artefato_id not in ids:
            ids.append(artefato_id)
            await self.es.update(
                index=self.sessions_index,
                id=session_id,
                body={"context_artefato_ids": ids},
            )

        try:
            await self.scoring.increment_score(
                index=settings.index_artefatos,
                doc_id=artefato_id,
                action="add_to_chat",
                root="artefato",
            )
        except Exception as exc:
            logger.warning("Scoring increment falhou para %s: %s", artefato_id, exc)

        return {
            "session_id": session_id,
            "context_document_ids": session.get("context_document_ids", []),
            "context_artefato_ids": ids,
        }

    async def clear_context(self, session_id: str) -> dict:
        """Zera context_document_ids e context_artefato_ids da sessão."""
        try:
            await self.es.get(index=self.sessions_index, id=session_id)
        except ESNotFoundError:
            raise NotFoundError(f"Sessão não encontrada: {session_id}")

        await self.es.update(
            index=self.sessions_index,
            id=session_id,
            body={"context_document_ids": [], "context_artefato_ids": []},
        )
        return {
            "session_id": session_id,
            "context_document_ids": [],
            "context_artefato_ids": [],
        }

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    async def _get_or_create_session(self, session_id: str) -> dict:
        """Retorna sessão válida ou cria nova (se expirada ou inexistente)."""
        now = _now()
        try:
            doc = await self.es.get(index=self.sessions_index, id=session_id)
            source = doc["_source"]
            expires_raw = source.get("expires_at", "")
            expires_at = datetime.fromisoformat(expires_raw)
            if expires_at.tzinfo is None:
                expires_at = expires_at.replace(tzinfo=timezone.utc)
            if expires_at > now:
                return source
        except Exception:
            pass

        expires_at = now + timedelta(hours=settings.CHAT_SESSION_TTL_HOURS)
        session = {
            "session_id": session_id,
            "messages": [],
            "context_document_ids": [],
            "context_artefato_ids": [],
            "created_at": _iso(now),
            "last_activity_at": _iso(now),
            "expires_at": _iso(expires_at),
        }
        await self.es.index(index=self.sessions_index, id=session_id, body=session)
        return session

    async def _classify_intent(self, message: str) -> str:
        """Classifica intenção via Rasa. Fallback: ask_about_document."""
        try:
            result = await self.rasa.parse(message)
            return result.get("intent", {}).get("name", "ask_about_document")
        except Exception:
            return "ask_about_document"

    async def _build_context(
        self, message: str, session: dict, source_type: str | None = None
    ) -> str:
        """Monta contexto para o LLM a partir dos IDs de contexto da sessão."""
        contexts: list[str] = []

        for doc_id in session.get("context_document_ids", []):
            ctx = await self._context_for_doc(
                message,
                doc_id,
                index=settings.index_documentos_ifal_v2,
                chunks_index=settings.index_documentos_ifal_v2_chunks,
                root="ato",
            )
            if ctx:
                contexts.append(ctx)

        for artefato_id in session.get("context_artefato_ids", []):
            ctx = await self._context_for_doc(
                message,
                artefato_id,
                index=settings.index_artefatos,
                chunks_index=settings.index_artefatos_chunks,
                root="artefato",
            )
            if ctx:
                contexts.append(ctx)

        if contexts:
            return "\n\n---\n\n".join(contexts)

        # Sem contexto específico → busca livre nos chunks
        indices = self._resolve_chunks_indices(source_type)
        chunks = await self._hybrid_search(message, indices)
        return self._format_chunks(chunks)

    async def _context_for_doc(
        self,
        message: str,
        doc_id: str,
        index: str,
        chunks_index: str,
        root: str,
    ) -> str:
        """Retorna contexto de um documento: chunks via RRF ou attachment.content."""
        try:
            doc = await self.es.get(index=index, id=doc_id)
        except Exception:
            logger.warning("Documento %s não encontrado em %s", doc_id, index)
            return ""

        source = doc["_source"]
        has_chunks = source.get(root, {}).get("total_chunks", 0) > 0
        if has_chunks:
            chunks = await self._hybrid_search(message, [chunks_index], doc_id)
            return self._format_chunks(chunks)
        return source.get("attachment", {}).get("content", "")[:10000]

    async def _hybrid_search(
        self,
        query: str,
        indices: list[str],
        document_id: str | None = None,
    ) -> list[dict]:
        """Busca híbrida BM25 + kNN com RRF nativo do ES (1 chamada)."""
        filter_clause: dict | None = (
            {"term": {"parent_document_id": document_id}} if document_id else None
        )

        query_body: dict = {
            "bool": {
                "must": [{"match": {"content": query}}],
                "filter": [filter_clause],
            }
        } if filter_clause else {"match": {"content": query}}

        knn_clause: dict = {
            "field": "embedding_vector",
            "k": 5,
            "num_candidates": 50,
        }
        if filter_clause:
            knn_clause["filter"] = filter_clause

        try:
            query_vector = await self.embed.generate_embedding(query)
            knn_clause["query_vector"] = query_vector
            body: dict = {
                "query": query_body,
                "knn": knn_clause,
                "rank": {"rrf": {"window_size": 10}},
                "size": 5,
            }
        except Exception as exc:
            # RRF ou kNN indisponível (licença Basic) → BM25 puro
            logger.debug("kNN/RRF indisponível, usando BM25 puro: %s", exc)
            body = {"query": query_body, "size": 5}

        try:
            result = await self.es.search(index=",".join(indices), body=body)
            return result.get("hits", {}).get("hits", [])
        except Exception as exc:
            logger.warning("_hybrid_search falhou: %s", exc)
            return []

    def _resolve_chunks_indices(self, source_type: str | None) -> list[str]:
        if source_type == "documentos_ifal_v2":
            return [settings.index_documentos_ifal_v2_chunks]
        if source_type == "artefatos":
            return [settings.index_artefatos_chunks]
        return self._all_chunks_indices

    def _format_chunks(self, chunks: list[dict]) -> str:
        return "\n\n".join(
            h["_source"].get("content", "") for h in chunks if h.get("_source")
        )

    async def _append_and_renew(
        self, session_id: str, user_msg: str, assistant_msg: str
    ) -> None:
        """Adiciona as mensagens ao histórico e renova expires_at."""
        now = _now()
        expires_at = now + timedelta(hours=settings.CHAT_SESSION_TTL_HOURS)

        try:
            doc = await self.es.get(index=self.sessions_index, id=session_id)
            messages: list[dict] = doc["_source"].get("messages", [])
        except Exception:
            messages = []

        messages.append({"role": "user", "content": user_msg, "timestamp": _iso(now)})
        messages.append({"role": "assistant", "content": assistant_msg, "timestamp": _iso(now)})

        max_msgs = settings.CHAT_HISTORY_MAX_MESSAGES
        if len(messages) > max_msgs:
            messages = messages[-max_msgs:]

        await self.es.update(
            index=self.sessions_index,
            id=session_id,
            body={
                "messages": messages,
                "last_activity_at": _iso(now),
                "expires_at": _iso(expires_at),
            },
        )
