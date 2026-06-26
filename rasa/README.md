# Rasa NLU no IUNA API

## O que é o Rasa?

Rasa é um framework open-source para processamento de linguagem natural (NLU — *Natural Language Understanding*). Ele recebe um texto em linguagem natural e responde com a **intenção** (*intent*) que aquele texto expressa.

| Texto recebido | Intent identificada |
|---|---|
| "quais são os prazos do edital?" | `ask_about_document` |
| "bom dia, tudo bem?" | `chitchat` |
| "qual a penalidade prevista na resolução?" | `ask_about_document` |
| "obrigado!" | `chitchat` |

Ele **não** gera respostas — só classifica. Quem gera a resposta é o LLM (Gemini/Claude/Ollama).

---

## Por que o IUNA usa Rasa?

O chat RAG precisa decidir **o que fazer** com cada mensagem antes de chamar o LLM:

```
Usuário manda mensagem
        │
        ▼
   [Rasa classifica]
        │
   ┌────┴────┐
   │         │
chitchat   ask_about_document
   │         │
   ▼         ▼
LLM sem   LLM com contexto de
contexto  documentos (RAG)
```

- **`chitchat`** → resposta livre, sem buscar documentos. Não faz sentido buscar chunks do ES para "bom dia".
- **`ask_about_document`** → aciona o pipeline RAG completo: busca chunks no ES, monta contexto, passa pro LLM.

Sem essa classificação, o chat tentaria fazer RAG em toda mensagem — inclusive saudações.

---

## Arquitetura no projeto

```
ChatService.handle_message()
    │
    ├─→ RasaClient.parse(message)   ← POST http://rasa:5005/model/parse
    │       │
    │   Retorna {"intent": {"name": "ask_about_document", "confidence": 0.95}}
    │
    ├─[chitchat]→ LLM.generate_response(context="", ...)
    │
    └─[ask_about_document]→ busca ES → LLM.generate_response(context=chunks, ...)
```

O `RasaClient` em `app/clients/rasa_client.py` faz um POST simples para a API HTTP do Rasa. Se o Rasa estiver offline ou a confidence for < 0.6, retorna `ask_about_document` automaticamente — o chat nunca quebra.

---

## Estrutura dos arquivos

```
rasa/
├── nlu.yml        # Dados de treino: exemplos de cada intent  ← você edita aqui
├── config.yml     # Pipeline de NLU (como processar o texto)
├── domain.yml     # Declaração das intents conhecidas         ← você edita aqui
├── endpoints.yml  # Configuração de serviços externos
└── models/        # Modelos treinados (gerado após treino, não versionado)
```

A pasta `rasa/` local **é** o que roda dentro do container — o Docker monta ela como volume (`./rasa:/app`). Editar um arquivo localmente é editar o arquivo que o container usa.

---

## Como rodar o Rasa

### `make start` sobe o Rasa?

**Não.** `make start` roda apenas a API FastAPI localmente via uvicorn. O Rasa é um container Docker separado e opcional.

### O Rasa é obrigatório?

**Não.** Se o Rasa estiver offline, a API continua funcionando — o `RasaClient` faz fallback para `ask_about_document` automaticamente. O `GET /api/v1/health` mostrará `rasa: "offline"`, mas o chat responde normalmente.

### Fluxo para usar o Rasa

**Passo 1 — Treinar o modelo (só precisa fazer na primeira vez e após mudanças nos arquivos)**

```bash
# Na raiz do projeto
docker-compose --profile rasa run --rm rasa rasa train
```

Isso cria `rasa/models/nlu-YYYYMMDD-HHMMSS-*.tar.gz`. Sem esse arquivo, o servidor Rasa não sobe.

**Passo 2 — Subir o servidor**

```bash
docker-compose --profile rasa up rasa
```

O container sobe, carrega o modelo treinado e expõe a API em `localhost:5005`.

**Passo 3 — Confirmar que está rodando**

```bash
curl http://localhost:5005/
# Deve retornar: {"version": "3.6.x", ...}

curl -X POST http://localhost:5005/model/parse \
  -H "Content-Type: application/json" \
  -d '{"text": "quais são os prazos do edital?"}'
# intent.name deve ser "ask_about_document"
```

### Subir a API junto com o Rasa (docker-compose completo)

```bash
# Sobe API + Rasa juntos
docker-compose --profile rasa up

# Ou em background
docker-compose --profile rasa up -d
```

> **Atenção ao `RASA_API_URL`**: O `.env` tem `RASA_API_URL=http://rasa:5005` — isso usa o nome do serviço Docker e só funciona quando a API também roda dentro do docker-compose. Se você roda a API localmente com `make start` e o Rasa via docker-compose, altere para `RASA_API_URL=http://localhost:5005` no `.env`.

| Situação | `RASA_API_URL` correto |
|---|---|
| API via `make start` + Rasa via docker-compose | `http://localhost:5005` |
| API + Rasa ambos via docker-compose | `http://rasa:5005` (padrão) |

### Não precisa de "Reopen in Container"

O Rasa tem seu próprio container gerenciado pelo docker-compose. O "Reopen in Container" do VS Code é para o devcontainer da API, não tem relação com o Rasa.

---

## Ciclo de edição → treino → uso

```
1. Parar o Rasa (se estiver rodando)
   docker-compose --profile rasa stop rasa

2. Editar os arquivos
   rasa/nlu.yml    ← adicionar/modificar exemplos
   rasa/domain.yml ← declarar novas intents

3. Retreinar
   docker-compose --profile rasa run --rm rasa rasa train

4. Subir novamente
   docker-compose --profile rasa up rasa
```

O treino dura ~1-3 minutos e sobrescreve o modelo em `rasa/models/`. Você pode deixar múltiplos modelos na pasta — o Rasa usa o mais recente por padrão.

---

## Estrutura interna do pipeline de NLU

```
Texto bruto
    │
WhitespaceTokenizer         ← divide em tokens (palavras)
    │
RegexFeaturizer             ← detecta padrões (números, datas, siglas)
    │
LexicalSyntacticFeaturizer  ← features de posição/morfologia
    │
CountVectorsFeaturizer      ← bag-of-words (nível palavra)
    │
CountVectorsFeaturizer      ← char n-grams (captura prefixos, sufixos, erros de digitação)
    │
DIETClassifier              ← classifica a intent (modelo principal)
    │
FallbackClassifier          ← se confidence < 0.6 → marca como incerto
```

O `FallbackClassifier` não retorna uma intent diferente — ele só sinaliza que a confidence está baixa. O `RasaClient` captura isso e usa `ask_about_document` como fallback.

---

## Melhorando o NLU

### O que melhora a qualidade de classificação

**1. Mais exemplos variados em `nlu.yml`**

O DIETClassifier aprende por exemplos. A qualidade depende da **variedade**, não só da quantidade.

Ruim (exemplos muito parecidos):
```yaml
- quais são os prazos?
- quais são os prazos do edital?
- quais são os prazos do processo?
```

Bom (estruturas diferentes, mesma intenção):
```yaml
- quais são os prazos?
- quando fecha as inscrições?
- até quando posso me inscrever?
- me informa a data limite
- qual o cronograma do processo?
```

**2. Cobrir variações linguísticas reais**

Pense em como pessoas reais perguntam — com erros, abreviações, formalidade variável:
```yaml
- vc pode me dizer sobre o edital?
- quero saber + sobre a resolução
- me fala do plano de ensino
- qual eh a norma sobre isso
```

**3. Exemplos negativos (fronteira entre intents)**

Se o modelo confunde chitchat com ask_about_document, adicione exemplos que explicitam a fronteira:
```yaml
# chitchat — perguntas sobre a IA, não sobre documentos
- você sabe tudo sobre documentos?
- você pode me ajudar com qualquer coisa?
- o que você consegue fazer?
```

### Sugestões de novos exemplos para `ask_about_document`

```yaml
# Consultas por tipo de documento
- tem algum edital de concurso disponível?
- qual resolução trata sobre regime de trabalho?
- existe normativa sobre afastamento?

# Referências a campos específicos
- quem assinou essa portaria?
- quando foi publicado esse ato?
- qual a vigência dessa resolução?

# Consultas com contexto institucional IFAL
- o que diz o estatuto sobre colegiados?
- quais são as atribuições do diretor geral?
- como funciona o processo de avaliação docente?

# Linguagem mais informal
- me explica esse documento
- do que trata esse edital?
- tem algo sobre bolsas?
- qual é a norma pra tirar licença?
```

### Sugestões de novos exemplos para `chitchat`

```yaml
# Mais variações de saudação
- e aí
- oi tudo bom?
- boa tarde!
- olá!

# Despedidas
- até mais
- até logo
- falou

# Agradecimentos
- valeu mesmo
- muito obrigada
- brigadão

# Perguntas sobre a ferramenta
- como você funciona?
- o que você faz?
- você é um robô?

# Respostas a perguntas
- não sei
- talvez
- claro
- sim
- não
```

### Como avaliar a qualidade do modelo

```bash
# Modo interativo — digita frases e vê a intent + confidence em tempo real
docker-compose --profile rasa run --rm -it rasa rasa shell nlu

# Avaliação formal com cross-validation (demora mais, mais preciso)
docker-compose --profile rasa run --rm rasa \
  rasa test nlu --nlu rasa/data/nlu.yml --cross-validation
```

No modo interativo, preste atenção na confidence:
- **> 0.85** → classificação confiável
- **0.60–0.85** → aceitável, mas considere adicionar exemplos
- **< 0.60** → fallback acionado → verifique os exemplos dessa intent

---

## Adicionando uma nova intent

1. Adicione em `nlu.yml` com pelo menos 10–15 exemplos variados:

```yaml
- intent: solicitar_documento
  examples: |
    - quero solicitar uma certidão
    - como faço para pedir uma declaração?
    - preciso de um documento comprovando meu vínculo
    - onde solicito a carteira de servidor?
```

2. Declare em `domain.yml`:

```yaml
intents:
  - ask_about_document
  - chitchat
  - solicitar_documento   # ← adicionar aqui
```

3. Retreine e suba:

```bash
docker-compose --profile rasa run --rm rasa rasa train
docker-compose --profile rasa up rasa
```

4. Trate no `ChatService` em `app/services/chat.py`:

```python
if intent == "solicitar_documento":
    # lógica específica — ex: resposta guiada sem RAG
    response = await self.llm.generate_response(
        context="", question=message, history=history
    )
```

---

## Verificar status pelo health endpoint

```bash
curl -H "Authorization: Bearer <TOKEN>" http://localhost:8000/api/v1/health
```

Com Rasa online:
```json
{
  "status": "healthy",
  "dependencies": {
    "elasticsearch": { "status": "up" },
    "rasa": { "status": "up", "url": "http://rasa:5005" }
  }
}
```

Com Rasa offline (chat continua funcionando):
```json
{
  "status": "healthy",
  "dependencies": {
    "elasticsearch": { "status": "up" },
    "rasa": { "status": "offline", "url": "http://rasa:5005" }
  }
}
```

---

## Decisões de design

| Decisão | Justificativa |
|---|---|
| Rasa como container separado (`profiles: rasa`) | Re-treinar sem redeploy da API; opcional para desenvolvimento |
| Apenas NLU, sem dialogue management | Só precisamos classificar intents; o histórico de conversa é gerenciado pela API |
| `DIETClassifier` | Treino rápido (~2 min), funciona bem com poucos dados, sem GPU |
| Fallback para `ask_about_document` | Comportamento conservador: sempre tenta buscar nos docs, nunca falha |
| Threshold 0.6 | Abaixo disso a confidence não é confiável; melhor usar o fallback seguro |
| Exemplos em PT-BR | O corpus e os usuários são brasileiros |
| Volume `./rasa:/app` | Editar localmente = editar no container; sem rebuild de imagem ao mudar dados de treino |
