"""
===============================================================================
Domaine : documents (ParsedDocument, DetectedChapter)
===============================================================================
Objectif :
    Fixer le contrat entre les parseurs (intégrations) et la détection de
    chapitres (domaine) : ce que devient un fichier une fois lu, sans I/O.

Responsabilités :
    - Décrire les blocs de texte extraits (titre éventuel, page, police).
    - Décrire la table des matières / signets quand le PDF en fournit une.
    - Décrire un chapitre détecté (titre, position, mots, pages).

Pur :
    Ni base, ni réseau, ni horloge, ni lecture de fichier.

Utilisé par :
    chapter_detection, estimation, PdfParser, MarkdownParser, IngestionService
    (contrat validé avec le lot C — répartition §3)

Exemple d'utilisation :
    doc = ParsedDocument(
        blocks=(TextBlock(text="Intro", heading_level=1, page=1),),
        outline=(),
    )
    chapters = detect_chapters(doc)

Lot :
    B (ingestion)
===============================================================================
"""

from dataclasses import dataclass


# =============================================================================
# Types
# =============================================================================


@dataclass(frozen=True)
class TextBlock:
    """Fragment de texte extrait d'un document.

    Un titre Markdown `#` / `##` ou un titre PDF se traduit par
    ``heading_level`` 1 ou 2. Un paragraphe a ``heading_level`` à None.

    Attributes:
        text: Contenu brut, jamais interprété ni exécuté.
        heading_level: 1 pour un titre de document / chapitre fort, 2 pour
            un sous-titre de chapitre, None pour le corps.
        page: Numéro de page (PDF, 1-indexé) ; None en Markdown.
        font_size: Taille de police si connue (heuristique PDF) ; None sinon.
    """

    text: str
    heading_level: int | None = None
    page: int | None = None
    font_size: float | None = None


@dataclass(frozen=True)
class OutlineEntry:
    """Entrée de table des matières ou signet PDF.

    Attributes:
        title: Libellé du signet.
        level: Niveau hiérarchique (1 = chapitre principal).
        page: Page cible, 1-indexée.
    """

    title: str
    level: int
    page: int


@dataclass(frozen=True)
class ParsedDocument:
    """Résultat de parse() : texte structuré, sans décision de chapitre.

    Le parseur remplit ``blocks`` et, si le PDF a des signets, ``outline``.
    ``chapter_detection`` lit ces deux champs et décide ce qui est un chapitre.
    """

    blocks: tuple[TextBlock, ...]
    outline: tuple[OutlineEntry, ...] = ()


@dataclass(frozen=True)
class DetectedChapter:
    """Chapitre proposé à l'étudiant avant validation manuelle (P0-05 / P0-06).

    Attributes:
        title: Titre affiché, modifiable ensuite.
        position: Ordre dans le document, à partir de 0.
        word_count: Nombre de mots du corps du chapitre (≥ 0).
        page_start: Première page (PDF) ; None en Markdown.
        page_end: Dernière page (PDF) ; None en Markdown.
    """

    title: str
    position: int
    word_count: int
    page_start: int | None = None
    page_end: int | None = None
