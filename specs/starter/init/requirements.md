# 📋 Requisitos - IUNA API (adaptado para Claude)

**Projeto**: IUNA API  
**Instituição**: IFAL - Instituto Federal de Alagoas  
**Versão**: 1.0.0  
**Última Atualização**: 2026-05-28

---

## 1. Visão Geral

A IUNA API é uma API REST construída com FastAPI destinada ao processamento inteligente de documentos institucionais (editais, portarias, regulamentos, livros) armazenados no Elasticsearch. Ela expõe serviços de resumo, vetorização, extração de entidades, segmentação (chunking) e chat conversacional baseado em recuperação de contexto (RAG), integrado com o serviço de NLU do Rasa e o LLM Claude (Anthropic).

---

## 2. Requisitos Funcionais

### RF-01 — Autenticação e Autorização
- **RF-01.1**: A API deve autenticar usuários via endpoint de login retornando um token JWT.
- **RF-01.2**: Todas as rotas sob `/api/v1/` (exceto `/health-check` e `/info`) devem exigir token JWT válido no cabeçalho `Authorization: Bearer <token>`.
- **RF-01.3**: O token deve ter tempo de expiração configurável via variável de ambiente.

---

### RF-02 — Módulo de Resumo (`/api/v1/summary`)
- **RF-02.1**: O endpoint `POST /api/v1/summary/generate` deve aceitar texto bruto no corpo da requisição e retornar um resumo gerado por LLM.
- **RF-02.2**: O endpoint deve aceitar, alternativamente, um `path_id` (ID do documento no Elasticsearch). Neste caso, o texto é buscado do campo `_source.attachment.content` do índice `artefatos`.
- **RF-02.3**: Quando o processamento ocorrer via `path_id`, o resumo gerado deve ser gravado de volta no Elasticsearch, no campo `_source.artefato.resumo` do documento correspondente.
- **RF-02.4**: O resumo gerado deve sempre ser retornado no corpo da resposta JSON da requisição.
- **RF-02.5**: O serviço deve poder ser acionado via CLI/Batch para processar múltiplos documentos em lote.

---

### RF-03 — Módulo de Vetorização (`/api/v1/vectorization`)
- **RF-03.1**: O endpoint `POST /api/v1/vectorization/generate` deve aceitar texto bruto e retornar o vetor de embeddings gerado pela API de embeddings do LLM configurado.
- **RF-03.2**: O endpoint deve aceitar, alternativamente, um `path_id`. Neste caso, o texto é buscado do Elasticsearch.
- **RF-03.3**: Quando processado via `path_id`, o vetor gerado deve ser gravado no campo `_source.artefato.embedding_vector` do documento no Elasticsearch.
- **RF-03.4**: O vetor gerado deve sempre ser retornado no corpo da resposta JSON.
- **RF-03.5**: O serviço deve poder ser acionado via CLI/Batch.

---

### RF-04 — Módulo de Extração de Entidades (`/api/v1/entities`)
- **RF-04.1**: O endpoint `POST /api/v1/entities/generate` deve aceitar texto bruto e retornar uma lista de entidades nomeadas extraídas (nome, categoria) pelo LLM.
- **RF-04.2**: Categorias de entidades esperadas incluem: `DOCUMENTO`, `ORGANIZACAO`, `REGULAMENTO`, `DATA`, `PESSOA`, `LOCAL`.
- **RF-04.3**: O endpoint deve aceitar, alternativamente, um `path_id`. Neste caso, o texto é buscado do Elasticsearch.
- **RF-04.4**: Quando processado via `path_id`, as entidades extraídas devem ser gravadas no campo `_source.artefato.entidades` do documento no Elasticsearch.
- **RF-04.5**: As entidades devem sempre ser retornadas no corpo da resposta JSON.
- **RF-04.6**: O serviço deve poder ser acionado via CLI/Batch.

---

### RF-05 — Módulo de Segmentação (`/api/v1/chunking`)
- **RF-05.1**: O endpoint `POST /api/v1/chunking/generate` deve aceitar texto bruto e retornar a lista de blocos (chunks) gerada.
- **RF-05.2**: O endpoint deve aceitar parâmetros opcionais `chunk_size` (padrão: 1000 caracteres) e `chunk_overlap` (padrão: 200 caracteres).
- **RF-05.3**: O endpoint deve aceitar, alternativamente, um `path_id`. Neste caso, o texto é buscado do Elasticsearch.
- **RF-05.4**: Quando processado via `path_id`, cada chunk deve ser vetorizado individualmente e indexado no índice `artefatos_chunks` do Elasticsearch, com os campos:
  - `parent_path_id`: ID do documento pai em `artefatos`.
  - `chunk_index`: Posição sequencial do bloco.
  - `content`: Texto do bloco.
  - `embedding_vector`: Vetor semântico do bloco gerado pelo LLM.
- **RF-05.5**: O ChunkingService deve internamente invocar o VectorService para gerar os embeddings de cada chunk.
- **RF-05.6**: O serviço deve poder ser acionado via CLI/Batch.

---

### RF-06 — Módulo de Chat (`/api/v1/chat`)
- **RF-06.1**: O endpoint `POST /api/v1/chat/message` deve aceitar `message` (texto do usuário) e `session_id` (identificador de sessão).
- **RF-06.2**: Opcionalmente, deve aceitar uma lista de `path_ids` para restringir o contexto do RAG a documentos específicos.
- **RF-06.3**: O ChatService deve enviar a mensagem ao **Rasa Service** via `POST /model/parse` e extrair a intenção e entidades retornadas.
- **RF-06.4**: Se a intenção classificada for do tipo `ask_about_document`, o serviço deve realizar uma busca vetorial (kNN) no índice `artefatos_chunks` do Elasticsearch para recuperar os chunks semanticamente relevantes.
- **RF-06.5**: O contexto composto pelos chunks recuperados, pelo histórico de sessão e pela mensagem do usuário deve ser enviado ao LLM (Claude) para geração da resposta final.
- **RF-06.6**: Se a intenção for `chitchat` ou conversa geral, a mensagem deve ser enviada diretamente ao LLM sem busca no Elasticsearch.
- **RF-06.7**: A resposta gerada deve ser retornada no corpo da resposta JSON.

---

### RF-07 — Processamento em Lote (CLI/Batch)
- **RF-07.1**: O módulo `app/cli/batch.py` deve aceitar o parâmetro `--action` com os valores: `vectorize-all`, `chunk-all`, `summarize-all`, `entities-all`, `process-docs`.
- **RF-07.2**: O parâmetro `--ids` opcional deve permitir especificar uma lista de IDs do Elasticsearch separados por vírgula.
- **RF-07.3**: Toda a lógica de processamento dos serviços (Summary, Vector, Entities, Chunking) deve ser executável de forma independente do servidor web FastAPI.

---

## 3. Requisitos Não-Funcionais

### RNF-01 — Flexibilidade de LLM
- **RNF-01.1**: A integração com o LLM deve ser feita exclusivamente através da interface abstrata `BaseLLMProvider`.
- **RNF-01.2**: A implementação ativa do provedor deve ser selecionada por variável de ambiente `ACTIVE_LLM_PROVIDER`.
- **RNF-01.3**: A substituição de um provedor por outro não deve exigir alterações nos Services ou Controllers.
- **RNF-01.4**: O provedor padrão (default) SHALL ser `gemini`.
- **RNF-01.5**: O projeto SHALL suportar três provedores: `gemini` (cloud, default), `claude` (cloud, Anthropic) e `ollama` (local, auto-hospedado).

### RNF-01a — Provedores suportados

**Gemini (Google) — provedor padrão**
- **RNF-01a.1**: O repositório SHALL fornecer `GeminiProvider` implementando `BaseLLMProvider` via SDK `google-generativeai`.
- **RNF-01a.2**: O `GeminiProvider` SHALL autenticar usando a variável `GEMINI_API_KEY`.
- **RNF-01a.3**: O `GeminiProvider` SHALL usar `gemini-1.5-flash` para geração de texto e `models/text-embedding-004` para embeddings.

**Claude (Anthropic)**
- **RNF-01a.4**: O repositório SHALL fornecer `ClaudeProvider` implementando `BaseLLMProvider` via SDK `anthropic`.
- **RNF-01a.5**: O `ClaudeProvider` SHALL autenticar usando a variável `CLAUDE_API_KEY`.

**Ollama (local)**
- **RNF-01a.6**: O repositório SHALL fornecer `OllamaProvider` implementando `BaseLLMProvider` via SDK `ollama`.
- **RNF-01a.7**: O `OllamaProvider` SHALL conectar ao servidor Ollama via `OLLAMA_BASE_URL` (default: `http://localhost:11434`).
- **RNF-01a.8**: O modelo Ollama a usar SHALL ser configurável via `OLLAMA_MODEL` (default: `llama3`).
- **RNF-01a.9**: O `OllamaProvider` SHALL funcionar sem conexão com a internet, processando localmente.

### RNF-01-Config — Variáveis de configuração obrigatórias (LLM/Infra)
- **RNF-01-Config.1**: O arquivo de configuração (`app/config.py`) SHALL expor as variáveis:
  `ACTIVE_LLM_PROVIDER`, `GEMINI_API_KEY`, `CLAUDE_API_KEY`, `OLLAMA_BASE_URL`, `OLLAMA_MODEL`,
  `ELASTICSEARCH_HOSTS`, `ELASTICSEARCH_USER`, `ELASTICSEARCH_PASSWORD`,
  `RASA_API_URL`, `SECRET_KEY`, `JWT_ALGORITHM`, `ACCESS_TOKEN_EXPIRE_MINUTES`.
- **RNF-01-Config.2**: O projeto SHALL fornecer um `.env.example` com todas as variáveis acima e descrições curtas.

### RNF-02 — Segurança
- **RNF-02.1**: Credenciais (chaves de API, senhas do Elasticsearch, chaves JWT) nunca devem estar no código-fonte; devem ser lidas do arquivo `.env`.
- **RNF-02.2**: O arquivo `.env` não deve ser versionado no repositório (deve estar no `.gitignore`).
- **RNF-02.3**: A comunicação com o Elasticsearch deve suportar autenticação via usuário/senha.

### RNF-03 — Conteinerização
- **RNF-03.1**: O projeto deve ser conteinerizado com Docker.
- **RNF-03.2**: Um arquivo `docker-compose.yml` deve orquestrar os serviços FastAPI e Rasa.
- **RNF-03.3**: O Elasticsearch pode ser apontado para uma instância externa via variáveis de ambiente, sem necessidade de subir um container local.

### RNF-04 — Testabilidade
- **RNF-04.1**: Os Services devem ser testáveis de forma isolada, sem dependência do ciclo de vida do FastAPI.
- **RNF-04.2**: Os testes de integração devem usar mocks para chamadas externas (Elasticsearch, Rasa, Claude API).
- **RNF-04.3**: O projeto deve conter testes unitários e de integração separados.

### RNF-05 — Rastreabilidade
- **RNF-05.1**: O Rasa deve ser treinado com intenções generalistas voltadas à consulta de documentos, sem necessidade de re-treinamento para cada novo PDF adicionado.
- **RNF-05.2**: O índice `artefatos_chunks` deve sempre conter a referência ao documento pai via `parent_path_id`.
