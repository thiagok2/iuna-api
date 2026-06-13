# CLAUDE.md — IUNA API

**Projeto**: IUNA API  
**Stack**: Python 3.10+ · FastAPI · Elasticsearch · Rasa NLU · Claude (Anthropic)  
**Metodologia**: Spec-Driven Development (SDD)

---

## O que é este projeto

API REST generalista para processamento inteligente de documentos armazenados no Elasticsearch. Expõe serviços de resumo, vetorização, extração de entidades, segmentação (chunking) e chat conversacional baseado em RAG (Retrieval-Augmented Generation). Pode ser usada com qualquer tipo de documento (PDFs, textos, regulamentos, livros, etc.) — não é restrita a nenhuma instituição ou domínio específico.

---

## Metodologia: Spec-Driven Development (SDD)

**NUNCA implemente sem especificação prévia validada.** O fluxo obrigatório para qualquer feature nova, enhancement ou bugfix de complexidade média/alta é:

```
Requirements → Design → Tasks → Implementação
```

Os três artefatos vivem em `specs/` (ou no root para o projeto base):
- `requirements.md` — O quê (perspectiva de negócio, critérios EARS com SHALL)
- `design.md` — Como (arquitetura, interfaces, propriedades de corretude, error handling)
- `tasks.md` — Em que ordem (tasks atômicas < 2h, rastreáveis por requisito, com grafo de ondas)

**Exceção**: mudanças triviais (typo, renomear variável, ajustar padding) podem ser feitas diretamente.

Leia `metodologia-spec-driven-development.md` para o guia completo da metodologia.

### Quando o usuário pedir uma nova feature

1. Confirme se já existe spec em `specs/` para ela.
2. Se não existir: proponha criar requirements primeiro antes de escrever código.
3. Se o usuário quiser pular a spec: avise e confirme antes de continuar.

---

## Arquitetura em Camadas

```
Entrypoints (FastAPI Routers / CLI Batch)
         ↓
    Services (lógica de negócio)
         ↓
  Clients / Providers (infraestrutura)
  Elasticsearch   BaseLLMProvider → ClaudeProvider
  RasaClient                      → (GeminiProvider, etc.)
```

**Regra absoluta**: nenhuma camada "salta" outra. Controllers chamam Services; Services chamam Clients e Providers. Controllers nunca chamam Clients diretamente.

### Estrutura de arquivos alvo

```
app/
├── main.py                         # FastAPI init + inclusão de routers
├── config.py                       # Pydantic Settings (lê .env)
├── api/
│   ├── dependencies.py             # get_current_user, OAuth2PasswordBearer
│   ├── endpoints.py                # /health-check, /info (sem auth)
│   └── v1/
│       ├── auth.py                 # POST /auth/token
│       ├── summary.py              # POST /summary/generate
│       ├── vectorization.py        # POST /vectorization/generate
│       ├── entities.py             # POST /entities/generate
│       ├── chunking.py             # POST /chunking/generate
│       └── chat.py                 # POST /chat/message
├── core/
│   ├── config.py                   # (mover config.py para cá)
│   └── security.py                 # JWT, hash_password, verify_token
├── services/
│   ├── summary_service.py
│   ├── vector_service.py
│   ├── entities_service.py
│   ├── chunking_service.py
│   └── chat_service.py
├── clients/
│   ├── elasticsearch.py            # get, update, search_knn
│   └── rasa.py                     # parse_message
├── providers/llm/
│   ├── base.py                     # BaseLLMProvider (ABC) + LLMProviderError
│   ├── gemini.py                   # GeminiProvider (default)
│   ├── claude.py                   # ClaudeProvider
│   ├── ollama.py                   # OllamaProvider (local)
│   └── factory.py                  # LLMFactory.get_provider()
└── cli/
    └── batch.py                    # CLI Typer (--action, --ids)
```

---

## Estado Atual da Implementação

Scaffold básico funcional. O que **existe**:
- `app/main.py` — FastAPI init, root endpoint
- `app/config.py` — Pydantic Settings com todas as variáveis
- `app/api/endpoints.py` — `/health-check` e `/info`
- `tests/integration/test_api.py` — 3 testes dos endpoints básicos

O que **ainda não existe** (backlog completo em `tasks.md`):
- Módulos 0-8: core/security.py, auth, clients, providers, services, controllers v1, CLI, testes completos

---

## Provedores LLM

O projeto suporta três provedores, selecionados via `ACTIVE_LLM_PROVIDER`:

| Valor | Provedor | SDK | Uso |
|-------|----------|-----|-----|
| `gemini` | Google Gemini | `google-generativeai` | **Default** — cloud, melhor custo/benefício para embeddings |
| `claude` | Anthropic Claude | `anthropic` | Cloud alternativo |
| `ollama` | Ollama | `ollama` | Local, sem internet, privacidade máxima |

A interface `BaseLLMProvider` (ABC) define os contratos:
- `generate_summary(text: str) -> str`
- `generate_embedding(text: str) -> list[float]`
- `extract_entities(text: str) -> list[dict]`
- `generate_chat_response(prompt: str, context: str) -> str`

Toda falha de API deve ser relançada como `LLMProviderError`. Services nunca capturam exceções dos SDKs diretamente.

---

## Configuração do Ambiente

Copie `.env.example` para `.env` (nunca versione `.env`):

```env
PROJECT_NAME="IUNA API"
API_V1_STR="/api/v1"
SECRET_KEY=<gere com: python3 -c "import secrets; print(secrets.token_hex(32))">
JWT_ALGORITHM="HS256"
ACCESS_TOKEN_EXPIRE_MINUTES=60
ELASTICSEARCH_HOSTS="https://seu-elastic:9200"
ELASTICSEARCH_USER=elastic
ELASTICSEARCH_PASSWORD=<senha>
# LLM — escolher um provedor (default: gemini)
ACTIVE_LLM_PROVIDER="gemini"
GEMINI_API_KEY=<chave Google AI Studio>
CLAUDE_API_KEY=<chave Anthropic — opcional>
OLLAMA_BASE_URL="http://localhost:11434"
OLLAMA_MODEL="llama3"
RASA_API_URL="http://rasa:5005"
```

---

## Comandos Essenciais

```bash
# Rodar localmente
.venv/bin/uvicorn app.main:app --reload

# Rodar via Docker
docker-compose up

# Rodar testes
.venv/bin/pytest

# Rodar testes com verbose
.venv/bin/pytest -v

# Testes unitários apenas
.venv/bin/pytest tests/unit/

# Testes de integração apenas
.venv/bin/pytest tests/integration/
```

---

## Testes

- **Framework**: pytest 8.1+
- **TestClient**: via `conftest.py` (fixture `client`)
- **Estratégia**: mocks para Elasticsearch, Rasa e API do Claude em testes de integração
- **Separação**: `tests/unit/` para lógica pura; `tests/integration/` para endpoints com mocks de externos
- **Regra**: Services devem ser testáveis sem o ciclo de vida do FastAPI

---

## Segurança

- Credenciais exclusivamente via `.env`, nunca no código
- Todas as rotas `/api/v1/*` protegidas com `Depends(get_current_user)`, exceto `/health-check` e `/info`
- OAuth2 Password Flow com JWT HS256
- `.env` no `.gitignore` (já está)

---

## Índices Elasticsearch

**`artefatos`** — documento original com metadados:
```json
{ "attachment": { "content": "..." }, "artefato": { "titulo": "", "resumo": null, "embedding_vector": null, "entidades": [] } }
```

**`artefatos_chunks`** — fragmentos vetorizados:
```json
{ "parent_path_id": "<id_artefato>", "chunk_index": 0, "content": "...", "embedding_vector": [...] }
```

---

## Decisões Arquiteturais

| Decisão | Justificativa |
|---------|--------------|
| Provedor LLM via `BaseLLMProvider` ABC | Substituição sem alterar Services ou Controllers (RNF-01) |
| Rasa como microserviço separado | NLU isolado; re-treinamento sem deploy da API |
| Chunking delega embedding ao VectorService | Evitar duplicação de lógica; VectorService é a única fonte de embeddings |
| Elasticsearch externo (via env) | Flexibilidade entre instância local e produção sem mudança de código |
| CLI Batch com Typer acessa Services diretamente | Mesmo código de negócio, sem dependência do ciclo HTTP (RNF-04.1) |

---

## Referências

- `specs/starter/init/requirements.md` — Requisitos funcionais e não-funcionais
- `specs/starter/init/design.md` — Design técnico detalhado com modelos de dados
- `specs/starter/init/tasks.md` — Backlog granular com prioridades e status
- `kiro.md` — Guia arquitetural com diagramas e análise de chunking
- `metodologia-spec-driven-development.md` — Guia completo da metodologia SDD
