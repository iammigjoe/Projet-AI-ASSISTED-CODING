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
# Extensions acceptées et type de contenu attendu pour chacune.
ALLOWED_EXTENSIONS = {
    ".pdf": DocumentType.PDF,
    ".md": DocumentType.MARKDOWN,
    ".markdown": DocumentType.MARKDOWN,
}


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


def check_extension(filename: str, file_type: DocumentType) -> None:
    """Vérifie que l'extension annoncée correspond au contenu réel.

    Le type vient toujours du contenu (magic bytes) ; l'extension sert seulement
    à refuser un fichier qui ment : un « .pdf » qui ne contient que du texte ne
    doit pas devenir une matière vide.

    Args:
        filename: Nom d'origine du fichier.
        file_type: Type déduit du contenu par detect_document_type.

    Raises:
        UnsupportedFileTypeError: Extension hors liste blanche, ou différente du contenu.
    """
    suffix = filename[filename.rfind(".") :].lower() if "." in filename else ""
    expected = ALLOWED_EXTENSIONS.get(suffix)
    if expected is None:
        raise UnsupportedFileTypeError("Seuls les fichiers .pdf et .md sont acceptés.")
    if expected is not file_type:
        raise UnsupportedFileTypeError(
            f"Le contenu de ce fichier ne correspond pas à son extension {suffix}."
        )
