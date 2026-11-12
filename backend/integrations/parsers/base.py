"""
===============================================================================
Intégration : DocumentParser (Protocol) et ParserRegistry
===============================================================================
Objectif :
    Définir le contrat commun des parseurs et le registre qui les sélectionne
    par DocumentType, sans if/elif dans IngestionService (OCP, diagramme §3).

Responsabilités :
    - supports() pur : aucun accès disque.
    - parse() renvoie toujours un ParsedDocument, ou lève ExtractionError.

Utilisé par :
    IngestionService, PdfParser, MarkdownParser

Lot :
    B (ingestion)
===============================================================================
"""

from pathlib import Path
from typing import Protocol, Sequence

from backend.domain.documents import ParsedDocument
from backend.domain.enums import DocumentType
from backend.domain.errors import UnsupportedFileTypeError


# =============================================================================
# Types
# =============================================================================


class DocumentParser(Protocol):
    """Lit un fichier et renvoie un ParsedDocument (contrat LSP)."""

    def supports(self, file_type: DocumentType) -> bool:
        """Indique si ce parseur prend en charge le type donné."""

    def parse(self, path: Path) -> ParsedDocument:
        """Extrait le texte structuré.

        Raises:
            ExtractionError: Fichier vide, scanné, illisible ou trop long.
        """


# =============================================================================
# API publique
# =============================================================================


class ParserRegistry:
    """Choisit le parseur d'après DocumentType."""

    def __init__(self, parsers: Sequence[DocumentParser]) -> None:
        self._parsers = list(parsers)

    def for_type(self, file_type: DocumentType) -> DocumentParser:
        """Retourne le premier parseur qui supporte le type.

        Raises:
            UnsupportedFileTypeError: Aucun parseur pour ce type.
        """
        for parser in self._parsers:
            if parser.supports(file_type):
                return parser
        raise UnsupportedFileTypeError(f"Aucun parseur pour {file_type.value}")
