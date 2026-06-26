from abc import ABC, abstractmethod


class BaseLLMProvider(ABC):
    @abstractmethod
    async def generate_summary(self, text: str) -> str: ...

    @abstractmethod
    async def generate_embedding(self, text: str) -> list[float]: ...

    @abstractmethod
    async def extract_entities(self, text: str) -> list[dict]: ...

    @abstractmethod
    async def extract_keywords(self, text: str) -> list[str]: ...

    @abstractmethod
    async def generate_response(
        self, context: str, question: str, history: list[dict] | None = None
    ) -> str: ...

    @abstractmethod
    async def health_check(self) -> bool: ...

    async def enrich_document_combined(self, text: str) -> dict:
        """Retorna resumo + entidades + keywords em uma estrutura unificada.

        Implementação padrão faz 3 chamadas individuais. Providers podem sobrescrever
        para consolidar em uma única requisição e reduzir custo de tokens de entrada.
        """
        summary = await self.generate_summary(text)
        entities = await self.extract_entities(text)
        keywords = await self.extract_keywords(text)
        return {"resumo": summary, "entidades": entities, "keywords": keywords}
