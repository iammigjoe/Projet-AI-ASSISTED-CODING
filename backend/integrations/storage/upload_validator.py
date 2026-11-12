"""
===============================================================================
Intégration : UploadValidator
===============================================================================
Objectif :
    Contrôler taille et type réel (magic bytes) d'un fichier uploadé (P0-03).

Responsabilités :
    - Refuser au-delà de MYPLAN_MAX_UPLOAD_BYTES.
    - Déduire DocumentType des octets, jamais de l'extension seule.
    - Accepter seulement PDF (%PDF) et Markdown (texte UTF-8 plausible).

Utilisé par :
    IngestionService

Lève :
    FileTooLargeError, UnsupportedFileTypeError, ExtractionError

Exemple d'utilisation :
    document_type = UploadValidator(20_971_520).validate(header, size)

Lot :
    B (ingestion)
===============================================================================
"""

from __future__ import annotations

from backend.domain.enums import DocumentType, ExtractionErrorCode
from backend.domain.errors import (
    ExtractionError,
    FileTooLargeError,
    UnsupportedFileTypeError,
)

# =============================================================================
# Constantes
# =============================================================================

PDF_MAGIC = b"%PDF"
HEADER_WINDOW = 16
MARKDOWN_SAMPLE = 4096


# =============================================================================
# API publique
# =============================================================================


class UploadValidator:
    """Valide taille et magic bytes ; ne lit jamais l'extension seule."""

    def __init__(self, max_upload_bytes: int) -> None:
        if max_upload_bytes <= 0:
            raise ValueError("max_upload_bytes doit être > 0")
        self._max_upload_bytes = max_upload_bytes

    def validate(self, header_bytes: bytes, size: int) -> DocumentType:
        """Contrôle la taille et déduit le DocumentType.

        Args:
            header_bytes: Premiers octets du fichier.
            size: Taille totale annoncée, en octets.

        Returns:
            DocumentType.PDF ou DocumentType.MARKDOWN.

        Raises:
            FileTooLargeError: Taille au-delà de la limite.
            UnsupportedFileTypeError: Type hors liste blanche.
            ExtractionError: Fichier vide.
        """
        if size <= 0:
            raise ExtractionError(
                ExtractionErrorCode.EMPTY_TEXT,
                "Fichier vide",
            )
        if size > self._max_upload_bytes:
            raise FileTooLargeError()
        return detect_document_type(header_bytes)


def detect_document_type(header_bytes: bytes) -> DocumentType:
    """Déduit le type réel à partir des premiers octets.

    Raises:
        UnsupportedFileTypeError: Type hors liste blanche.
    """
    if header_bytes.startswith(PDF_MAGIC):
        return DocumentType.PDF

    sample = header_bytes[:MARKDOWN_SAMPLE]
    if b"\x00" in sample:
        raise UnsupportedFileTypeError("Contenu binaire non autorisé")
    try:
        sample.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise UnsupportedFileTypeError("Le fichier n'est ni un PDF ni du texte UTF-8") from exc

    return DocumentType.MARKDOWN
