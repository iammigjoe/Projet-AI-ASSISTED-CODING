"""
===============================================================================
Tests : PdfParser
===============================================================================
Objectif :
    Vérifier signets, PDF vide, PDF scanné et faux PDF.

Lot :
    B (ingestion)
===============================================================================
"""

from pathlib import Path

import pytest

from backend.domain.chapter_detection import detect_chapters
from backend.domain.enums import ExtractionErrorCode
from backend.domain.errors import ExtractionError
from backend.integrations.parsers.pdf_parser import PdfParser

FIXTURES = Path(__file__).resolve().parents[1] / "fixtures" / "documents"


def test_pdf_parser_with_bookmarks_detects_chapters() -> None:
    parsed = PdfParser().parse(FIXTURES / "with-bookmarks.pdf")
    chapters = detect_chapters(parsed)

    assert len(parsed.outline) == 2
    assert [c.title for c in chapters] == [
        "Chapter 1 — Workflow",
        "Chapter 2 — Metrics",
    ]


def test_pdf_parser_empty_raises_scanned_or_empty() -> None:
    with pytest.raises(ExtractionError) as exc_info:
        PdfParser().parse(FIXTURES / "empty.pdf")

    assert exc_info.value.error_code in {
        ExtractionErrorCode.EMPTY_TEXT,
        ExtractionErrorCode.SCANNED_PDF,
    }


def test_pdf_parser_scanned_raises_scanned_pdf() -> None:
    with pytest.raises(ExtractionError) as exc_info:
        PdfParser().parse(FIXTURES / "scanned-no-text.pdf")

    assert exc_info.value.error_code == ExtractionErrorCode.SCANNED_PDF


def test_pdf_parser_fake_pdf_raises_invalid_bytes() -> None:
    with pytest.raises(ExtractionError) as exc_info:
        PdfParser().parse(FIXTURES / "fake.pdf")

    assert exc_info.value.error_code == ExtractionErrorCode.INVALID_BYTES


def test_pdf_parser_no_bookmarks_still_parses_text() -> None:
    parsed = PdfParser().parse(FIXTURES / "no-bookmarks.pdf")

    assert parsed.outline == ()
    assert len(parsed.blocks) >= 2
    assert any(b.heading_level == 1 for b in parsed.blocks)
