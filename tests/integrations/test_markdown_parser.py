"""
===============================================================================
Tests : MarkdownParser
===============================================================================
Objectif :
    Parser les cours d'exemple et refuser un fichier vide.

Lot :
    B (ingestion)
===============================================================================
"""

from pathlib import Path

import pytest

from backend.domain.chapter_detection import detect_chapters
from backend.domain.enums import ExtractionErrorCode
from backend.domain.errors import ExtractionError
from backend.integrations.parsers.markdown_parser import MarkdownParser

FIXTURES = Path(__file__).resolve().parents[1] / "fixtures" / "documents"


@pytest.mark.parametrize(
    ("filename", "expected_chapters"),
    [
        ("machine-learning.md", 5),
        ("statistics.md", 4),
        ("cloud-mlops.md", 3),
        ("nested-headings.md", 3),
    ],
)
def test_markdown_parser_detects_expected_chapter_count(
    filename: str,
    expected_chapters: int,
) -> None:
    parsed = MarkdownParser().parse(FIXTURES / filename)
    chapters = detect_chapters(parsed)

    assert len(chapters) == expected_chapters
    assert chapters[0].position == 0
    assert all(c.word_count > 0 for c in chapters)


def test_markdown_parser_empty_file_raises_empty_text() -> None:
    with pytest.raises(ExtractionError) as exc_info:
        MarkdownParser().parse(FIXTURES / "empty.md")

    assert exc_info.value.error_code == ExtractionErrorCode.EMPTY_TEXT
    assert exc_info.value.code == "EXTRACTION_FAILED"


def test_markdown_parser_machine_learning_titles() -> None:
    parsed = MarkdownParser().parse(FIXTURES / "machine-learning.md")
    titles = [c.title for c in detect_chapters(parsed)]

    assert titles[0] == "Chapter 1 — The ML workflow"
    assert titles[-1] == "Chapter 5 — Model deployment"
