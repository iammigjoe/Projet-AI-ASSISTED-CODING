"""
===============================================================================
Intégration : PdfParser
===============================================================================
Objectif :
    Extraire texte, titres et signets d'un PDF via PyMuPDF (P0-04).

Responsabilités :
    - Remplir blocks (texte + taille de police) et outline (table des matières).
    - Lever EMPTY_TEXT, SCANNED_PDF ou TIMEOUT selon le cas.
    - Respecter une limite de temps et de pages (PDF piégés).

Utilisé par :
    ParserRegistry, IngestionService

Lève :
    ExtractionError

Exemple d'utilisation :
    parsed = PdfParser().parse(Path("cours.pdf"))

Lot :
    B (ingestion)
===============================================================================
"""

from __future__ import annotations

import time
from pathlib import Path

import fitz

from backend.domain.documents import OutlineEntry, ParsedDocument, TextBlock
from backend.domain.enums import DocumentType, ExtractionErrorCode
from backend.domain.errors import ExtractionError

# =============================================================================
# Constantes
# =============================================================================

DEFAULT_TIMEOUT_SEC = 15.0
MAX_PAGES = 500  # au-delà, PDF probablement piégé
# En dessous de ce ratio caractères / page, on considère un scan sans OCR.
MIN_CHARS_PER_PAGE = 20


# =============================================================================
# API publique
# =============================================================================


class PdfParser:
    """Parseur PDF basé sur PyMuPDF."""

    def __init__(
        self,
        timeout_sec: float = DEFAULT_TIMEOUT_SEC,
        max_pages: int = MAX_PAGES,
    ) -> None:
        self._timeout_sec = timeout_sec
        self._max_pages = max_pages

    def supports(self, file_type: DocumentType) -> bool:
        """True uniquement pour DocumentType.PDF."""
        return file_type is DocumentType.PDF

    def parse(self, path: Path) -> ParsedDocument:
        """Ouvre le PDF et construit un ParsedDocument.

        Raises:
            ExtractionError: INVALID_BYTES, TIMEOUT, EMPTY_TEXT, SCANNED_PDF.
        """
        started = time.monotonic()
        try:
            document = fitz.open(path)
        except Exception as exc:  # noqa: BLE001 — PyMuPDF lève plusieurs types
            raise ExtractionError(
                ExtractionErrorCode.INVALID_BYTES,
                "PDF illisible",
            ) from exc

        try:
            if document.page_count == 0:
                raise ExtractionError(ExtractionErrorCode.EMPTY_TEXT)
            if document.page_count > self._max_pages:
                raise ExtractionError(
                    ExtractionErrorCode.TIMEOUT,
                    "PDF trop long",
                )

            outline = _read_outline(document)
            blocks: list[TextBlock] = []
            total_chars = 0

            for page_index in range(document.page_count):
                if time.monotonic() - started > self._timeout_sec:
                    raise ExtractionError(ExtractionErrorCode.TIMEOUT)
                page = document.load_page(page_index)
                page_number = page_index + 1
                page_blocks, page_chars = _blocks_from_page(page, page_number)
                blocks.extend(page_blocks)
                total_chars += page_chars

            if total_chars == 0:
                # Aucun texte extractible : scan probable (OCR = P3).
                raise ExtractionError(ExtractionErrorCode.SCANNED_PDF)

            avg = total_chars / document.page_count
            if avg < MIN_CHARS_PER_PAGE and not outline:
                raise ExtractionError(ExtractionErrorCode.SCANNED_PDF)

            if not blocks:
                raise ExtractionError(ExtractionErrorCode.EMPTY_TEXT)

            return ParsedDocument(blocks=tuple(blocks), outline=tuple(outline))
        finally:
            document.close()


# =============================================================================
# Fonctions internes
# =============================================================================


def _read_outline(document: fitz.Document) -> list[OutlineEntry]:
    """Convertit la TOC PyMuPDF en OutlineEntry (pages 1-indexées)."""
    entries: list[OutlineEntry] = []
    for item in document.get_toc(simple=True):
        # item = [level, title, page]
        if len(item) < 3:
            continue
        level, title, page = item[0], str(item[1]).strip(), int(item[2])
        if not title or page < 1:
            continue
        entries.append(OutlineEntry(title=title, level=level, page=page))
    return entries


def _blocks_from_page(page: fitz.Page, page_number: int) -> tuple[list[TextBlock], int]:
    """Extrait des TextBlock à partir du dict de la page."""
    blocks: list[TextBlock] = []
    chars = 0
    payload = page.get_text("dict")
    for block in payload.get("blocks", []):
        if block.get("type") != 0:
            continue
        lines_text: list[str] = []
        sizes: list[float] = []
        for line in block.get("lines", []):
            spans = line.get("spans", [])
            line_parts = [span.get("text", "") for span in spans]
            line_text = "".join(line_parts).strip()
            if not line_text:
                continue
            lines_text.append(line_text)
            for span in spans:
                size = float(span.get("size", 0.0))
                if size > 0:
                    sizes.append(size)
        if not lines_text:
            continue
        text = "\n".join(lines_text)
        chars += len(text)
        font_size = max(sizes) if sizes else None
        heading_level = _guess_heading_level(font_size, text)
        blocks.append(
            TextBlock(
                text=text,
                heading_level=heading_level,
                page=page_number,
                font_size=font_size,
            )
        )
    return blocks, chars


def _guess_heading_level(font_size: float | None, text: str) -> int | None:
    """Heuristique simple : grosse police + ligne courte → titre."""
    if font_size is None:
        return None
    # Seuils empiriques : à affiner avec les PDF de test.
    if font_size >= 16 and len(text) <= 120:
        return 1
    if font_size >= 13 and len(text) <= 120:
        return 2
    return None
