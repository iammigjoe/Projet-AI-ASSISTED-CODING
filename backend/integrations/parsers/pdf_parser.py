"""
===============================================================================
Intégration : PdfParser
===============================================================================
Objectif :
    Extraire texte, titres et signets d'un PDF avec pypdf (P0-04, bloc 1).

Responsabilités :
    - Remplir blocks (texte + taille de police) et outline (signets).
    - Lever INVALID_BYTES, EMPTY_TEXT, SCANNED_PDF ou TIMEOUT selon le cas.
    - Respecter une limite de temps et de pages (PDF piégés).

Utilisé par :
    ParserRegistry, IngestionService

Lève :
    ExtractionError

Exemple d'utilisation :
    parsed = PdfParser().parse(Path("cours.pdf"))

Notes :
    Écrit d'abord avec PyMuPDF par le lot B, porté sur pypdf (recommandé par
    le sujet ; PyMuPDF est sous licence AGPL) sans changer le contrat : mêmes
    blocs, mêmes niveaux de titre, mêmes codes d'erreur, mêmes tests.

Lot :
    B (ingestion)
===============================================================================
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from pypdf import PdfReader
from pypdf.errors import PyPdfError

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
# Deux fragments dont la ligne de base diffère de moins que ceci sont sur la même ligne.
SAME_LINE_TOLERANCE = 2.0


# =============================================================================
# Types
# =============================================================================


@dataclass
class _Line:
    """Ligne de texte reconstituée à partir des fragments de pypdf."""

    baseline: float
    parts: list[str] = field(default_factory=list)
    font_size: float = 0.0


# =============================================================================
# API publique
# =============================================================================


class PdfParser:
    """Parseur PDF basé sur pypdf."""

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
            reader = PdfReader(path)
            page_count = len(reader.pages)
        except (PyPdfError, OSError, ValueError) as exc:
            raise ExtractionError(ExtractionErrorCode.INVALID_BYTES, "PDF illisible") from exc

        if page_count == 0:
            raise ExtractionError(ExtractionErrorCode.EMPTY_TEXT)
        if page_count > self._max_pages:
            raise ExtractionError(ExtractionErrorCode.TIMEOUT, "PDF trop long")

        outline = _read_outline(reader)
        blocks: list[TextBlock] = []
        total_chars = 0

        for page_index, page in enumerate(reader.pages):
            if time.monotonic() - started > self._timeout_sec:
                raise ExtractionError(ExtractionErrorCode.TIMEOUT)
            page_blocks, page_chars = _blocks_from_page(page, page_index + 1)
            blocks.extend(page_blocks)
            total_chars += page_chars

        if total_chars == 0:
            # Aucun texte extractible : scan probable (OCR = P3).
            raise ExtractionError(ExtractionErrorCode.SCANNED_PDF)

        if total_chars / page_count < MIN_CHARS_PER_PAGE and not outline:
            raise ExtractionError(ExtractionErrorCode.SCANNED_PDF)

        if not blocks:
            raise ExtractionError(ExtractionErrorCode.EMPTY_TEXT)

        return ParsedDocument(blocks=tuple(blocks), outline=tuple(outline))


# =============================================================================
# Fonctions internes
# =============================================================================


def _read_outline(reader: PdfReader) -> list[OutlineEntry]:
    """Convertit les signets en OutlineEntry (niveau d'imbrication, pages 1-indexées)."""
    entries: list[OutlineEntry] = []

    def walk(items: list[Any], level: int) -> None:
        for item in items:
            if isinstance(item, list):
                walk(item, level + 1)
                continue
            title = str(getattr(item, "title", "") or "").strip()
            try:
                page = reader.get_destination_page_number(item) + 1
            except (PyPdfError, KeyError, TypeError, ValueError):
                continue
            if title and page >= 1:
                entries.append(OutlineEntry(title=title, level=level, page=page))

    try:
        walk(reader.outline, 1)
    except PyPdfError:
        return []
    return entries


def _blocks_from_page(page: Any, page_number: int) -> tuple[list[TextBlock], int]:
    """Extrait des TextBlock, une ligne par bloc, avec sa plus grande taille de police."""
    lines: list[_Line] = []

    def visitor(text: str, cm: Any, tm: Any, _font_dict: Any, font_size: float) -> None:
        if not text.strip():
            return
        baseline = float(tm[5]) if tm else 0.0
        # Taille réelle = taille de police × échelle verticale de la matrice de texte.
        scale = abs(float(tm[3])) if tm and tm[3] else 1.0
        scale *= abs(float(cm[3])) if cm and cm[3] else 1.0
        size = float(font_size or 0.0) * scale
        line = next((ln for ln in lines if abs(ln.baseline - baseline) < SAME_LINE_TOLERANCE), None)
        if line is None:
            line = _Line(baseline=baseline)
            lines.append(line)
        line.parts.append(text.strip())
        line.font_size = max(line.font_size, size)

    page.extract_text(visitor_text=visitor)

    blocks: list[TextBlock] = []
    chars = 0
    for line in lines:
        text = " ".join(line.parts).strip()
        if not text:
            continue
        chars += len(text)
        font_size = line.font_size or None
        blocks.append(
            TextBlock(
                text=text,
                heading_level=_guess_heading_level(font_size, text),
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
