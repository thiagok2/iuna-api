# Metodologia: Spec-Driven Development (SDD)

## Visão Geral

Spec-Driven Development é uma metodologia de especificação e planejamento de software que transforma uma ideia bruta em um plano de implementação detalhado e verificável. O processo é iterativo e produz três artefatos sequenciais:

1. **Requirements** — O quê precisa ser feito (perspectiva de negócio/usuário)
2. **Design** — Como será feito (perspectiva técnica)
3. **Tasks** — Em que ordem executar (plano de implementação)

A metodologia pode ser aplicada tanto por equipes humanas quanto com assistência de IA. O diferencial está na granularidade, rastreabilidade entre artefatos e no uso de propriedades formais de corretude para validar a implementação.

---

## Princípios Fundamentais

| Princípio | Descrição |
|-----------|-----------|
| **Ground-truth incremental** | Cada artefato só é produzido quando o anterior está validado e aceito. Nunca avançar sem consenso. |
| **Rastreabilidade** | Todo critério de aceitação deve ser referenciável no design e nas tasks. Todo teste deve referenciar o requisito que valida. |
| **Propriedades de corretude** | Definir formalmente o que "funcionar corretamente" significa, tornando a corretude testável e não subjetiva. |
| **Granularidade atômica** | Cada task deve ser executável por uma pessoa sem ambiguidade. Se há dúvida, a task precisa ser dividida. |
| **Vocabulário compartilhado** | Termos de domínio devem ser definidos em glossário para eliminar ambiguidade entre equipe técnica e de negócio. |

---

## Fluxos de Trabalho

### Fluxo Requirements-First (recomendado para novas features)

```
Ideia → Requirements → Design → Tasks → Implementação
```

Usar quando: há necessidade clara de negócio, mas a solução técnica ainda não é evidente.

### Fluxo Design-First (para refactoring ou evolução técnica)

```
Ideia → Design → Requirements → Tasks → Implementação
```

Usar quando: a abordagem técnica já é conhecida, mas os requisitos formais ainda não estão documentados.

### Fluxo Bugfix (para correção de defeitos)

```
Bug reportado → Bugfix Requirements (com Bug Condition) → Design → Tasks → Implementação
```

Usar quando: algo que funcionava parou de funcionar, ou o comportamento é incorreto.

---

## Artefato 1: Requirements (Requisitos)

### Estrutura do Documento

```markdown
# Requirements Document

## Introduction
Parágrafo descrevendo o contexto, objetivo e escopo em linguagem acessível.

## Glossary
Definição dos termos de domínio usados no documento.

## Requirements

### Requisito N: [Título Descritivo]

**User Story:** Como [papel], eu quero [ação], para que [benefício].

#### Critérios de Aceitação
1. [Critério usando formato EARS]
2. [Critério usando formato EARS]
...
```

### Critérios para um Bom Requisito

| Critério | Como avaliar |
|----------|-------------|
| **Atômico** | O requisito trata de exatamente uma funcionalidade? |
| **Testável** | É possível escrever um teste que verifica se o requisito foi atendido? |
| **Sem ambiguidade** | Duas pessoas leem o requisito e entendem a mesma coisa? |
| **Rastreável** | Pode ser referenciado por número em outros artefatos? |
| **Independente** | Pode ser implementado sem depender de outros requisitos (quando possível)? |

### Formato EARS para Critérios de Aceitação

EARS (Easy Approach to Requirements Syntax) elimina ambiguidade usando palavras-chave obrigatórias:

| Palavra-chave | Quando usar | Exemplo |
|---------------|-------------|---------|
| **WHEN** | Gatilho/evento que inicia o comportamento | WHEN o usuário clica no botão "Publicar" |
| **WHILE** | Condição que está ativa durante o comportamento | WHILE o formulário está em estado de publicação |
| **WHERE** | Contexto ou escopo onde o comportamento se aplica | WHERE a aplicação está na rota `/feed` |
| **IF** | Condição opcional que pode ou não estar presente | IF o usuário está autenticado |
| **THE [Sistema]** | O sujeito que executa a ação | THE Aplicação |
| **SHALL** | Obrigação do sistema (verbo modal obrigatório) | SHALL exibir a mensagem de sucesso |
| **THEN** | Consequência de uma condição | THEN o sistema exibe erro de validação |

**Padrão completo:**

```
[WHERE contexto,] [WHILE estado ativo,] WHEN evento, THE Sistema SHALL ação.
[IF condição,] THE Sistema SHALL ação.
THE Sistema SHALL comportamento constante.
```

**Exemplos reais:**

```
✅ WHEN um usuário clica em um emoji, THE InputBox SHALL inserir o emoji na posição 
   atual do cursor no textarea.

✅ WHILE o InputBox está em estado de publicação (isPublicando), THE Barra de Emojis 
   SHALL desabilitar todos os botões de emoji.

✅ THE Barra de Emojis SHALL conter no mínimo 8 emojis de categorias emocionais diversas.

❌ O sistema deve funcionar bem com emojis.  (vago, não-testável)
❌ Os emojis devem ser bonitos.  (subjetivo)
```

### User Stories

Formato: **Como [papel], eu quero [ação], para que [benefício].**

| Elemento | Pergunta que responde | Exemplo |
|----------|----------------------|---------|
| **Papel** | Quem se beneficia? | "Como um usuário escrevendo um desabafo" |
| **Ação** | O que a pessoa quer fazer? | "eu quero ver uma barra de emojis" |
| **Benefício** | Por que isso importa? | "para que eu possa expressar emoções no texto" |

A user story é o "porquê". Os critérios de aceitação são o "o quê" verificável.

### Glossário

Cada termo técnico ou de domínio que possa ter interpretação ambígua deve ser definido:

```markdown
## Glossary

- **Emoji_Picker_Bar**: Barra horizontal de UI com botões de emoji clicáveis
- **Cursor_Position**: Ponto de inserção atual (caret) no textarea
- **Desabafo**: Confissão anônima publicada por um usuário
```

**Regras do glossário:**
- Use PascalCase ou snake_case para termos compostos
- A definição deve ser inequívoca (uma pessoa leiga entenderia?)
- Referencie termos do glossário nos critérios de aceitação

---

## Artefato 2: Design (Design Técnico)

### Estrutura do Documento

```markdown
# Design Document: [Nome da Feature]

## Overview
Resumo técnico de alto nível da solução.

## Architecture
Descrição da arquitetura com diagramas (Mermaid recomendado).
Tabela de decisões arquiteturais com justificativas.

## Components and Interfaces
Componentes modificados/criados, suas interfaces e contratos.

## Data Models
Modelos de dados, schemas, tipos e interfaces.

## Correctness Properties
Propriedades formais de corretude (ver seção dedicada).

## Error Handling
Como cada cenário de erro é tratado.

## Testing Strategy
Estratégia de testes: unit, property-based, integration.
```

### Decisões Arquiteturais

Cada decisão não-óbvia deve ser documentada com justificativa:

```markdown
| Decisão | Justificativa |
|---------|---------------|
| Inline no InputBox (sem componente separado) | Emoji bar é acoplado ao ref do textarea e estado `texto`; extrair exigiria prop drilling sem benefício real |
| `useRef` para rastrear cursor | React não expõe posição do cursor em componentes controlados; ler `selectionStart` do DOM ref é o padrão |
| `requestAnimationFrame` para restaurar cursor | Após `setTexto` causar re-render, o DOM reseta cursor para o final; rAF roda após paint |
```

**Perguntas para cada decisão:**
1. Quais alternativas foram consideradas?
2. Por que esta alternativa foi escolhida?
3. Quais tradeoffs foram aceitos?
4. Em que circunstâncias esta decisão deveria ser revisitada?

### Componentes e Interfaces

Para cada componente/módulo, documentar:
- Nome e localização no código
- Interface pública (props, exports, tipos)
- Comportamento esperado
- Dependências

```typescript
// Exemplo de interface documentada
interface EmojiItem {
  char: string;   // Caractere emoji (e.g., '❤️')
  label: string;  // Descrição em português para aria-label
}

// Função pura documentada
export function inserirEmojiNoTexto(
  texto: string,
  emoji: string,
  cursorPos: number,
  maxCaracteres: number
): { novoTexto: string; novaPosicao: number } | null
```

### Propriedades de Corretude (Correctness Properties)

**O que é uma propriedade de corretude?**

Uma propriedade é uma afirmação formal sobre o comportamento do sistema que deve ser verdadeira para TODOS os inputs válidos — não apenas para exemplos específicos.

**Diferença entre teste comum e propriedade:**

| Teste Comum (example-based) | Propriedade (property-based) |
|------------------------------|------------------------------|
| "Inserir '😊' na posição 5 do texto 'hello' resulta em 'hello😊'" | "Para QUALQUER texto, QUALQUER posição válida e QUALQUER emoji: resultado === texto[0..pos] + emoji + texto[pos..]" |
| Verifica um caso | Verifica uma família infinita de casos |
| Pode perder edge cases | Descobre edge cases via geração aleatória |

**Formato de uma propriedade:**

```markdown
### Property N: [Nome descritivo]

*For any* [domínio de entrada] [restrições], [operação] SHALL [resultado esperado].

**Validates: Requirements [lista de requisitos validados]**
```

**Exemplo real:**

```markdown
### Property 1: Inserção de emoji preserva texto adjacente

*For any* string de texto com comprimento ≤ 2000 caracteres, qualquer posição de 
cursor válida em [0, texto.length], e qualquer emoji do conjunto EMOJIS: inserir 
o emoji nessa posição SHALL produzir resultado onde 
`result === texto.slice(0, cursor) + emoji + texto.slice(cursor)` 
e a nova posição do cursor é `cursor + emoji.length`.

**Validates: Requirements 2.1, 2.2, 2.3**
```

**Como identificar propriedades:**
1. Quais invariantes o sistema deve manter? (ex: texto nunca excede 2000 chars)
2. Quais relações entre entrada e saída devem sempre valer? (ex: inserção preserva texto adjacente)
3. Quais operações são idempotentes? (ex: aplicar filtro duas vezes produz mesmo resultado)
4. Quais sequências de operações devem ser comutativas? (ex: inserir A depois B = inserir B depois A em posições independentes)

### Tratamento de Erros

Para cada cenário de erro identificado:

```markdown
| Cenário | Tratamento | Feedback ao Usuário |
|---------|------------|---------------------|
| Emoji ultrapassa limite de chars | `inserirEmoji` retorna sem modificar texto | Nenhum (limite visual do textarea já indica) |
| textarea ref é null | Fallback: insere no final do texto | Nenhum (transparente) |
```

---

## Artefato 3: Tasks (Plano de Implementação)

### Estrutura do Documento

```markdown
# Implementation Plan: [Nome da Feature]

## Overview
Resumo da estratégia de implementação (bottom-up, top-down, etc.)

## Tasks

- [ ] 1. [Grupo de tarefas]
  - [ ] 1.1 [Tarefa atômica]
    - Descrição detalhada do que fazer
    - _Requirements: N.N, N.N_

  - [ ] 1.2 [Tarefa atômica]
    - Descrição detalhada
    - _Requirements: N.N_

- [ ] 2. [Próximo grupo]
  ...

## Notes
Observações sobre ordem de execução, dependências e critérios de sucesso.

## Task Dependency Graph
Grafo de dependências entre tarefas (formato JSON).
```

### Critérios para uma Boa Task

| Critério | Pergunta de Verificação |
|----------|------------------------|
| **Atômica** | Uma pessoa consegue completar sem precisar tomar decisões de design? |
| **Verificável** | Existe um critério claro de "pronto"? |
| **Rastreável** | A task referencia quais requisitos implementa? |
| **Estimável** | É possível estimar esforço com confiança? (ideal: < 2h) |
| **Independente (quando possível)** | Pode ser executada em paralelo com tasks de outra wave? |

### Níveis de Granularidade

```
Grupo (1, 2, 3...)        → Épico / Milestone
  └── Subtask (1.1, 1.2)  → Unidade executável de trabalho
        └── Bullet points  → Instruções específicas dentro da subtask
```

**Exemplo real:**

```markdown
- [ ] 1. Criar helper puro e constante EMOJIS
  - [ ] 1.1 Criar função `inserirEmojiNoTexto` em `src/components/InputBox.tsx`
    - Definir interface `EmojiItem` com campos `char` e `label`
    - Implementar função pura exportada que retorna `{ novoTexto, novaPosicao } | null`
    - Retorna `null` se `texto.length + emoji.length > maxCaracteres`
    - _Requirements: 2.1, 2.2, 2.3, 2.5_
```

### Checkpoints

Inserir checkpoints entre grupos para validação incremental:

```markdown
- [ ] 4. Checkpoint - Verificar funcionalidade visual
  - Garantir que todos os testes passam
  - Validar visualmente o componente no browser
```

### Task Dependency Graph

O grafo de dependências define quais tasks podem ser executadas em paralelo (mesma "wave") e quais dependem de tasks anteriores:

```json
{
  "waves": [
    { "id": 0, "tasks": ["1.1", "1.2"] },
    { "id": 1, "tasks": ["2.1", "3.1"] },
    { "id": 2, "tasks": ["2.2"] },
    { "id": 3, "tasks": ["2.3"] },
    { "id": 4, "tasks": ["5.1", "5.2", "5.3", "5.4"] }
  ]
}
```

**Leitura:** Tasks na wave 0 podem começar imediatamente. Tasks na wave 1 só começam quando a wave 0 estiver completa. Tasks dentro da mesma wave são independentes entre si.

### Marcação de Tasks Opcionais

Tasks que podem ser postergadas para MVP mais rápido são marcadas com `*`:

```markdown
- [ ]* 5.1 Escrever property test para inserção de emoji
```

---

## Variação: Bugfix Requirements

Para correção de bugs, o documento de requisitos segue um formato especializado com análise formal do defeito.

### Estrutura

```markdown
# Bugfix Requirements Document

## Introduction
Contexto do bug e impacto no sistema.

## Bug Analysis

### Current Behavior (Defect)
Lista numerada de comportamentos incorretos usando formato WHEN/THEN.

### Expected Behavior (Correct)
Lista numerada de comportamentos esperados usando formato WHEN/THEN/SHALL.

### Unchanged Behavior (Regression Prevention)
Lista de comportamentos que NÃO devem mudar (proteção contra regressão).

## Bug Condition (Formal)
Função formal que identifica quando o bug se manifesta.
```

### Bug Condition — Formalização do Defeito

A Bug Condition é uma função booleana que retorna `true` para inputs onde o bug se manifesta:

```pascal
FUNCTION isBugCondition(X)
  INPUT: X of type { sentimento: string, reacoes: Map<string, number> }
  OUTPUT: boolean
  
  RETURN X.sentimento NOT IN ['triste', 'raiva', 'alivio']
      OR keys(X.reacoes) != {'apoio', 'forca', 'pouco'}
END FUNCTION
```

### Fix Checking e Preservation Checking

O design de bugfix deve demonstrar duas propriedades:

**Fix Checking** — Para todos os inputs onde o bug se manifesta, o código corrigido agora funciona:

```pascal
FOR ALL X WHERE isBugCondition(X) DO
  ASSERT sistema_corrigido(X) = COMPORTAMENTO_ESPERADO
END FOR
```

**Preservation Checking** — Para todos os inputs onde o bug NÃO se manifesta, o comportamento permanece idêntico:

```pascal
FOR ALL X WHERE NOT isBugCondition(X) DO
  ASSERT sistema_original(X) = sistema_corrigido(X)
END FOR
```

---

## Rastreabilidade Entre Artefatos

A rastreabilidade garante que nenhum requisito fique sem implementação e nenhuma task fique sem justificativa:

```
Requirements          →    Design              →    Tasks
─────────────────────────────────────────────────────────────
Req 2.1 (inserir      →    Property 1          →    Task 1.1 (helper puro)
emoji no cursor)            (preserva texto)         _Requirements: 2.1, 2.2_

Req 2.5 (limite       →    Property 2          →    Task 2.2 (handler)
de caracteres)              (limite respeitado)      _Requirements: 2.5_

Req 4.1 (role=        →    Property 3          →    Task 2.3 (JSX)
toolbar)                    (aria-labels)            _Requirements: 4.1, 4.3_
```

**Regra de ouro:** Se uma task não referencia nenhum requisito, ela não deveria existir. Se um requisito não é referenciado por nenhuma task, ele não será implementado.

---

## Checklist de Revisão

### Para Requirements

- [ ] Cada requisito tem user story com papel, ação e benefício?
- [ ] Cada critério de aceitação usa formato EARS com SHALL?
- [ ] Os critérios são testáveis (é possível escrever um teste automatizado)?
- [ ] O glossário define todos os termos de domínio?
- [ ] Não há requisitos vagos ou subjetivos?
- [ ] Cada requisito é atômico (trata de uma coisa só)?

### Para Design

- [ ] O overview é compreensível para alguém que não leu os requisitos?
- [ ] Decisões arquiteturais têm justificativa documentada?
- [ ] Interfaces e contratos estão definidos com tipos?
- [ ] Propriedades de corretude são verificáveis via teste?
- [ ] Cada propriedade referencia os requisitos que valida?
- [ ] Cenários de erro estão mapeados com tratamento definido?
- [ ] A estratégia de testes cobre unit, property e integration?

### Para Tasks

- [ ] Cada task é executável em menos de 2 horas?
- [ ] Cada task referencia os requisitos que implementa?
- [ ] O grafo de dependências está correto (sem ciclos)?
- [ ] Tasks paralelas são realmente independentes?
- [ ] Checkpoints estão posicionados em momentos de validação útil?
- [ ] Tasks opcionais estão claramente marcadas?
- [ ] A descrição de cada task é suficiente para executar sem perguntas?

---

## Guia Rápido: Processo Passo a Passo

### 1. Definir Escopo (5-15 min)
- Escrever uma frase resumindo o que será feito
- Classificar: feature nova / enhancement / bugfix
- Nomear: `{tipo}-{número}-{nome-kebab-case}`

### 2. Elaborar Requirements (30-60 min)
- Escrever Introduction contextual
- Definir Glossário com termos de domínio
- Para cada funcionalidade:
  - Escrever user story
  - Listar critérios de aceitação em formato EARS
- Revisar: cada critério é testável?

### 3. Elaborar Design (45-90 min)
- Descrever Overview técnico
- Documentar Architecture com diagramas
- Listar decisões com justificativas
- Definir interfaces e tipos
- Formular Correctness Properties
- Mapear Error Handling
- Definir Testing Strategy

### 4. Elaborar Tasks (20-40 min)
- Agrupar trabalho em milestones lógicos
- Decompor em subtasks atômicas
- Adicionar descrição detalhada a cada subtask
- Referenciar requisitos em cada task
- Definir grafo de dependências (waves)
- Posicionar checkpoints
- Marcar tasks opcionais

### 5. Implementar (tempo variável)
- Seguir a ordem do grafo de dependências
- Marcar tasks como concluídas (`[x]`)
- Validar em cada checkpoint
- Rodar property tests para verificar corretude

---

## Exemplo Completo Simplificado

Para uma feature "Botão de Curtir":

**Requisito:**
```
### Requisito 1: Curtir um Desabafo

**User Story:** Como um visitante, eu quero curtir um desabafo, para que eu possa 
demonstrar apoio sem precisar comentar.

#### Critérios de Aceitação
1. THE Aplicação SHALL exibir um botão de curtir em cada card de desabafo
2. WHEN um visitante clica no botão de curtir, THE Aplicação SHALL incrementar 
   o contador de curtidas em 1
3. THE Aplicação SHALL persistir a contagem de curtidas no Firestore
4. WHEN um visitante já curtiu um desabafo, THE Aplicação SHALL impedir 
   nova curtida no mesmo desabafo (via localStorage)
```

**Propriedade de Corretude:**
```
Property 1: Curtir incrementa contador em exatamente 1

*For any* desabafo com N curtidas e qualquer visitante que ainda não curtiu: 
após curtir, o contador SHALL ser exatamente N+1.

**Validates: Requirements 1.2, 1.3**
```

**Task:**
```
- [ ] 1.1 Implementar hook `useCurtida` em `src/hooks/useCurtida.ts`
  - Criar hook que lê contagem atual e incrementa via transaction
  - Usar localStorage para rastrear curtidas já dadas
  - Retornar `{ curtidas, jaCurtiu, curtir }`
  - _Requirements: 1.2, 1.3, 1.4_
```

---

## Quando NÃO Usar Esta Metodologia

Esta abordagem é ideal para features com complexidade média a alta. Para mudanças triviais (renomear variável, corrigir typo, ajustar padding), basta fazer. Reserve o SDD para:

- Features que envolvem mais de um componente/módulo
- Mudanças que afetam comportamento observável pelo usuário
- Correções de bugs com risco de regressão
- Trabalho que será executado por mais de uma pessoa
- Funcionalidades que precisam de validação antes da implementação
