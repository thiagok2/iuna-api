# 🏗️ Design Técnico - IUNA API (adaptado para Claude)

**Projeto**: IUNA API  
**Instituição**: IFAL - Instituto Federal de Alagoas  
**Versão**: 1.0.0  
**Última Atualização**: 2026-05-28

---

## 1. Visão Geral da Arquitetura

A IUNA API adota uma arquitetura em camadas com separação clara entre responsabilidades. Nenhuma camada "salta" outra: Controllers chamam Services, que chamam Clients e Providers.

```
┌──────────────────────────────────────────────┐
│                   ENTRYPOINTS                │
│  ┌─────────────────┐  ┌────────────────────┐ │
│  │  FastAPI Routers│  │   CLI / Batch      │ │
│  └────────┬────────┘  └─────────┬──────────┘ │
└───────────┼─────────────────────┼────────────┘
            │                     │
┌───────────▼─────────────────────▼────────────┐
│                  SERVICES                    │
│  SummaryService  │  VectorService            │
│  EntitiesService │  ChunkingService          │
│  ChatService                                 │
└────────────┬──────────────┬──────────────────┘
             │              │
     ┌───────▼──────┐ ┌─────▼──────────────────┐
     │   CLIENTS    │ │       PROVIDERS         │
     │ Elasticsearch│ │  BaseLLMProvider        │
     │ RasaClient   │ │  └─ ClaudeProvider      │
     └──────────────┘ │  └─ (OpenAI, etc.)      │
                      │  LLMFactory             │
                      └─────────────────────────┘
```

---

## 2. Estrutura de Arquivos

```text
iuna-api/
├── app/
│   ├── __init__.py
│   ├── main.py                     # Inicialização do FastAPI e inclusão dos routers
│   ├── api/
│   │   ├── __init__.py
│   │   ├── dependencies.py         # get_current_user, OAuth2PasswordBearer
│   │   ├── endpoints.py            # /health-check, /info (sem autenticação)
│   │   └── v1/
│   │       ├── __init__.py
│   │       ├── auth.py             # POST /auth/token (login)
│   │       ├── summary.py          # POST /summary/generate
│   │       ├── vectorization.py    # POST /vectorization/generate
│   │       ├── entities.py         # POST /entities/generate
│   │       ├── chunking.py         # POST /chunking/generate
│   │       └── chat.py             # POST /chat/message
│   ├── core/
│   │   ├── __init__.py
│   │   ├── config.py               # Pydantic Settings (leitura de .env)
│   │   └── security.py             # create_access_token, verify_token, hash_password
│   ├── services/
│   │   ├── __init__.py
│   │   ├── summary_service.py
│   │   ├── vector_service.py
│   │   ├── entities_service.py
│   │   ├── chunking_service.py
│   │   └── chat_service.py
│   ├── clients/
│   │   ├── __init__.py
│   │   ├── elasticsearch.py        # ElasticsearchClient (get, update, search_knn)
│   │   └── rasa.py                 # RasaClient (parse_message)
│   ├── providers/
│   │   └── llm/
│   │       ├── __init__.py
│   │       ├── base.py             # BaseLLMProvider (ABC)
│   │       ├── gemini.py           # GeminiProvider (padrão)
│   │       ├── claude.py           # ClaudeProvider
│   │       ├── ollama.py           # OllamaProvider (local)
│   │       └── factory.py          # LLMFactory.get_provider()
│   └── cli/
│       ├── __init__.py
│       └── batch.py                # CLI Typer com actions de processamento em lote
├── rasa/                           # Projeto Rasa separado
│   ├── config.yml
│   ├── domain.yml
│   ├── endpoints.yml
│   ├── models/                     # Modelos treinados (gerados pelo rasa train)
│   └── data/
│       ├── nlu.yml                 # Exemplos de intenções para treinamento
│       └── stories.yml             # Fluxos de conversa
├── tests/
│   ├── conftest.py
│   ├── unit/
│   │   ├── test_chunking_service.py
│   │   ├── test_vector_service.py
│   │   └── test_summary_service.py
│   └── integration/
│       ├── test_api.py
│       ├── test_summary_endpoint.py
│       ├── test_vectorization_endpoint.py
│       ├── test_entities_endpoint.py
│       ├── test_chunking_endpoint.py
│       └── test_chat_endpoint.py
├── Dockerfile
├── docker-compose.yml
├── .env.example                    # Modelo do .env (sem dados sensíveis)
├── .gitignore
├── requirements.txt
├── pyproject.toml
├── README.md
├── kiro.md
├── requirements.md                 # Este documento
├── design.md                       # Documento de design técnico
└── tasks.md                        # Backlog de tarefas granulares
```

---

## 3. Configuração (`app/core/config.py`)

Todas as configurações são lidas de variáveis de ambiente via `pydantic-settings`:

| Variável | Tipo | Descrição |
| :--- | :--- | :--- |
| `PROJECT_NAME` | `str` | Nome do projeto (default: "IUNA API") |
| `API_V1_STR` | `str` | Prefixo da API (default: "/api/v1") |
| `SECRET_KEY` | `str` | Chave secreta para assinatura de JWT |
| `JWT_ALGORITHM` | `str` | Algoritmo JWT (default: "HS256") |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | `int` | Expiração do token em minutos |
| `ELASTICSEARCH_HOSTS` | `str` | URL do Elasticsearch |
| `ELASTICSEARCH_USER` | `str` | Usuário do Elasticsearch |
| `ELASTICSEARCH_PASSWORD` | `str` | Senha do Elasticsearch |
| `ACTIVE_LLM_PROVIDER` | `str` | Provedor ativo: `gemini` (default), `claude`, `ollama` |
| `GEMINI_API_KEY` | `str` | Chave de API do Gemini (Google) |
| `CLAUDE_API_KEY` | `str` | Chave de API do Claude (Anthropic) |
| `OLLAMA_BASE_URL` | `str` | URL do servidor Ollama (default: `http://localhost:11434`) |
| `OLLAMA_MODEL` | `str` | Modelo Ollama a usar (default: `llama3`) |
| `RASA_API_URL` | `str` | URL do serviço Rasa (default: "http://rasa:5005") |

---

## 4. Modelagem de Dados no Elasticsearch

### 4.1 Índice `artefatos` (Documentos Originais)

```json
{
  "_index": "artefatos",
  "_id": "<elasticsearch_id>",
  "_source": {
    "attachment": {
      "content": "<texto extraído do PDF>"
    },
    "artefato": {
      "titulo": "string",
      "path_id": "string",
      "resumo": "string | null",
      "embedding_vector": "[float] | null",
      "entidades": [
        { "texto": "string", "categoria": "string" }
      ]
    }
  }
}
```

### 4.2 Índice `artefatos_chunks` (Fragmentos Vetorizados)

```json
{
  "_index": "artefatos_chunks",
  "_id": "chunk_<parent_id>_<index>",
  "_source": {
    "parent_path_id": "<_id do documento em artefatos>",
    "chunk_index": 0,
    "content": "string",
    "embedding_vector": "[float]"
  }
}
```

---

## 5. Interface de LLM (`app/providers/llm/base.py`)

```python
from abc import ABC, abstractmethod

class BaseLLMProvider(ABC):
    @abstractmethod
    def generate_summary(self, text: str) -> str: ...

    @abstractmethod
    def generate_embedding(self, text: str) -> list[float]: ...

    @abstractmethod
    def extract_entities(self, text: str) -> list[dict]: ...

    @abstractmethod
    def generate_chat_response(self, prompt: str, context: str) -> str: ...
```

### Factory (`app/providers/llm/factory.py`)

```python
from app.core.config import settings
from app.providers.llm.base import BaseLLMProvider
from app.providers.llm.gemini import GeminiProvider
from app.providers.llm.claude import ClaudeProvider
from app.providers.llm.ollama import OllamaProvider

class LLMFactory:
    @staticmethod
    def get_provider() -> BaseLLMProvider:
        if settings.ACTIVE_LLM_PROVIDER == "gemini":
            return GeminiProvider(api_key=settings.GEMINI_API_KEY)
        if settings.ACTIVE_LLM_PROVIDER == "claude":
            return ClaudeProvider(api_key=settings.CLAUDE_API_KEY)
        if settings.ACTIVE_LLM_PROVIDER == "ollama":
            return OllamaProvider(base_url=settings.OLLAMA_BASE_URL, model=settings.OLLAMA_MODEL)
        raise ValueError(f"Provedor LLM não suportado: {settings.ACTIVE_LLM_PROVIDER}")
```

### Decisões de design dos provedores

| Decisão | Alternativas | Justificativa |
|---------|-------------|---------------|
| Gemini como default | Claude, Ollama | Melhor custo-benefício para embeddings e geração; `text-embedding-004` é state-of-the-art para RAG |
| Ollama via SDK `ollama` | HTTP direto, openai-compat | SDK oficial mais idiomático; suporte nativo a streaming e modelos locais |
| Cada provider lança `LLMProviderError` | Exceções nativas dos SDKs | Isola Services de detalhes de cada SDK; facilita retry e fallback |
| Ollama embeddings via `nomic-embed-text` | Usar modelo de chat para embeddings | Modelos de embedding especializados têm melhor qualidade vetorial |

---

## 6. Fluxo de Dados — Endpoints de Processamento

### 6.1 Fluxo com `path_id`
```
Controller → Service → ElasticsearchClient.get(path_id)
                     → LLMProvider.generate_*(content)
                     → ElasticsearchClient.update(path_id, resultado)
                     → Retorna JSON com resultado
```

### 6.2 Fluxo com texto no corpo
```
Controller → Service → LLMProvider.generate_*(text)
                     → Retorna JSON com resultado
```

---

## 7. Fluxo de Dados — Chat

```
POST /chat/message
  → ChatService.process(message, session_id, path_ids)
    → RasaClient.parse_message(message)
      ← { intent, entities }
    → [Se intent == "ask_about_document"]
      → ElasticsearchClient.search_knn(embedding, path_ids)
        ← chunks relevantes
      → LLMProvider.generate_chat_response(message, context=chunks)
    → [Se intent == "chitchat"]
      → LLMProvider.generate_chat_response(message, context="")
  ← { response, session_id }
```

---

## 8. Treinamento do Rasa NLU

O Rasa é treinado com intenções **generalistas**, sem depender de dados específicos de nenhum PDF. Novos documentos não exigem re-treinamento.

### Intenções Planejadas (`rasa/data/nlu.yml`)

| Intenção | Exemplos de frases |
| :--- | :--- |
| `ask_about_document` | "O que diz sobre X?", "Explique Y", "Como funciona Z?" |
| `chitchat` | "Olá", "Bom dia", "Quem é você?" |
| `encerrar` | "Até logo", "Tchau", "Encerrar" |
| `ajuda` | "Preciso de ajuda", "Não entendi", "Como usar?" |

---

## 9. Infraestrutura Docker

### Serviços no `docker-compose.yml`

| Serviço | Imagem | Porta | Responsabilidade |
| :--- | :--- | :--- | :--- |
| `web` | Build local (`Dockerfile`) | `8000` | IUNA API (FastAPI) |
| `rasa` | `rasa/rasa:3.6.15-full` | `5005` | NLU e Dialogue Manager |
| `elasticsearch` | `elasticsearch:8.12.2` (opcional) | `9200` | Banco de Dados de Documentos |

> O Elasticsearch pode ser substituído por uma instância externa ajustando apenas as variáveis de ambiente no `.env`, sem alteração na aplicação.

---

## 10. Segurança

- **Autenticação**: OAuth2 Password Flow com JWT (HS256).
- **Dependência FastAPI**: `Depends(get_current_user)` em todas as rotas protegidas.
- **Secrets**: Carregados exclusivamente do arquivo `.env` (nunca no código).
- **CORS**: Configurável via middleware do FastAPI para ambientes de produção.
