"""
Generate sample PDF files for testing the PDF extractor.

Run: python samples/generate_sample_pdfs.py
"""

import os
import sys

# Ensure project root is in path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def generate_simple_pdf(filepath: str, title: str, content: str) -> None:
    """Generate a simple PDF using PyPDF2 (available in requirements)."""
    from PyPDF2 import PdfWriter
    from PyPDF2.generic import (
        ArrayObject,
        DecodedStreamObject,
        DictionaryObject,
        NameObject,
        NumberObject,
        TextStringObject,
    )

    # Create a minimal PDF with reportlab if available, otherwise use raw PDF stream
    try:
        from reportlab.lib.pagesizes import A4
        from reportlab.pdfgen import canvas
        import io

        buffer = io.BytesIO()
        c = canvas.Canvas(buffer, pagesize=A4)
        c.setFont("Helvetica-Bold", 16)
        c.drawString(72, 750, title)
        c.setFont("Helvetica", 12)

        # Write content line by line
        y = 720
        for line in content.split("\n"):
            if y < 72:
                c.showPage()
                c.setFont("Helvetica", 12)
                y = 750
            c.drawString(72, y, line)
            y -= 15

        c.save()
        with open(filepath, "wb") as f:
            f.write(buffer.getvalue())
        print(f"  ✓ Created (reportlab): {filepath}")

    except ImportError:
        # Fallback: create a minimal valid PDF manually
        _create_minimal_pdf(filepath, title, content)
        print(f"  ✓ Created (minimal): {filepath}")


def _create_minimal_pdf(filepath: str, title: str, content: str) -> None:
    """Create a minimal valid PDF file with embedded text."""
    # This creates a bare-minimum valid PDF with text content
    text = f"{title}\n\n{content}"
    # Escape special PDF characters
    text_escaped = text.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")

    stream_content = f"BT /F1 12 Tf 72 750 Td ({text_escaped}) Tj ET"
    stream_bytes = stream_content.encode("latin-1")

    pdf_content = (
        b"%PDF-1.4\n"
        b"1 0 obj<</Type/Catalog/Pages 2 0 R>>endobj\n"
        b"2 0 obj<</Type/Pages/Kids[3 0 R]/Count 1>>endobj\n"
        b"3 0 obj<</Type/Page/Parent 2 0 R/MediaBox[0 0 612 792]"
        b"/Contents 4 0 R/Resources<</Font<</F1 5 0 R>>>>>>endobj\n"
        b"4 0 obj<</Length " + str(len(stream_bytes)).encode() + b">>\n"
        b"stream\n" + stream_bytes + b"\nendstream\nendobj\n"
        b"5 0 obj<</Type/Font/Subtype/Type1/BaseFont/Helvetica>>endobj\n"
        b"xref\n0 6\n"
        b"0000000000 65535 f \n"
        b"0000000009 00000 n \n"
        b"0000000058 00000 n \n"
        b"0000000115 00000 n \n"
        b"0000000266 00000 n \n"
        b"0000000000 00000 n \n"
        b"trailer<</Size 6/Root 1 0 R>>\n"
        b"startxref\n0\n%%EOF\n"
    )

    with open(filepath, "wb") as f:
        f.write(pdf_content)


def main():
    samples_dir = os.path.dirname(os.path.abspath(__file__))

    print("Generating sample PDFs...")

    # Sample 1: Institutional document
    generate_simple_pdf(
        os.path.join(samples_dir, "documento_institucional.pdf"),
        "Resolução IFAL Nº 01/2024",
        (
            "RESOLUÇÃO Nº 01/2024 - CONSELHO SUPERIOR\n"
            "\n"
            "O REITOR DO INSTITUTO FEDERAL DE ALAGOAS, no uso de suas atribuições legais,\n"
            "considerando o disposto na Lei nº 11.892, de 29 de dezembro de 2008,\n"
            "RESOLVE:\n"
            "\n"
            "Art. 1º Aprovar o Regulamento dos Cursos de Graduação do IFAL.\n"
            "Art. 2º Esta resolução entra em vigor na data de sua publicação.\n"
            "\n"
            "Maceió, 15 de março de 2024.\n"
            "Prof. Dr. Carlos Guedes de Lacerda\n"
            "Reitor do IFAL"
        ),
    )

    # Sample 2: Edital
    generate_simple_pdf(
        os.path.join(samples_dir, "edital_selecao.pdf"),
        "Edital Nº 05/2024 - Seleção de Bolsistas",
        (
            "EDITAL Nº 05/2024\n"
            "SELEÇÃO DE BOLSISTAS PARA PROJETOS DE PESQUISA\n"
            "\n"
            "O Instituto Federal de Alagoas torna público o processo seletivo\n"
            "para concessão de bolsas de iniciação científica.\n"
            "\n"
            "1. DAS VAGAS\n"
            "Serão oferecidas 20 (vinte) vagas distribuídas entre os campi.\n"
            "\n"
            "2. DOS REQUISITOS\n"
            "- Estar regularmente matriculado em curso do IFAL\n"
            "- Ter disponibilidade de 20 horas semanais\n"
            "- Não acumular outra bolsa\n"
            "\n"
            "3. DAS INSCRIÇÕES\n"
            "Período: 01/04/2024 a 30/04/2024\n"
            "Local: Portal do Aluno - sistemas.ifal.edu.br"
        ),
    )

    # Sample 3: Generic artifact (plano de ensino)
    generate_simple_pdf(
        os.path.join(samples_dir, "plano_ensino_programacao.pdf"),
        "Plano de Ensino - Programação Web",
        (
            "PLANO DE ENSINO\n"
            "Disciplina: Programação Web\n"
            "Curso: Sistemas de Informação\n"
            "Carga Horária: 80h\n"
            "Professor: João Silva\n"
            "\n"
            "EMENTA:\n"
            "Desenvolvimento de aplicações web utilizando HTML, CSS, JavaScript.\n"
            "Frameworks modernos: React, Vue.js. APIs REST. Banco de dados.\n"
            "\n"
            "OBJETIVOS:\n"
            "- Desenvolver aplicações web responsivas\n"
            "- Implementar APIs RESTful\n"
            "- Integrar frontend com backend\n"
            "\n"
            "BIBLIOGRAFIA:\n"
            "- FLANAGAN, David. JavaScript: The Definitive Guide. O'Reilly, 2020.\n"
            "- FREEMAN, Adam. Pro ASP.NET Core. Apress, 2022."
        ),
    )

    print("\nDone! Sample PDFs created in samples/")


if __name__ == "__main__":
    main()
