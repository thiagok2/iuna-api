# Elasticsearch Ingest Attachment Pipeline

Pipeline para extração de texto de PDFs usando Apache Tika (plugin ingest-attachment).

## Pré-requisito: verificar se o plugin está instalado

```bash
curl -H "Authorization: Basic ZWxhc3RpYzpTWFR0NHJrMDV1RHE=" \
  "https://elastic.pnld-avaliacao-dev.nees.ufal.br/_nodes/plugins" \
  | python3 -c "import sys,json; nodes=json.load(sys.stdin).get('nodes',{}); [print(n['name'], [p['name'] for p in n.get('plugins',[])]) for n in nodes.values()]"
```

Na resposta, procure por `"ingest-attachment"` na lista de plugins de cada nó.
Se não estiver presente, o plugin precisa ser instalado no cluster ES:

```bash
bin/elasticsearch-plugin install ingest-attachment
```

---

## Criar o pipeline

```bash
curl -X PUT \
  -H "Content-Type: application/json" \
  -H "Authorization: Basic ZWxhc3RpYzpTWFR0NHJrMDV1RHE=" \
  "https://elastic.pnld-avaliacao-dev.nees.ufal.br/_ingest/pipeline/attachment" \
  -d '{
    "description": "Extrair texto de anexos PDF",
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
  }'
```

### O que o pipeline faz:

1. **attachment processor**: Recebe o campo `data` (PDF codificado em base64) e extrai o conteúdo textual para `attachment.content`, metadados para `attachment.title`, `attachment.content_length`, etc.
2. **remove processor**: Remove o campo `data` após a extração para não armazenar o base64 permanentemente (economia de storage).

`indexed_chars: -1` = sem limite de caracteres extraídos (extrai o documento inteiro).

---

## Verificar se o pipeline foi criado

```bash
curl -H "Authorization: Basic ZWxhc3RpYzpTWFR0NHJrMDV1RHE=" \
  "https://elastic.pnld-avaliacao-dev.nees.ufal.br/_ingest/pipeline/attachment"
```

---

## Exemplo de uso (indexar documento com pipeline)

```bash
curl -X POST \
  -H "Content-Type: application/json" \
  -H "Authorization: Basic ZWxhc3RpYzpTWFR0NHJrMDV1RHE=" \
  "https://elastic.pnld-avaliacao-dev.nees.ufal.br/artefatos/_doc?pipeline=attachment" \
  -d '{
    "data": "<BASE64_DO_PDF_AQUI>",
    "filename": "resolucao_001_2025.pdf",
    "artefato": {
      "artefato_id": "res-001-2025",
      "titulo": "Resolução nº 001/2025",
      "tipo": "resolucao"
    }
  }'
```

Após a indexação, o documento terá:
- `attachment.content` — texto completo extraído do PDF
- `attachment.title` — título extraído dos metadados do PDF (se disponível)
- `attachment.content_length` — tamanho do conteúdo extraído
- Campo `data` removido (não armazenado)

---

## Testar o pipeline isoladamente (simulate)

```bash
curl -X POST \
  -H "Content-Type: application/json" \
  -H "Authorization: Basic ZWxhc3RpYzpTWFR0NHJrMDV1RHE=" \
  "https://elastic.pnld-avaliacao-dev.nees.ufal.br/_ingest/pipeline/attachment/_simulate" \
  -d '{
    "docs": [
      {
        "_source": {
          "data": "<BASE64_DO_PDF_AQUI>"
        }
      }
    ]
  }'
```
