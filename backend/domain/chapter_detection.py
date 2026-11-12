"""
===============================================================================
Domaine : chapter_detection
===============================================================================
Objectif :
    Décider quels blocs d'un ParsedDocument forment des chapitres, sans
    ouvrir de fichier (P0-05).

Responsabilités :
    - Si une outline (signets PDF) existe : un entrée de niveau 1 = un chapitre.
    - Sinon Markdown / heuristique : titres de niveau 2 (##) deviennent des
      chapitres ; le titre de niveau 1 (#) est le nom du document, pas un
      chapitre.
    - Compter les mots du corps de chaque chapitre.
    - Renseigner page_start / page_end quand les pages sont connues.

Pur :
    Ni base, ni réseau, ni horloge, ni lecture de fichier.

Utilisé par :
    IngestionService

Exemple d'utilisation :
    chapters = detect_chapters(parsed)

Lot :
    B (ingestion)
===============================================================================
"""

from __future__ import annotations

from backend.domain.documents import (
    DetectedChapter,
    OutlineEntry,
    ParsedDocument,
    TextBlock,
)

# =============================================================================
# API publique
# =============================================================================


def detect_chapters(document: ParsedDocument) -> list[DetectedChapter]:
    """Détecte une liste ordonnée de chapitres dans un document déjà parsé.

    Args:
        document: Sortie d'un DocumentParser.

    Returns:
        Chapitres ordonnés (position 0..n-1). Liste vide si aucun titre
        de chapitre n'est trouvé (l'étudiant corrigera en P0-06).
    """
    if document.outline:
        return _from_outline(document)
    return _from_heading_blocks(document.blocks)


# =============================================================================
# Fonctions internes
# =============================================================================


def _word_count(text: str) -> int:
    """Compte les mots (séparés par des blancs)."""
    return len(text.split())


def _from_outline(document: ParsedDocument) -> list[DetectedChapter]:
    """Chapitres à partir des signets de niveau 1."""
    level_one = [e for e in document.outline if e.level == 1]
    if not level_one:
        # Outline présente mais sans niveau 1 : repli sur les titres du corps.
        return _from_heading_blocks(document.blocks)

    chapters: list[DetectedChapter] = []
    for index, entry in enumerate(level_one):
        page_end = _page_end_for_outline(level_one, index, document)
        body = _text_between_pages(
            document.blocks,
            page_start=entry.page,
            page_end=page_end,
            exclude_title=entry.title,
        )
        chapters.append(
            DetectedChapter(
                title=entry.title,
                position=index,
                word_count=_word_count(body),
                page_start=entry.page,
                page_end=page_end,
            )
        )
    return chapters


def _page_end_for_outline(
    level_one: list[OutlineEntry],
    index: int,
    document: ParsedDocument,
) -> int:
    """Dernière page du chapitre : page avant le signet suivant, ou max du doc."""
    if index + 1 < len(level_one):
        return max(level_one[index].page, level_one[index + 1].page - 1)
    pages = [b.page for b in document.blocks if b.page is not None]
    if pages:
        return max(pages)
    return level_one[index].page


def _text_between_pages(
    blocks: tuple[TextBlock, ...],
    *,
    page_start: int,
    page_end: int,
    exclude_title: str,
) -> str:
    """Concatène le corps entre page_start et page_end, hors titre du chapitre."""
    parts: list[str] = []
    for block in blocks:
        if block.page is None:
            continue
        if block.page < page_start or block.page > page_end:
            continue
        if block.heading_level is not None and block.text.strip() == exclude_title:
            continue
        if block.heading_level is not None:
            continue
        parts.append(block.text)
    return "\n".join(parts)


def _from_heading_blocks(blocks: tuple[TextBlock, ...]) -> list[DetectedChapter]:
    """Chapitres à partir des titres ## (niveau 2), typique Markdown.

    S'il n'y a que des titres de niveau 1, chacun devient un chapitre
    (heuristique PDF sans signets).
    """
    level_two_indexes = [i for i, b in enumerate(blocks) if b.heading_level == 2]
    if level_two_indexes:
        return _chapters_from_indexes(blocks, level_two_indexes)

    level_one_indexes = [i for i, b in enumerate(blocks) if b.heading_level == 1]
    # Un seul # en tête (titre du document) ne forme pas un chapitre seul :
    # on attend des ##. S'il y a plusieurs #, heuristique PDF.
    if len(level_one_indexes) >= 2:
        return _chapters_from_indexes(blocks, level_one_indexes)

    return []


def _chapters_from_indexes(
    blocks: tuple[TextBlock, ...],
    heading_indexes: list[int],
) -> list[DetectedChapter]:
    """Construit les chapitres entre titres successifs."""
    chapters: list[DetectedChapter] = []
    for position, start in enumerate(heading_indexes):
        end = heading_indexes[position + 1] if position + 1 < len(heading_indexes) else len(blocks)
        title_block = blocks[start]
        body_parts = [b.text for b in blocks[start + 1 : end] if b.heading_level is None]
        body = "\n".join(body_parts)
        page_numbers = [b.page for b in blocks[start:end] if b.page is not None]
        chapters.append(
            DetectedChapter(
                title=title_block.text,
                position=position,
                word_count=_word_count(body),
                page_start=min(page_numbers) if page_numbers else None,
                page_end=max(page_numbers) if page_numbers else None,
            )
        )
    return chapters
