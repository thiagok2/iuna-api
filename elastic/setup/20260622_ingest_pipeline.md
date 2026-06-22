# Elasticsearch Ingest Attachment Pipeline

Pipeline para extração de texto de PDFs usando Apache Tika (plugin ingest-attachment).

## Pré-requisito: verificar se o plugin está instalado

```
GET https://elastic.pnld-avaliacao-dev.nees.ufal.br/_nodes/plugins
Authorization: Basic ZWxhc3RpYzpTWFR0NHJrMDV1RHE=
```

Na resposta, procure por `"ingest-attachment"` na lista de plugins de cada nó.
Se não estiver presente, o plugin precisa ser instalado no cluster ES:

```bash
bin/elasticsearch-plugin install ingest-attachment
```

---

## Criar o pipeline

```
PUT https://elastic.pnld-avaliacao-dev.nees.ufal.br/_ingest/pipeline/attachment_pipeline
Authorization: Basic ZWxhc3RpYzpTWFR0NHJrMDV1RHE=
Content-Type: application/json

{
  "description": "Extract text from PDF base64 data using Apache Tika",
  "processors": [
    {
      "attachment": {
        "field": "data",
        "target_field": "attachment",
        "indexed_chars": -1
      }
    },
    {
      "remove": {
        "field": "data",
        "ignore_missing": true
      }
    }
  ]
}
```

### O que o pipeline faz:

1. **attachment processor**: Recebe o campo `data` (PDF codificado em base64) e extrai o conteúdo textual para `attachment.content`, metadados para `attachment.title`, `attachment.content_length`, etc.
2. **remove processor**: Remove o campo `data` após a extração para não armazenar o base64 permanentemente (economia de storage).

`indexed_chars: -1` = sem limite de caracteres extraídos (extrai o documento inteiro).

---

## Verificar se o pipeline foi criado

```
GET https://elastic.pnld-avaliacao-dev.nees.ufal.br/_ingest/pipeline/attachment_pipeline
Authorization: Basic ZWxhc3RpYzpTWFR0NHJrMDV1RHE=
```

---

## Exemplo de uso (indexar documento com pipeline)

```
POST https://elastic.pnld-avaliacao-dev.nees.ufal.br/documentos_ifal_v2/_doc?pipeline=attachment_pipeline
Authorization: Basic ZWxhc3RpYzpTWFR0NHJrMDV1RHE=
Content-Type: application/json

{
  "data": "<BASE64_DO_PDF_AQUI>",
  "filename": "resolucao_001_2025.pdf",
  "ato": {
    "ato_id": "res-001-2025",
    "titulo": "Resolução nº 001/2025",
    "tipo_doc": "resolucao",
    "ano": 2025
  }
}
```

Após a indexação, o documento terá:
- `attachment.content` — texto completo extraído do PDF
- `attachment.title` — título extraído dos metadados do PDF (se disponível)
- `attachment.content_length` — tamanho do conteúdo extraído
- Campo `data` removido (não armazenado)

---

## Testar o pipeline isoladamente (simulate)

```
POST https://elastic.pnld-avaliacao-dev.nees.ufal.br/_ingest/pipeline/attachment_pipeline/_simulate
Authorization: Basic ZWxhc3RpYzpTWFR0NHJrMDV1RHE=
Content-Type: application/json

{
  "docs": [
    {
      "_source": {
        "data": "<BASE64_DO_PDF_AQUI>"
      }
    }
  ]
}
```
