# Documento de Requisitos — Busca de Documentos (document-search)

## Introdução

Este módulo implementa os controladores e serviços de busca para documentos armazenados no Elasticsearch (índice `documentos_ifal_v2`). O escopo abrange documentos institucionais (editais, portarias, resoluções, regulamentos, atas, memorandos, ofícios, pareceres, contratos, convênios), materiais didáticos (apostilas, livros, planos de ensino, guias de estudo, slides, roteiros de aula) e propostas de projeto de submissão (projetos de pesquisa, extensão, inovação, TCC). Todas as operações possuem duplo ponto de entrada: API HTTP (controllers) e CLI/Batch (usando o filename como identificador para leitura e escrita sobre diretórios completos). O módulo também inclui a segmentação (chunking) de documentos em blocos maiores (~3000 caracteres / 1 página) com busca integrada em TODOS os blocos de um documento segmentado.

## Glossário

- **Search_Controller**: Camada HTTP (FastAPI Router) responsável por receber requisições de busca, validar parâmetros e delegar ao Search_Service.
- **Search_Service**: Camada de lógica de negócios que constrói queries Elasticsearch, executa buscas e formata resultados.
- **ES_Client**: Cliente de infraestrutura que se comunica diretamente com o cluster Elasticsearch.
- **CLI_Runner**: Componente de linha de comando que executa operações em lote (batch) sobre diretórios de arquivos, usando o filename como identificador.
- **Chunking_Service**: Serviço responsável por segmentar textos de documentos em blocos (chunks) de tamanho configurável.
- **Documento**: Registro indexado no Elasticsearch (índice `documentos_ifal_v2`) representando qualquer tipo de documento do IFAL — institucional, didático ou proposta de projeto.
- **Chunk**: Fragmento de texto gerado pela segmentação de um documento, armazenado no índice `documentos_ifal_v2_chunks` com referência ao documento pai.
- **Faceta**: Agregação de valores de um campo específico do índice, usada para navegação filtrada (ex: tipos de documento, órgãos, anos).
- **Filename**: Nome do arquivo físico do documento, usado como identificador único em operações CLI/Batch sobre diretórios.
- **Full_Text_Search**: Busca textual completa usando o motor BM25 do Elasticsearch sobre campos text.
- **Filtered_Search**: Busca combinando texto livre com filtros exatos em campos keyword (tipo_doc, fonte.orgao, ano, etc).
- **Faceted_Search**: Busca que retorna, além dos resultados, agregações (facetas) para navegação refinada.

## Requisitos

### Requisito 1: Busca Full-Text de Documentos

**User Story:** Como um usuário da API, quero realizar buscas textuais livres sobre os documentos indexados, para encontrar documentos relevantes com base em termos de pesquisa.

#### Critérios de Aceitação

1. WHEN uma requisição GET é recebida em `/api/v1/search` com o parâmetro `q` (query string), THE Search_Controller SHALL delegar a busca ao Search_Service e retornar os documentos correspondentes em formato JSON paginado.
2. WHEN o parâmetro `q` é fornecido, THE Search_Service SHALL executar uma busca full-text BM25 nos campos `ato.titulo`, `ato.ementa`, `attachment.content` e `ato.tags` do índice `documentos_ifal_v2`.
3. WHEN o parâmetro `q` está vazio ou ausente, THE Search_Controller SHALL retornar erro HTTP 400 com mensagem descritiva indicando que o termo de busca é obrigatório.
4. THE Search_Service SHALL retornar os resultados ordenados por relevância (_score) do Elasticsearch por padrão.
5. WHEN os parâmetros `page` (padrão: 1) e `page_size` (padrão: 20) são fornecidos, THE Search_Service SHALL aplicar paginação offset-based nos resultados retornados.
6. THE Search_Controller SHALL retornar no corpo da resposta JSON os campos: `total` (total de resultados), `page`, `page_size`, `results` (lista de documentos) e `took_ms` (tempo de execução da query em milissegundos).

---

### Requisito 2: Busca Filtrada de Documentos

**User Story:** Como um usuário da API, quero combinar busca textual com filtros estruturados, para refinar resultados por tipo de documento, órgão, ano ou esfera.

#### Critérios de Aceitação

1. WHEN uma requisição GET é recebida em `/api/v1/search` com o parâmetro `q` e filtros adicionais, THE Search_Controller SHALL delegar ao Search_Service aplicando os filtros como cláusulas `filter` na query Elasticsearch.
2. WHEN o parâmetro `tipo_doc` é fornecido, THE Search_Service SHALL filtrar resultados pelo campo `ato.tipo_doc.keyword` com match exato.
3. WHEN o parâmetro `orgao` é fornecido, THE Search_Service SHALL filtrar resultados pelo campo `ato.fonte.orgao.keyword` com match exato.
4. WHEN o parâmetro `ano` é fornecido, THE Search_Service SHALL filtrar resultados pelo campo `ato.ano` com valor numérico exato.
5. WHEN o parâmetro `esfera` é fornecido, THE Search_Service SHALL filtrar resultados pelo campo `ato.fonte.esfera.keyword` com match exato.
6. WHEN o parâmetro `data_inicio` e/ou `data_fim` são fornecidos, THE Search_Service SHALL filtrar resultados pelo campo `ato.data_publicacao` usando range query com os limites especificados.
7. WHEN o parâmetro `publico` (boolean) é fornecido, THE Search_Service SHALL filtrar resultados pelo campo `ato.publico`.
8. WHEN múltiplos filtros são fornecidos simultaneamente, THE Search_Service SHALL aplicar todos como cláusulas AND (interseção).

---

### Requisito 3: Busca Facetada (Agregações)

**User Story:** Como um usuário da API, quero receber agregações (facetas) junto com os resultados de busca, para navegar e refinar consultas progressivamente.

#### Critérios de Aceitação

1. WHEN uma requisição GET é recebida em `/api/v1/search/facets` com o parâmetro `q`, THE Search_Controller SHALL retornar resultados de busca acompanhados de agregações (facetas).
2. THE Search_Service SHALL retornar facetas para os campos: `ato.tipo_doc.keyword`, `ato.fonte.orgao.keyword`, `ato.fonte.esfera.keyword`, `ato.ano` e `ato.tags.keyword`.
3. WHEN facetas são retornadas, THE Search_Service SHALL incluir para cada valor: o termo (key), a contagem de documentos (doc_count) e indicação se o filtro está ativo.
4. WHEN filtros são aplicados junto com a requisição de facetas, THE Search_Service SHALL calcular as contagens das facetas considerando os filtros aplicados (post-filter aggregation pattern).

---

### Requisito 4: Busca por Documento Individual

**User Story:** Como um usuário da API, quero buscar um documento específico pelo seu identificador, para visualizar todos os seus metadados e conteúdo.

#### Critérios de Aceitação

1. WHEN uma requisição GET é recebida em `/api/v1/search/{document_id}`, THE Search_Controller SHALL retornar o documento completo do índice `documentos_ifal_v2` correspondente ao `ato.ato_id` fornecido.
2. WHEN uma requisição GET é recebida em `/api/v1/search/by-filename/{filename}`, THE Search_Controller SHALL retornar o documento correspondente ao campo `filename.keyword` fornecido.
3. IF o `document_id` ou `filename` fornecido não corresponder a nenhum documento indexado, THEN THE Search_Controller SHALL retornar erro HTTP 404 com mensagem descritiva.
4. THE Search_Controller SHALL retornar todos os campos do documento (_source) no corpo da resposta JSON.

---

### Requisito 5: Segmentação (Chunking) de Documentos com Blocos Maiores

**User Story:** Como um desenvolvedor, quero segmentar documentos em blocos de pelo menos uma página (~3000 caracteres), para que a busca semântica opere sobre fragmentos significativos do texto.

#### Critérios de Aceitação

1. WHEN uma requisição POST é recebida em `/api/v1/search/chunk` com `document_id` ou `filename`, THE Search_Controller SHALL delegar ao Chunking_Service para segmentar o conteúdo textual do documento.
2. THE Chunking_Service SHALL usar tamanho de chunk padrão de 3000 caracteres (aproximadamente 1 página) e sobreposição (overlap) padrão de 500 caracteres.
3. WHEN parâmetros opcionais `chunk_size` (mínimo: 3000) e `chunk_overlap` são fornecidos na requisição, THE Chunking_Service SHALL usar os valores especificados pelo usuário, validando que `chunk_size` é maior ou igual a 3000.
4. IF o valor de `chunk_size` fornecido for menor que 3000, THEN THE Search_Controller SHALL retornar erro HTTP 422 com mensagem indicando que o tamanho mínimo de chunk é 3000 caracteres.
5. WHEN a segmentação é concluída, THE Chunking_Service SHALL indexar cada chunk no índice `documentos_ifal_v2_chunks` com os campos: `parent_document_id` (referência ao documento pai via `ato.ato_id`), `parent_filename` (filename do documento pai), `chunk_index` (posição sequencial), `content` (texto do bloco) e `total_chunks` (número total de blocos gerados).
6. THE Chunking_Service SHALL preservar a associação entre todos os chunks e o documento pai para garantir busca completa em todos os blocos.

---

### Requisito 6: Busca em Documentos Segmentados (Chunks)

**User Story:** Como um usuário da API, quero que a busca textual pesquise em TODOS os blocos de documentos segmentados, para encontrar informações mesmo quando estão em fragmentos específicos.

#### Critérios de Aceitação

1. WHEN uma requisição GET é recebida em `/api/v1/search/chunks` com o parâmetro `q`, THE Search_Controller SHALL executar busca full-text no índice `documentos_ifal_v2_chunks` sobre o campo `content`.
2. THE Search_Service SHALL retornar para cada resultado de chunk: o conteúdo do chunk, o `chunk_index`, o `parent_document_id`, o `parent_filename` e o `total_chunks` do documento pai.
3. WHEN o parâmetro `document_id` ou `filename` é fornecido junto com `q`, THE Search_Service SHALL restringir a busca de chunks apenas aos blocos associados ao documento pai especificado.
4. THE Search_Service SHALL agrupar os resultados de chunks por documento pai, indicando em quais blocos o termo foi encontrado e a relevância de cada bloco.
5. WHEN um documento segmentado é encontrado pela busca, THE Search_Service SHALL indicar que o resultado provém de um documento segmentado e informar o total de blocos nos quais o termo aparece versus o total de blocos do documento.

---

### Requisito 7: Operações CLI/Batch sobre Diretórios

**User Story:** Como um administrador do sistema, quero executar operações de busca e segmentação em lote via CLI sobre diretórios completos, usando o filename como identificador para leitura e escrita.

#### Critérios de Aceitação

1. WHEN o comando CLI `iuna search` é executado com `--directory <path>` e `--query <termo>`, THE CLI_Runner SHALL executar a busca para cada arquivo no diretório usando o filename como identificador e exportar os resultados em formato JSON para o diretório de saída.
2. WHEN o comando CLI `iuna chunk` é executado com `--directory <path>`, THE CLI_Runner SHALL segmentar todos os documentos do diretório em chunks de pelo menos 3000 caracteres, usando o filename de cada arquivo como identificador para leitura do conteúdo e gravação dos chunks associados.
3. WHEN o parâmetro `--output <path>` é fornecido, THE CLI_Runner SHALL gravar os resultados da operação no diretório de saída especificado.
4. WHEN o parâmetro `--output` é omitido, THE CLI_Runner SHALL gravar os resultados em um subdiretório `_output` dentro do diretório de entrada.
5. THE CLI_Runner SHALL usar exclusivamente o filename (sem extensão) como identificador do documento em todas as operações de leitura e escrita.
6. WHEN um arquivo do diretório já possui chunks indexados no Elasticsearch, THE CLI_Runner SHALL oferecer a opção `--force` para reprocessar e `--skip-existing` para ignorar documentos já segmentados.
7. THE CLI_Runner SHALL exibir progresso da operação em lote (arquivo atual / total de arquivos) no terminal durante a execução.

---

### Requisito 8: Suporte ao Escopo Amplo de Documentos

**User Story:** Como um usuário do sistema, quero que a busca abranja todos os tipos de documentos do IFAL (institucionais, didáticos e propostas de projeto), para acessar qualquer material disponível na base.

#### Critérios de Aceitação

1. THE Search_Service SHALL suportar busca sobre os seguintes tipos de documentos institucionais indexados no campo `ato.tipo_doc`: editais, portarias, resoluções, regulamentos, atas, memorandos, ofícios, pareceres, contratos, convênios, despachos, instruções normativas e comunicados.
2. THE Search_Service SHALL suportar busca sobre materiais didáticos indexados no campo `ato.tipo_doc`: apostilas, livros, planos de ensino, guias de estudo, slides, roteiros de aula, provas, listas de exercícios e material complementar.
3. THE Search_Service SHALL suportar busca sobre propostas de projeto indexadas no campo `ato.tipo_doc`: projetos de pesquisa, projetos de extensão, projetos de inovação, trabalhos de conclusão de curso (TCC) e relatórios técnicos.
4. WHEN nenhum filtro de `tipo_doc` é aplicado, THE Search_Service SHALL buscar em todos os tipos de documentos disponíveis sem distinção.
5. WHEN o parâmetro `categoria` é fornecido com valores `institucional`, `didatico` ou `projeto`, THE Search_Service SHALL filtrar pelos tipos de documento correspondentes à categoria informada.

---

### Requisito 9: Camada de Serviço de Busca (Search_Service)

**User Story:** Como um desenvolvedor, quero que toda a lógica de construção de queries e processamento de resultados esteja isolada no Search_Service, para manter os controllers finos e facilitar reutilização via CLI.

#### Critérios de Aceitação

1. THE Search_Service SHALL ser independente da camada HTTP, consumível tanto pelo Search_Controller (API) quanto pelo CLI_Runner (Batch).
2. THE Search_Service SHALL construir queries Elasticsearch usando a DSL `bool` com cláusulas `must` (full-text), `filter` (filtros exatos) e `aggs` (agregações).
3. THE Search_Service SHALL abstrair a comunicação com o Elasticsearch através do ES_Client, sem acoplar-se diretamente à biblioteca `elasticsearch-py`.
4. IF o Elasticsearch retornar erro de conexão ou timeout, THEN THE Search_Service SHALL propagar uma exceção tipada (`SearchServiceError`) com mensagem descritiva e código de erro.
5. IF a query contiver caracteres especiais do Elasticsearch (ex: `+`, `-`, `&&`, `||`, `!`, `(`, `)`, `{`, `}`, `[`, `]`, `^`, `"`, `~`, `*`, `?`, `:`, `\`, `/`), THEN THE Search_Service SHALL sanitizar a query antes de enviá-la ao Elasticsearch, escapando caracteres reservados.
6. THE Search_Service SHALL registrar logs estruturados (nível INFO) para cada busca executada, incluindo: query original, filtros aplicados, tempo de execução e total de resultados.

---

### Requisito 10: Respostas e Tratamento de Erros da API

**User Story:** Como um consumidor da API, quero que as respostas sigam um formato consistente e que erros sejam tratados de forma padronizada, para facilitar a integração.

#### Critérios de Aceitação

1. THE Search_Controller SHALL retornar respostas de sucesso com status HTTP 200 e corpo JSON contendo os campos `success` (boolean), `data` (objeto de resultado) e `meta` (metadados de paginação e tempo).
2. IF uma requisição contiver parâmetros inválidos (tipo errado, valor fora do range), THEN THE Search_Controller SHALL retornar status HTTP 422 com corpo JSON contendo `success: false`, `error_code` e `message` descritiva.
3. IF o Elasticsearch estiver indisponível, THEN THE Search_Controller SHALL retornar status HTTP 503 com corpo JSON contendo `success: false`, `error_code: "service_unavailable"` e `message` indicando indisponibilidade temporária do serviço de busca.
4. IF o documento solicitado não existir, THEN THE Search_Controller SHALL retornar status HTTP 404 com corpo JSON contendo `success: false`, `error_code: "not_found"` e `message` descritiva.
5. THE Search_Controller SHALL incluir o header `X-Request-Id` em todas as respostas para rastreabilidade de requisições.
