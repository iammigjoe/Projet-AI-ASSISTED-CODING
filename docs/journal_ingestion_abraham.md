# Journal d'implémentation — Lot B (Abraham Miguel Tala)

Branche : `feature/upload-documents` (reprise sur `develop` à jour, socle lot A inclus).  
Périmètre : parties 1 à 7 du plan.  
Aligné sur le socle A : `DocumentType` (pas `FileType`), erreurs via `DomainError`
(`EXTRACTION_FAILED`, `FILE_TOO_LARGE`, `UNSUPPORTED_FILE_TYPE`).  
L'API documents et la page Streamlit viendront ensuite.

Comment relancer les tests :

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
pytest
```

---

## Partie 1 — Contrat `ParsedDocument` + fichiers d'exemple

**Pourquoi.** Houria (lot C) consomme des chapitres, pas des PDF. La forme des objets doit être fixée avant le reste.

**Fichiers.**

| Fichier | Rôle |
|---|---|
| `backend/domain/documents.py` | `TextBlock`, `OutlineEntry`, `ParsedDocument`, `DetectedChapter` |
| `backend/domain/enums.py` | `FileType`, `DocumentStatus`, `MasteryGoal`, `ExtractionErrorCode` (amorcé pour B ; A complète) |
| `backend/domain/errors.py` | `ExtractionError` avec un `code` stable |
| `tests/fixtures/documents/*.md` | Tes trois cours + `nested-headings.md` + `empty.md` |

**Décisions.**

- Les cours ont quitté `data/` (réservé à la base SQLite, ignoré par Git) pour `tests/fixtures/documents/`.
- Un `ParsedDocument` ne décide pas des chapitres : il porte `blocks` + `outline` ; `chapter_detection` décide ensuite.

---

## Partie 2 — `MarkdownParser`

**Pourquoi.** Transformer `.md` → `ParsedDocument` sans mélanger détection ni estimation.

**Fichier.** `backend/integrations/parsers/markdown_parser.py`

**Comportement.**

- Titres ATX `#` … `######` → `heading_level`.
- Paragraphes → `heading_level=None`.
- Fichier vide → `ExtractionError(EMPTY_TEXT)`.
- Limite de temps `timeout_sec` (défaut 5 s).

**Tests.** `tests/integrations/test_markdown_parser.py`  
Machine Learning → 5 chapitres, Statistics → 4, Cloud → 3, nested → 3.

---

## Partie 3 — `chapter_detection`

**Pourquoi.** La détection se trompera (P0-06) : elle doit être testable sans fichier.

**Fichier.** `backend/domain/chapter_detection.py`

**Règles.**

1. Si `outline` a des entrées de niveau 1 (signets PDF) → un chapitre par entrée.
2. Sinon, titres `##` (niveau 2) → chapitres (cas Markdown).
3. Sinon, plusieurs titres `#` → heuristique PDF sans signets.
4. Un seul `#` + du texte → aucun chapitre (titre de document seul).

---

## Partie 4 — `estimation`

**Pourquoi.** Formule transparente P0-07, modifiable à la main plus tard.

**Fichier.** `backend/domain/estimation.py`

```text
minutes = ceil( (mots / wpm) × coeff_difficulté × coeff_objectif )
```

| Entrée | Coefficients retenus (provisoires) |
|---|---|
| Difficulté 1…5 | 0.8, 0.9, 1.0, 1.2, 1.5 |
| `discovery` / `standard` / `mastery` | 0.8 / 1.0 / 1.3 |

- Chapitre de 0 mot → `0`.
- `effective_minutes` préfère `estimated_min_override` (RG5).
- `StudySettings` est un dataclass du domaine : en attendant `user_settings` de Marc.

---

## Partie 5 — Upload sécurisé

**Fichiers.**

| Fichier | Rôle |
|---|---|
| `backend/integrations/storage/upload_validator.py` | Taille max + magic bytes |
| `backend/integrations/storage/local_file_storage.py` | UUID + extension contrôlée |

**Règles de sécu.**

- PDF = octets qui commencent par `%PDF`.
- Markdown = UTF-8 sans null bytes (pas d'extension seule).
- `filename_original` n'est **jamais** un chemin disque.
- `storage.open("../x")` est refusé (path traversal).

---

## Partie 6 — `PdfParser` + fixtures PDF

**Fichier.** `backend/integrations/parsers/pdf_parser.py` (PyMuPDF)

**Fixtures.**

| Fichier | Cas |
|---|---|
| `with-bookmarks.pdf` | Signets niveau 1 |
| `no-bookmarks.pdf` | Titres par taille de police |
| `empty.pdf` | Page blanche |
| `scanned-no-text.pdf` | Aucun texte extractible → `SCANNED_PDF` |
| `fake.pdf` | Pas un PDF → `INVALID_BYTES` |

---

## Partie 7 — `IngestionService`

**Fichier.** `backend/services/ingestion_service.py`

Enchaînement :

1. `accept_upload(data, filename_original)` → valide, stocke, renvoie métadonnées.
2. `process_stored(storage_key, settings, difficulty)` → parse → détecte → estime.

Pas de SQLAlchemy ici : Marc livre les modèles `documents` / `chapters` et `get_current_user`. Ensuite seulement : routers, schémas Pydantic, page Streamlit (parties 8–9).

---

## Ce qui attend Marc (lot A)

- Modèles et migration `documents`, `chapters`, `courses`, `user_settings`
- `get_current_user` (même provisoire)
- `backend/api/errors.py`, `frontend/api/base.py`
- Vrais paramètres d'étude (vitesse de lecture) branchés à la place de `StudySettings` de test

## Ce que tu peux faire tout de suite

- Relire ce journal avec Houria pour valider `ParsedDocument` / `DetectedChapter`
- Ouvrir une PR vers `develop` (relecture : Marc)
- Ne pas committer `.venv/`, `data/*.db`, ni `storage/*` hors `.gitkeep`
