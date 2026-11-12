"""
===============================================================================
Tests : chapter_detection
===============================================================================
Objectif :
    Vérifier la détection Markdown (##) et le repli sur les signets PDF.

Lot :
    B (ingestion)
===============================================================================
"""

from backend.domain.chapter_detection import detect_chapters
from backend.domain.documents import OutlineEntry, ParsedDocument, TextBlock


def test_detect_chapters_markdown_level_two_titles() -> None:
    document = ParsedDocument(
        blocks=(
            TextBlock(text="Machine Learning", heading_level=1),
            TextBlock(text="Chapter 1 — The ML workflow", heading_level=2),
            TextBlock(text="Define the problem collect data"),
            TextBlock(text="Chapter 2 — Metrics", heading_level=2),
            TextBlock(text="Precision recall F1"),
        )
    )

    chapters = detect_chapters(document)

    assert len(chapters) == 2
    assert chapters[0].title == "Chapter 1 — The ML workflow"
    assert chapters[0].position == 0
    assert chapters[0].word_count == 5
    assert chapters[1].title == "Chapter 2 — Metrics"
    assert chapters[1].word_count == 3


def test_detect_chapters_prefers_outline_level_one() -> None:
    document = ParsedDocument(
        blocks=(
            TextBlock(text="Intro body", page=1),
            TextBlock(text="More body", page=2),
        ),
        outline=(
            OutlineEntry(title="Intro", level=1, page=1),
            OutlineEntry(title="Next", level=1, page=2),
        ),
    )

    chapters = detect_chapters(document)

    assert [c.title for c in chapters] == ["Intro", "Next"]
    assert chapters[0].page_start == 1
    assert chapters[1].page_start == 2


def test_detect_chapters_empty_when_only_document_title() -> None:
    document = ParsedDocument(
        blocks=(
            TextBlock(text="Only title", heading_level=1),
            TextBlock(text="Some paragraph without chapter headings"),
        )
    )

    assert detect_chapters(document) == []
