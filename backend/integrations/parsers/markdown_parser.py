"""
===============================================================================
Intégration : MarkdownParser
===============================================================================
Objectif :
    Transformer un fichier Markdown en ParsedDocument (titres # / ## / ###
    et paragraphes), sans décider encore ce qui est un chapitre.

Responsabilités :
    - Lire le fichier avec une limite de temps.
    - Mapper les titres ATX (heading_level = nombre de #).
    - Lever EMPTY_TEXT si le fichier ne contient aucun texte utile.

Dépendances :
    pathlib uniquement (pas de markdown-it : un parseur ligne à ligne
    suffit pour # / ## et évite une dépendance lourde pour le MVP).

Utilisé par :
    ParserRegistry, IngestionService

Lève :
    ExtractionError (EMPTY_TEXT, TIMEOUT)

Exemple d'utilisation :
    parsed = MarkdownParser().parse(Path("cours.md"))

Lot :
    B (ingestion)
===============================================================================
"""

from __future__ import annotations

import time
from pathlib import Path

from backend.domain.documents import ParsedDocument, TextBlock
from backend.domain.enums import DocumentType, ExtractionErrorCode
from backend.domain.errors import ExtractionError

# =============================================================================
# Constantes
# =============================================================================

DEFAULT_TIMEOUT_SEC = 5.0


# =============================================================================
# API publique
# =============================================================================


class MarkdownParser:
    """Parseur Markdown : titres ATX et paragraphes."""

    def __init__(self, timeout_sec: float = DEFAULT_TIMEOUT_SEC) -> None:
        self._timeout_sec = timeout_sec

    def supports(self, file_type: DocumentType) -> bool:
        """True uniquement pour DocumentType.MARKDOWN."""
        return file_type is DocumentType.MARKDOWN

    def parse(self, path: Path) -> ParsedDocument:
        """Lit ``path`` et construit un ParsedDocument.

        Args:
            path: Chemin du fichier Markdown déjà stocké sous un UUID.

        Returns:
            Blocs ordonnés ; outline vide (le Markdown n'a pas de signets).

        Raises:
            ExtractionError: EMPTY_TEXT ou TIMEOUT.
        """
        started = time.monotonic()
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError as exc:
            raise ExtractionError(
                ExtractionErrorCode.INVALID_BYTES,
                "Le fichier Markdown n'est pas en UTF-8",
            ) from exc

        if time.monotonic() - started > self._timeout_sec:
            raise ExtractionError(ExtractionErrorCode.TIMEOUT)

        blocks = _blocks_from_markdown(text)
        if not blocks or all(not b.text.strip() for b in blocks):
            raise ExtractionError(ExtractionErrorCode.EMPTY_TEXT)

        if time.monotonic() - started > self._timeout_sec:
            raise ExtractionError(ExtractionErrorCode.TIMEOUT)

        return ParsedDocument(blocks=tuple(blocks), outline=())


# =============================================================================
# Fonctions internes
# =============================================================================


def _blocks_from_markdown(text: str) -> list[TextBlock]:
    """Découpe le Markdown en TextBlock (ATX headings + paragraphes)."""
    blocks: list[TextBlock] = []
    paragraph_lines: list[str] = []

    def flush_paragraph() -> None:
        if not paragraph_lines:
            return
        body = "\n".join(paragraph_lines).strip()
        paragraph_lines.clear()
        if body:
            blocks.append(TextBlock(text=body, heading_level=None))

    for line in text.splitlines():
        heading = _parse_atx_heading(line)
        if heading is not None:
            flush_paragraph()
            level, title = heading
            blocks.append(TextBlock(text=title, heading_level=level))
            continue
        if not line.strip():
            flush_paragraph()
            continue
        paragraph_lines.append(line)

    flush_paragraph()
    return blocks


def _parse_atx_heading(line: str) -> tuple[int, str] | None:
    """Retourne (niveau, titre) pour une ligne ``## Titre``, sinon None."""
    stripped = line.lstrip()
    if not stripped.startswith("#"):
        return None
    level = 0
    for char in stripped:
        if char != "#":
            break
        level += 1
    if level < 1 or level > 6:
        return None
    # Un titre ATX exige un espace (ou fin) après les dièses.
    rest = stripped[level:]
    if rest and not rest[0].isspace():
        return None
    title = rest.strip().rstrip("#").strip()
    if not title:
        return None
    return level, title
