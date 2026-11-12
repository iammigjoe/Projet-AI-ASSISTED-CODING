"""
===============================================================================
Intégration : LocalFileStorage
===============================================================================
Objectif :
    Écrire les fichiers uploadés sous un nom généré (UUID), hors accès public.

Responsabilités :
    - Générer storage_key = UUID v4 + extension contrôlée (.pdf / .md).
    - Ne jamais utiliser filename_original comme chemin (path traversal).
    - Résoudre open() uniquement sous le dossier de stockage.

Utilisé par :
    IngestionService

Exemple d'utilisation :
    key = storage.save(data, DocumentType.MARKDOWN)
    path = storage.open(key)

Lot :
    B (ingestion)
===============================================================================
"""

from __future__ import annotations

import hashlib
import uuid
from pathlib import Path
from typing import Protocol

from backend.domain.enums import DocumentType


# =============================================================================
# Constantes
# =============================================================================

EXTENSIONS: dict[DocumentType, str] = {
    DocumentType.PDF: ".pdf",
    DocumentType.MARKDOWN: ".md",
}


# =============================================================================
# Types
# =============================================================================


class FileStorage(Protocol):
    """Seul endroit qui connaît le disque pour les uploads."""

    def save(self, data: bytes, file_type: DocumentType) -> str:
        """Écrit les octets et renvoie la storage_key."""

    def open(self, storage_key: str) -> Path:
        """Résout la storage_key en chemin absolu sous le dossier de stockage."""


# =============================================================================
# API publique
# =============================================================================


class LocalFileStorage:
    """Stockage local sous un répertoire dédié (MYPLAN_STORAGE_DIR)."""

    def __init__(self, root: Path) -> None:
        self._root = root.resolve()
        self._root.mkdir(parents=True, exist_ok=True)

    def save(self, data: bytes, file_type: DocumentType) -> str:
        """Enregistre ``data`` sous un UUID + extension contrôlée.

        Args:
            data: Contenu brut du fichier.
            file_type: Type déjà validé par UploadValidator.

        Returns:
            storage_key (ex. ``3f2a….md``), jamais un chemin absolu.
        """
        storage_key = f"{uuid.uuid4()}{EXTENSIONS[file_type]}"
        path = self._safe_path(storage_key)
        path.write_bytes(data)
        return storage_key

    def open(self, storage_key: str) -> Path:
        """Retourne le chemin absolu d'une storage_key déjà connue.

        Raises:
            ValueError: Si la clé tente de sortir du dossier (path traversal).
            FileNotFoundError: Si le fichier n'existe pas.
        """
        path = self._safe_path(storage_key)
        if not path.is_file():
            raise FileNotFoundError(storage_key)
        return path

    @staticmethod
    def sha256(data: bytes) -> str:
        """Empreinte hexadécimale du contenu (colonne documents.sha256)."""
        return hashlib.sha256(data).hexdigest()

    def _safe_path(self, storage_key: str) -> Path:
        """Refuse toute clé qui sortirait de ``self._root``."""
        if not storage_key or storage_key != Path(storage_key).name:
            raise ValueError("storage_key invalide")
        path = (self._root / storage_key).resolve()
        if not path.is_relative_to(self._root):
            raise ValueError("storage_key hors du dossier de stockage")
        return path
