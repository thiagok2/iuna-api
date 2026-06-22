"""
PDF text extraction utility.

ESTRATÉGIA DE EXTRAÇÃO DE TEXTO:

    Primária: Elasticsearch Ingest Attachment Pipeline (Apache Tika)
    ─────────────────────────────────────────────────────────────────
    A extração principal de texto é feita pelo Elasticsearch durante a indexação.
    O PDF é enviado como base64 no campo "data" e o pipeline "attachment_pipeline"
    (configurado no ES) extrai o texto automaticamente para "attachment.content".

    Vantagens:
    - Suporte robusto a PDFs diversos (OCR, caracteres especiais, layouts complexos)
    - Baseado em Apache Tika (mesma engine usada pelo Solr, Alfresco, etc.)
    - Não requer dependências Python pesadas no container da API
    - Processamento server-side no cluster ES

    Fallback: pdfplumber / PyPDF2 (extração local)
    ────────────────────────────────────────────────
    Usado apenas quando o ES não está disponível ou para testes locais.
    Mantido como fallback para cenários offline ou debugging.

Fluxo de indexação:
    1. API recebe PDF (multipart upload)
    2. Codifica para base64
    3. Envia ao ES com pipeline=attachment_pipeline:
       {"data": "<base64>", "ato": {...}, "filename": "..."}
    4. ES extrai texto → attachment.content é populado automaticamente
    5. O campo "data" é removido após extração (não armazena base64 permanentemente)
"""

import io
import logging

logger = logging.getLogger(__name__)


def extract_pdf_text(file_content: bytes) -> str:
    """
    Extract text content from a PDF file using local libraries.

    NOTA: Este método é um FALLBACK. A estratégia primária é o ES Ingest
    Attachment Pipeline (Apache Tika), usado durante a indexação.
    Use esta função apenas quando o ES não estiver disponível ou para testes.

    Args:
        file_content: Raw bytes of the PDF file.

    Returns:
        Extracted text as a single string. Returns empty string if extraction fails.
    """
    text = _extract_with_pdfplumber(file_content)
    if text:
        return text

    logger.info("pdfplumber extraction yielded no text, trying PyPDF2 fallback")
    text = _extract_with_pypdf2(file_content)
    return text


def _extract_with_pdfplumber(file_content: bytes) -> str:
    """Extract text using pdfplumber (local fallback - primary method)."""
    try:
        import pdfplumber

        pages_text: list[str] = []
        with pdfplumber.open(io.BytesIO(file_content)) as pdf:
            for page in pdf.pages:
                page_text = page.extract_text()
                if page_text:
                    pages_text.append(page_text)
        return "\n\n".join(pages_text)
    except Exception as exc:
        logger.warning("pdfplumber extraction failed: %s", exc)
        return ""


def _extract_with_pypdf2(file_content: bytes) -> str:
    """Extract text using PyPDF2 (local fallback - secondary method)."""
    try:
        from PyPDF2 import PdfReader

        reader = PdfReader(io.BytesIO(file_content))
        pages_text: list[str] = []
        for page in reader.pages:
            page_text = page.extract_text()
            if page_text:
                pages_text.append(page_text)
        return "\n\n".join(pages_text)
    except Exception as exc:
        logger.warning("PyPDF2 extraction failed: %s", exc)
        return ""
