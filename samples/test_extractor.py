"""
Test the PDF extractor with sample files.

Run: python samples/test_extractor.py
"""

import os
import sys

# Ensure project root is in path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core.pdf_extractor import extract_pdf_text


def test_extract_from_file(filepath: str) -> None:
    """Test extraction from a single PDF file."""
    filename = os.path.basename(filepath)
    print(f"\n{'='*60}")
    print(f"Testing: {filename}")
    print(f"{'='*60}")

    if not os.path.exists(filepath):
        print(f"  ⚠ File not found: {filepath}")
        print("  → Run 'python samples/generate_sample_pdfs.py' first")
        return

    with open(filepath, "rb") as f:
        content = f.read()

    print(f"  File size: {len(content)} bytes")

    text = extract_pdf_text(content)

    if text:
        print(f"  Extracted text length: {len(text)} chars")
        print(f"  Preview (first 200 chars):")
        print(f"  ---")
        print(f"  {text[:200]}")
        print(f"  ---")
        print(f"  ✓ Extraction successful")
    else:
        print(f"  ✗ No text extracted")


def test_empty_bytes() -> None:
    """Test extraction with empty/invalid content."""
    print(f"\n{'='*60}")
    print("Testing: Empty bytes (should return empty string)")
    print(f"{'='*60}")

    text = extract_pdf_text(b"")
    assert text == "", f"Expected empty string, got: {text!r}"
    print("  ✓ Empty bytes → empty string")


def test_invalid_pdf() -> None:
    """Test extraction with invalid PDF content."""
    print(f"\n{'='*60}")
    print("Testing: Invalid PDF (random bytes)")
    print(f"{'='*60}")

    text = extract_pdf_text(b"This is not a PDF file at all")
    assert text == "", f"Expected empty string, got: {text!r}"
    print("  ✓ Invalid PDF → empty string (graceful handling)")


def main():
    samples_dir = os.path.dirname(os.path.abspath(__file__))

    print("=" * 60)
    print("PDF Extractor Test Suite")
    print("=" * 60)

    # Test edge cases
    test_empty_bytes()
    test_invalid_pdf()

    # Test with sample PDFs
    sample_files = [
        "documento_institucional.pdf",
        "edital_selecao.pdf",
        "plano_ensino_programacao.pdf",
    ]

    for filename in sample_files:
        filepath = os.path.join(samples_dir, filename)
        test_extract_from_file(filepath)

    print(f"\n{'='*60}")
    print("All tests completed!")
    print(f"{'='*60}")


if __name__ == "__main__":
    main()
