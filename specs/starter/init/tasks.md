# ✅ Backlog de Tarefas - IUNA API (adaptado para Claude)

**Projeto**: IUNA API  
**Instituição**: IFAL - Instituto Federal de Alagoas  
**Versão**: 1.0.0  
**Última Atualização**: 2026-05-28

---

> **Legenda de Status**:  
> `[ ]` Pendente  |  `[ / ]` Em progresso  |  `[x]` Concluído  |  `[-]` Bloqueado

> **Legenda de Prioridade**: 🔴 Crítico  |  🟡 Alta  |  🟢 Normal

---

## ⚙️ Setup Inicial do Projeto (pré-requisito de todos os módulos)

> Executar uma única vez antes de qualquer módulo. Não depende de nenhuma task de negócio.

- [ ] 🔴 Instalar dependências do projeto no virtualenv
  - `pip install -r requirements.txt`
  - Verificar que `.venv/bin/pytest` e `.venv/bin/uvicorn` funcionam

- [ ] 🔴 Criar `.env` local a partir do template abaixo (nunca versionar)
  ```env
  PROJECT_NAME="IUNA API"
  API_V1_STR="/api/v1"
  SECRET_KEY=                        # gerar: python3 -c "import secrets; print(secrets.token_hex(32))"
  JWT_ALGORITHM="HS256"
  ACCESS_TOKEN_EXPIRE_MINUTES=60
  ELASTICSEARCH_HOSTS="https://seu-elastic:9200"
  ELASTICSEARCH_USER=elastic
  ELASTICSEARCH_PASSWORD=
  # LLM — escolher um provedor (default: gemini)
  ACTIVE_LLM_PROVIDER="gemini"
  GEMINI_API_KEY=                    # chave Google AI Studio
  CLAUDE_API_KEY=                    # chave Anthropic (opcional)
  OLLAMA_BASE_URL="http://localhost:11434"   # apenas se usar Ollama local
  OLLAMA_MODEL="llama3"              # modelo padrão do Ollama
  RASA_API_URL="http://rasa:5005"
  ```

- [ ] 🔴 Criar `.env.example` na raiz com as mesmas chaves e valores em branco (para versionar como referência)

- [ ] 🔴 Confirmar que `.env` está no `.gitignore`
  - `grep '\.env' .gitignore`

- [ ] 🟡 Adicionar dependências ausentes ao `requirements.txt` conforme os módulos forem sendo implementados
  - `python-jose[cryptography]>=3.3.0` — JWT (Módulo 0)
  - `passlib[bcrypt]>=1.7.4` — hash de senhas (Módulo 0)
  - `python-multipart>=0.0.9` — OAuth2 form data (Módulo 0)
  - `typer>=0.12.0` — CLI Batch (Módulo 5)

- [ ] 🟢 Rodar os testes do scaffold para confirmar ambiente OK
  - `.venv/bin/pytest tests/ -v` — deve passar 3 testes

---

## 🏗️ Módulo 0 — Infraestrutura e Configuração Base

- [ ] 🔴 Criar arquivo `.env.example` com todas as variáveis listadas no `design.md`
- [ ] 🔴 Garantir que `.env` está listado no `.gitignore`
- [ ] 🔴 Atualizar `app/config.py` com todas as novas variáveis (`ELASTICSEARCH_*`, `CLAUDE_API_KEY`, `RASA_API_URL`, `SECRET_KEY`, `JWT_ALGORITHM`, `ACCESS_TOKEN_EXPIRE_MINUTES`)
- [ ] 🔴 Criar `app/core/security.py` com funções:
  - `create_access_token(data: dict, expires_delta: timedelta) -> str`
  - `verify_token(token: str) -> dict`
  - `hash_password(password: str) -> str`
  - `verify_password(plain: str, hashed: str) -> bool`
- [ ] 🟡 Criar `app/api/dependencies.py` com:
  - `get_current_user(token: str = Depends(oauth2_scheme)) -> User`
- [ ] 🟡 Criar `app/api/v1/auth.py` com:
  - `POST /auth/token` (recebe `username` e `password`, retorna JWT)
- [ ] 🟡 Atualizar `app/main.py` para incluir todos os routers de `v1/` sob o prefixo `/api/v1`
- [ ] 🟢 Criar `app/api/v1/__init__.py`

---

## 🔌 Módulo 1 — Clients de Infraestrutura

### Elasticsearch Client (`app/clients/elasticsearch.py`)
- [ ] 🔴 Criar classe `ElasticsearchClient` com:
  - `get(index: str, doc_id: str) -> dict` — busca documento por ID
  - `update(index: str, doc_id: str, fields: dict) -> None` — atualiza campos do documento (partial update)
  - `search_knn(index: str, vector: list[float], top_k: int, filter_ids: list[str] | None) -> list[dict]` — busca vetorial kNN no índice de chunks
- [ ] 🔴 Inicializar o client Elasticsearch com `ELASTICSEARCH_HOSTS`, `ELASTICSEARCH_USER` e `ELASTICSEARCH_PASSWORD` da config
- [ ] 🟡 Tratar erros de conexão com exceções customizadas

### Rasa Client (`app/clients/rasa.py`)
- [ ] 🔴 Criar classe `RasaClient` com:
  - `parse_message(text: str) -> dict` — envia mensagem ao `POST /model/parse` do Rasa e retorna `{ intent, entities }`
- [ ] 🟡 Inicializar o client com `RASA_API_URL` da config
- [ ] 🟡 Tratar erros de conexão e timeout com log de aviso

---

## 🤖 Módulo 2 — Providers de LLM

### Interface Base (`app/providers/llm/base.py`)
- [ ] 🔴 Criar classe abstrata `BaseLLMProvider(ABC)` com os métodos abstratos:
  - `generate_summary(text: str) -> str`
  - `generate_embedding(text: str) -> list[float]`
  - `extract_entities(text: str) -> list[dict]`
  - `generate_chat_response(prompt: str, context: str) -> str`
- [ ] 🔴 Criar exceção customizada `LLMProviderError(Exception)` no mesmo arquivo
  - _Requirements: RNF-01.1_

### Implementação Gemini — padrão (`app/providers/llm/gemini.py`)
- [ ] 🔴 Criar `GeminiProvider(BaseLLMProvider)` usando SDK `google-generativeai`
- [ ] 🔴 `generate_summary`: modelo `gemini-1.5-flash` com prompt de instrução de resumo em português
- [ ] 🔴 `generate_embedding`: modelo `models/text-embedding-004`
- [ ] 🔴 `extract_entities`: modelo `gemini-1.5-flash` com prompt estruturado retornando JSON `[{"texto": str, "categoria": str}]`
- [ ] 🔴 `generate_chat_response`: modelo `gemini-1.5-flash` com prompt RAG (contexto + pergunta)
- [ ] 🔴 Toda falha da API Gemini deve ser capturada e relançada como `LLMProviderError`
- [ ] 🟡 Adicionar `google-generativeai>=0.5.0` ao `requirements.txt`
  - _Requirements: RNF-01a.1, RNF-01a.2, RNF-01a.3_

### Implementação Claude — Anthropic (`app/providers/llm/claude.py`)
- [ ] 🔴 Criar `ClaudeProvider(BaseLLMProvider)` usando SDK `anthropic`
- [ ] 🔴 `generate_summary`: usar `messages.create` com prompt de resumo
- [ ] 🔴 `generate_embedding`: usar endpoint de embeddings compatível (Voyage AI via `anthropic` ou modelo externo)
- [ ] 🔴 `extract_entities`: `messages.create` com prompt estruturado retornando JSON de entidades
- [ ] 🔴 `generate_chat_response`: `messages.create` com prompt RAG
- [ ] 🔴 Toda falha da API Claude deve ser relançada como `LLMProviderError`
- [ ] 🟡 Confirmar que `anthropic>=1.0.0` está no `requirements.txt` (já está)
  - _Requirements: RNF-01a.4, RNF-01a.5_

### Implementação Ollama — local (`app/providers/llm/ollama.py`)
- [ ] 🔴 Criar `OllamaProvider(BaseLLMProvider)` usando SDK `ollama`
- [ ] 🔴 `__init__`: receber `base_url: str` e `model: str`; inicializar `ollama.Client(host=base_url)`
- [ ] 🔴 `generate_summary`: `client.generate(model=self.model, prompt=...)` com prompt de resumo
- [ ] 🔴 `generate_embedding`: `client.embeddings(model="nomic-embed-text", prompt=text)` — usar modelo de embedding dedicado
- [ ] 🔴 `extract_entities`: `client.generate` com prompt estruturado retornando JSON de entidades
- [ ] 🔴 `generate_chat_response`: `client.generate` com prompt RAG
- [ ] 🔴 Tratar `ConnectionError` (Ollama não disponível) relançando como `LLMProviderError` com mensagem clara
- [ ] 🟡 Adicionar `ollama>=0.2.0` ao `requirements.txt`
  - _Requirements: RNF-01a.6, RNF-01a.7, RNF-01a.8, RNF-01a.9_

### Factory (`app/providers/llm/factory.py`)
- [ ] 🔴 Criar `LLMFactory` com método estático `get_provider() -> BaseLLMProvider` selecionando o provedor via `ACTIVE_LLM_PROVIDER`
- [ ] 🔴 Suportar os valores `"gemini"` (default), `"claude"` e `"ollama"`
- [ ] 🔴 Lançar `ValueError` com mensagem descritiva para valores não suportados
  - _Requirements: RNF-01.2, RNF-01.4, RNF-01.5_

---

## 📝 Módulo 3 — Serviços de Processamento

### SummaryService (`app/services/summary_service.py`)
- [ ] 🔴 Criar `SummaryService` com:
  - `generate_from_text(text: str) -> str` — chama `LLMProvider.generate_summary`
  - `generate_from_path_id(path_id: str) -> dict` — busca texto no ES, gera resumo, atualiza `artefato.resumo` no ES, retorna resultado

### VectorService (`app/services/vector_service.py`)
- [ ] 🔴 Criar `VectorService` com:
  - `generate_from_text(text: str) -> list[float]` — chama `LLMProvider.generate_embedding`
  - `generate_from_path_id(path_id: str) -> dict` — busca texto no ES, gera vetor, atualiza `artefato.embedding_vector` no ES, retorna resultado

### EntitiesService (`app/services/entities_service.py`)
- [ ] 🔴 Criar `EntitiesService` com:
  - `extract_from_text(text: str) -> list[dict]` — chama `LLMProvider.extract_entities`
  - `extract_from_path_id(path_id: str) -> dict` — busca texto no ES, extrai entidades, atualiza `artefato.entidades` no ES, retorna resultado

### ChunkingService (`app/services/chunking_service.py`)
- [ ] 🔴 Criar `ChunkingService` com:
  - `split_text(text: str, chunk_size: int, overlap: int) -> list[str]` — algoritmo de divisão com sobreposição (sliding window)
  - `generate_from_text(text: str, chunk_size: int, overlap: int) -> list[dict]` — divide e retorna lista de chunks com índice
  - `generate_from_path_id(path_id: str, chunk_size: int, overlap: int) -> dict` — busca texto no ES, divide, vetoriza cada chunk via `VectorService`, indexa cada chunk no índice `artefatos_chunks` com `parent_path_id`, retorna lista de chunks criados

### ChatService (`app/services/chat_service.py`)
- [ ] 🔴 Criar `ChatService` com:
  - `process(message: str, session_id: str, path_ids: list[str] | None) -> dict`
    - Chama `RasaClient.parse_message(message)` para obter `intent` e `entities`
    - Se `intent == "ask_about_document"`: gera embedding da mensagem, busca chunks no ES via `search_knn`, monta contexto, chama `LLMProvider.generate_chat_response`
    - Se `intent == "chitchat"` ou outros: chama `LLMProvider.generate_chat_response` sem contexto
    - Retorna `{ response, session_id, intent }`

---

## 🛣️ Módulo 4 — Controllers (Routers FastAPI)

### Auth (`app/api/v1/auth.py`)
- [ ] 🟡 Implementar `POST /auth/token` com `OAuth2PasswordRequestForm`

### Summary (`app/api/v1/summary.py`)
- [ ] 🔴 Criar router com `POST /summary/generate`
- [ ] 🔴 Aceitar body `{ text: str | None, path_id: str | None }` (validar que ao menos um está presente)
- [ ] 🔴 Chamar `SummaryService.generate_from_text` ou `generate_from_path_id` conforme o input
- [ ] 🔴 Proteger rota com `Depends(get_current_user)`

### Vectorization (`app/api/v1/vectorization.py`)
- [ ] 🔴 Criar router com `POST /vectorization/generate`
- [ ] 🔴 Aceitar body `{ text: str | None, path_id: str | None }`
- [ ] 🔴 Chamar `VectorService` conforme o input
- [ ] 🔴 Proteger rota com `Depends(get_current_user)`

### Entities (`app/api/v1/entities.py`)
- [ ] 🔴 Criar router com `POST /entities/generate`
- [ ] 🔴 Aceitar body `{ text: str | None, path_id: str | None }`
- [ ] 🔴 Chamar `EntitiesService` conforme o input
- [ ] 🔴 Proteger rota com `Depends(get_current_user)`

### Chunking (`app/api/v1/chunking.py`)
- [ ] 🔴 Criar router com `POST /chunking/generate`
- [ ] 🔴 Aceitar body `{ text: str | None, path_id: str | None, chunk_size: int = 1000, chunk_overlap: int = 200 }`
- [ ] 🔴 Chamar `ChunkingService` conforme o input
- [ ] 🔴 Proteger rota com `Depends(get_current_user)`

### Chat (`app/api/v1/chat.py`)
- [ ] 🔴 Criar router com `POST /chat/message`
- [ ] 🔴 Aceitar body `{ message: str, session_id: str, path_ids: list[str] | None }`
- [ ] 🔴 Chamar `ChatService.process()`
- [ ] 🔴 Proteger rota com `Depends(get_current_user)`

---

## 📦 Módulo 5 — CLI / Batch (`app/cli/batch.py`)

- [ ] 🟡 Adicionar `typer` ao `requirements.txt`
- [ ] 🟡 Criar app CLI com `typer` e comando `process` com parâmetros:
  - `--action`: `vectorize-all` | `chunk-all` | `summarize-all` | `entities-all` | `process-docs`
  - `--ids`: lista de IDs separados por vírgula (opcional)
- [ ] 🟡 Implementar lógica de busca de IDs pendentes no Elasticsearch (documentos onde o campo alvo é `null`)
- [ ] 🟡 Implementar iteração e chamada dos Services correspondentes para cada ID

---

## 🦾 Módulo 6 — Rasa (Projeto Separado `./rasa/`)

- [ ] 🟡 Criar estrutura de diretórios `./rasa/` com `config.yml`, `domain.yml`, `endpoints.yml`, `data/`
- [ ] 🟡 Criar `rasa/data/nlu.yml` com exemplos de intenções generalistas:
  - `ask_about_document` (mínimo 20 exemplos variados)
  - `chitchat` (mínimo 10 exemplos)
  - `encerrar` (mínimo 5 exemplos)
  - `ajuda` (mínimo 5 exemplos)
- [ ] 🟡 Criar `rasa/domain.yml` declarando todas as intenções
- [ ] 🟡 Criar `rasa/config.yml` com pipeline NLU (`WhitespaceTokenizer`, `DIETClassifier`)
- [ ] 🟡 Treinar o modelo inicial via Docker: `docker-compose run --rm rasa rasa train`

---

## 🧪 Módulo 7 — Testes

### Testes Unitários (`tests/unit/`)
- [ ] 🟡 `test_chunking_service.py`: testar `split_text` com diferentes `chunk_size` e `overlap`
- [ ] 🟡 `test_vector_service.py`: testar `generate_from_text` com mock do `LLMProvider`
- [ ] 🟡 `test_summary_service.py`: testar `generate_from_text` com mock do `LLMProvider`
- [ ] 🟡 `test_entities_service.py`: testar `extract_from_text` com mock do `LLMProvider`

### Testes de Integração (`tests/integration/`)
- [ ] 🟡 `test_summary_endpoint.py`: testar `POST /summary/generate` com texto e com `path_id` (mock ES e LLM)
- [ ] 🟡 `test_vectorization_endpoint.py`: testar `POST /vectorization/generate`
- [ ] 🟡 `test_entities_endpoint.py`: testar `POST /entities/generate`
- [ ] 🟡 `test_chunking_endpoint.py`: testar `POST /chunking/generate` com `path_id` (verificar indexação de chunks no ES mockado)
- [ ] 🟡 `test_chat_endpoint.py`: testar `POST /chat/message` com mock do Rasa e do ES
- [ ] 🟢 `test_api.py`: garantir que `/health-check` e `/info` retornam 200 sem autenticação

---

## 📄 Módulo 8 — Dependências (`requirements.txt`)

- [ ] 🔴 Garantir versões fixas das dependências principais:
  - `fastapi>=0.110.0`
  - `uvicorn>=0.28.0`
  - `pydantic-settings>=2.2.0`
  - `python-jose[cryptography]>=3.3.0`   — JWT
  - `passlib[bcrypt]>=1.7.4`             — hashing de senhas
  - `python-multipart>=0.0.9`            — OAuth2 form data
  - `elasticsearch>=8.12.0`             — client Elasticsearch
  - `httpx>=0.27.0`                      — client HTTP (Rasa)
  - `google-generativeai>=0.5.0`         — Gemini SDK (provedor padrão)
  - `anthropic>=1.0.0`                   — Claude SDK
  - `ollama>=0.2.0`                      — Ollama SDK (LLM local)
  - `typer>=0.12.0`                      — CLI Batch
  - `pytest>=8.1.0`                      — testes
