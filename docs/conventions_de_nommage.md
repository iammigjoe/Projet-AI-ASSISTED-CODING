# Conventions de nommage

Règles de nommage de MyPlan, de la base de données jusqu'aux branches Git. Elles sont écrites **avant le code** : chaque règle doit être vérifiable dans le dépôt dès que la partie concernée existe. Une convention affichée et non suivie est pire qu'une convention absente, parce qu'elle laisse croire que le code la respecte. Si le code et ce document divergent, l'un des deux est corrigé dans la même pull request, et la règle concernée est signalée ici à son emplacement.

## Sommaire

1. [Principes généraux](#1-principes-généraux)
2. [Python : backend](#2-python--backend)
3. [Streamlit : frontend](#3-streamlit--frontend)
4. [Base de données : SQLite](#4-base-de-données--sqlite)
5. [API REST](#5-api-rest)
6. [Format des réponses de l'API](#6-format-des-réponses-de-lapi)
7. [Tests](#7-tests)
8. [Migrations Alembic](#8-migrations-alembic)
9. [Variables d'environnement](#9-variables-denvironnement)
10. [Git](#10-git)
11. [Fichiers et dossiers](#11-fichiers-et-dossiers)
12. [Docstrings d'en-tête](#12-docstrings-den-tête)

---

## 1. Principes généraux

| Règle | Détail |
|---|---|
| **Langue du code** | Anglais : modules, classes, fonctions, variables, routes, tables, colonnes |
| **Langue des contenus** | Français : textes de l'interface, messages d'erreur affichés à l'étudiant, documentation |
| **Abréviations** | Interdites, sauf acronymes établis (`id`, `url`, `pdf`, `jwt`, `llm`, `utc`) et unités (`min`) |
| **Un concept, un nom** | Le même mot dans toutes les couches : `Chapter` (modèle), `chapters` (table), `ChapterRead` (schéma), `/api/v1/chapters` (route), `ChapterRepository` (accès aux données) |
| **Vocabulaire fixé** | Voir le glossaire ci-dessous : on n'écrit jamais `lesson` pour un chapitre ni `slot` pour une session |

### Glossaire

| Français (interface) | Anglais (code) | Ce que c'est |
|---|---|---|
| matière, cours | `course` | Une matière de l'étudiant (« Analyse 2 ») |
| document | `document` | Un fichier PDF ou Markdown rattaché à une matière |
| chapitre | `chapter` | Une partie d'un document, unité de planification |
| disponibilité | `availability` | Créneau hebdomadaire récurrent où l'étudiant peut travailler |
| exception | `availability_exception` | Jour bloqué ou créneau ajouté ponctuellement |
| créneau libre | `free_slot` | Intervalle calculé (disponibilités − exceptions − agenda occupé). N'existe qu'en mémoire, jamais en base |
| échéance | `deadline` | Examen ou rendu de projet |
| planning | `plan` | Une version de la répartition des sessions |
| session | `study_session` | Une plage d'étude d'un chapitre, dans un planning |
| auto-évaluation | `self_rating` | Note de 1 à 5 donnée après une session |
| stabilité | `stability` | Paramètre `S` de la courbe d'oubli, en jours |
| rétention | `retention` | Probabilité `R` de se souvenir d'un chapitre à un instant donné |

`session` seul est réservé : il désigne déjà la session SQLAlchemy et le `st.session_state` de Streamlit. Une session d'étude s'écrit **toujours** `study_session`.

### Casse par contexte

| Contexte | Convention | Exemple |
|---|---|---|
| Modules et paquets Python | `snake_case` | `planner.py`, `calendar_sync_service.py` |
| Classes | `PascalCase` | `StudySession`, `PlanningService` |
| Fonctions, méthodes, variables | `snake_case` | `estimate_minutes()`, `free_slots` |
| Constantes | `UPPER_SNAKE_CASE` | `DEFAULT_READING_SPEED_WPM` |
| Membres d'énumération | `UPPER_SNAKE_CASE`, valeur en `snake_case` | `SessionStatus.PLANNED = "planned"` |
| Tables | `snake_case` **pluriel** | `courses`, `study_sessions` |
| Colonnes | `snake_case` | `due_at`, `estimated_min` |
| Routes | `kebab-case` pluriel, préfixe `/api/v1/` | `/api/v1/study-sessions` |
| Pages Streamlit | `snake_case`, anglais ; titre affiché en français | `plan.py`, titre « Planning » |
| Branches Git | préfixe + `kebab-case` | `feature/chapter-detection` |

---

## 2. Python : backend

Le code suit PEP 8, formaté par `ruff format` et vérifié par `ruff check`. Toutes les signatures publiques sont annotées.

### Modèles SQLAlchemy (`backend/db/models/`)

`PascalCase`, **singulier**, un modèle par entité. La table est plurielle (voir §4).

```python
# BIEN
class Course(Base):
    __tablename__ = "courses"

class StudySession(Base):
    __tablename__ = "study_sessions"

# MAL
class Courses(Base): ...        # pluriel
class Matiere(Base): ...        # français
class CourseModel(Base): ...    # suffixe inutile
class Session(Base): ...        # collision avec la session SQLAlchemy
```

### Schémas Pydantic (`backend/api/schemas/`)

`Entité + Rôle`. Un schéma par sens de circulation : ce qu'on reçoit n'est jamais ce qu'on renvoie.

| Suffixe | Usage | Exemple |
|---|---|---|
| `Create` | Corps d'un `POST` | `CourseCreate` |
| `Update` | Corps d'un `PATCH`, tous les champs optionnels | `ChapterUpdate` |
| `Read` | Réponse | `CourseRead` |
| `Summary` | Réponse allégée pour une liste | `DocumentSummary` |

```python
# BIEN
CourseCreate, CourseUpdate, CourseRead
PlanGenerate          # paramètres de génération, ce n'est pas un Create de Plan

# MAL
CourseSchema          # sens non précisé
CourseIn / CourseOut  # deux conventions dans un même projet
CourseDTO             # vocabulaire d'un autre framework
```

**Un modèle SQLAlchemy n'est jamais renvoyé tel quel par un endpoint.** Il passe toujours par un schéma `Read` (`response_model=`), sinon une colonne ajoutée plus tard, comme `password_hash` ou `encrypted_refresh_token`, partirait dans la réponse sans que personne ne l'ait décidé.

### Objets du domaine (`backend/domain/`)

`@dataclass(frozen=True)`, sans suffixe, sans aucun import de SQLAlchemy, FastAPI ou Pydantic.

```python
@dataclass(frozen=True)
class ChapterToPlan:
    chapter_id: int
    minutes_remaining: int
    deadline_due_at: datetime
```

Le nom décrit ce que le domaine manipule, pas la table d'où ça vient : `ChapterToPlan`, `FreeSlot`, `PlannedSession`, `PlanShortfall`.

### Services, repositories, intégrations

| Couche | Convention | Exemples |
|---|---|---|
| Services (couche 3) | `PascalCase + Service` | `IngestionService`, `PlanningService`, `CalendarSyncService` |
| Repositories (couche 5) | `PascalCase + Repository` | `CourseRepository`, `StudySessionRepository` |
| Interfaces (`typing.Protocol`) | nom du rôle, sans `I` ni `Interface` | `DocumentParser`, `CalendarWriter`, `LlmClient` |
| Implémentations | technologie + rôle | `PdfParser`, `GoogleCalendarClient`, `AnthropicLlmClient` |
| Exceptions | `PascalCase + Error` | `PlanNotFeasibleError`, `ExtractionError` |

Les specs écrivent `UserRepo`, `CourseRepo` : ce document fixe `UserRepository`, sans abréviation.

### Méthodes des repositories

Chaque méthode qui lit ou écrit une donnée d'utilisateur prend `user_id` en **premier argument**. Il n'existe pas de `get(course_id)` : l'oubli du filtre devient une erreur de signature, pas une faille.

```python
# BIEN
def get(self, user_id: int, course_id: int) -> Course | None: ...
def list(self, user_id: int) -> list[Course]: ...
def delete(self, user_id: int, course_id: int) -> bool: ...

# MAL
def get(self, course_id: int) -> Course | None: ...      # aucune isolation
def get_course_by_id_for_user(...): ...                   # le nom répète la classe
```

Seule exception : les méthodes du scheduler qui lisent à travers tous les utilisateurs. Leur nom finit par `_for_all_users` (`list_due_for_all_users`), pour qu'elles se repèrent en revue ; voir [diagramme_classes.md](diagramme_classes.md) §7.

### Fonctions et variables

```python
# Verbes pour les fonctions
estimate_minutes()
detect_chapters()
build_free_slots()

# Booléens : is_, has_, can_
is_overridden
has_google_credentials

# Unités dans le nom quand ce n'est pas une datetime
duration_min        # minutes
stability_days      # jours
reading_speed_wpm   # mots par minute
max_upload_bytes

# Instants : suffixe _at, toujours en UTC et avec fuseau
due_at, started_at, last_review_at
```

Une `datetime` sans fuseau (naïve) est une erreur dans tout le backend. On écrit `datetime.now(UTC)`, jamais `datetime.now()` ni `datetime.utcnow()`.

### Énumérations

`enum.StrEnum` dans `backend/domain/enums.py`, pour toute valeur à ensemble fini. Jamais de chaîne libre.

```python
class SessionStatus(StrEnum):
    PLANNED = "planned"
    DONE = "done"
    MISSED = "missed"

class DocumentStatus(StrEnum):
    PENDING = "pending"
    PROCESSING = "processing"
    READY = "ready"
    FAILED = "failed"

class DeadlineType(StrEnum):
    EXAM = "exam"
    PROJECT = "project"

class ExceptionKind(StrEnum):
    BLOCKED = "blocked"
    ADDED = "added"

class PlanStatus(StrEnum):
    DRAFT = "draft"
    ACTIVE = "active"
    ARCHIVED = "archived"
```

---

## 3. Streamlit : frontend

Avec le dossier `pages/` seul, Streamlit construit le menu à partir du **nom des fichiers** : `1_Matieres.py` s'afficherait « Matieres », sans accent, et l'ordre dépendrait d'un préfixe numérique. Le menu est donc déclaré dans `app.py` avec `st.navigation` et `st.Page` (Streamlit 1.36 et suivants) : les fichiers suivent la convention du code, le titre affiché est en français et l'ordre est celui de la liste.

```python
# frontend/app.py
pages = [
    st.Page("pages/courses.py", title="Matières"),
    st.Page("pages/documents.py", title="Documents"),
    st.Page("pages/availabilities.py", title="Disponibilités"),
    st.Page("pages/deadlines.py", title="Échéances"),
    st.Page("pages/plan.py", title="Planning"),
    st.Page("pages/dashboard.py", title="Tableau de bord"),
    st.Page("pages/settings.py", title="Paramètres"),
]
st.navigation(pages).run()
```

```text
frontend/
├── app.py                      # Point d'entrée : connexion, puis menu
├── pages/
│   ├── login.py
│   ├── courses.py
│   ├── documents.py
│   ├── availabilities.py
│   ├── deadlines.py
│   ├── plan.py
│   ├── dashboard.py
│   └── settings.py
├── api/                        # Un client par domaine, seul contact avec FastAPI
│   ├── base.py                 # Requêtes, jeton, gestion des erreurs
│   ├── auth_api.py
│   ├── courses_api.py
│   ├── documents_api.py
│   ├── planning_api.py
│   └── progress_api.py
└── components/                 # Morceaux d'interface réutilisés
    ├── chapter_editor.py
    └── session_card.py
```

Les specs prévoient un seul `api_client.py`. Il est découpé en un fichier par domaine : à quatre, un fichier unique serait modifié dans presque chaque pull request et deviendrait le premier lieu de conflits (voir [repartition_taches.md](repartition_taches.md)).

Clés de `st.session_state` : `snake_case`, constantes déclarées dans `frontend/state.py`.

```python
ACCESS_TOKEN = "access_token"
CURRENT_USER = "current_user"
SELECTED_COURSE_ID = "selected_course_id"
```

---

## 4. Base de données : SQLite

### Tables

`snake_case`, **pluriel**, anglais : c'est le choix des specs (`users`, `study_sessions`), conservé.

Le pluriel a une raison de plus ici : `user` est un mot réservé de PostgreSQL, et le passage à PostgreSQL est prévu (P3). `users` ne demandera aucun renommage.

Les tables d'association prennent les deux noms, dans l'ordre de la dépendance : `deadline_chapters`.

### Colonnes

| Règle | Exemple |
|---|---|
| `snake_case`, anglais | `word_count`, `password_hash` |
| Clé primaire : `id` | `id INTEGER PRIMARY KEY` |
| Clé étrangère : `<entité au singulier>_id` | `course_id`, `chapter_id` |
| Instant en UTC : suffixe `_at` | `created_at`, `due_at`, `starts_at` |
| Heure locale sans date : suffixe `_local` | `starts_local`, `ends_local` |
| Durée : unité en suffixe | `estimated_min`, `max_session_min` |
| Booléen : `is_` ou `has_` | `is_active` |
| Jamais de mot réservé SQL | `starts_at` et `ends_at`, pas `start` et `end` |

Les specs nomment `start` et `end` les bornes des sessions et des disponibilités. `END` est un mot réservé en SQL : chaque requête écrite à la main devrait l'échapper. Les colonnes deviennent `starts_at` / `ends_at` pour les instants, et `starts_local` / `ends_local` pour les heures récurrentes (voir [modele_donnees.md](modele_donnees.md) §5).

Colonnes présentes sur chaque table d'entité :

```sql
created_at  TEXT NOT NULL   -- ISO 8601 UTC
updated_at  TEXT NOT NULL   -- ISO 8601 UTC
```

### Contraintes et index

Noms explicites, pour qu'une erreur d'intégrité dise d'elle-même ce qu'elle protège :

| Objet | Format | Exemple |
|---|---|---|
| Unicité | `uq_<table>_<colonnes>` | `uq_users_email` |
| Index | `ix_<table>_<colonnes>` | `ix_study_sessions_plan_id` |
| Vérification | `ck_<table>_<règle>` | `ck_study_sessions_self_rating_range` |
| Clé étrangère | `fk_<table>_<colonne>_<table cible>` | `fk_chapters_document_id_documents` |

Fixés une fois pour toutes par la `naming_convention` du `MetaData` SQLAlchemy, pour qu'Alembic génère les mêmes noms sur toutes les machines.

---

## 5. API REST

### Routes

`kebab-case`, **pluriel**, préfixe `/api/v1/`. L'action est portée par la méthode HTTP.

```text
POST   /api/v1/auth/register
POST   /api/v1/auth/login
POST   /api/v1/auth/refresh

GET    /api/v1/courses
POST   /api/v1/courses
GET    /api/v1/courses/{course_id}
PATCH  /api/v1/courses/{course_id}
DELETE /api/v1/courses/{course_id}

POST   /api/v1/courses/{course_id}/documents      # upload
GET    /api/v1/documents/{document_id}            # statut d'extraction
GET    /api/v1/documents/{document_id}/chapters
PATCH  /api/v1/chapters/{chapter_id}

GET    /api/v1/availabilities
GET    /api/v1/availability-exceptions
GET    /api/v1/deadlines

POST   /api/v1/plans                              # génère une nouvelle version
GET    /api/v1/plans/{plan_id}/study-sessions
PATCH  /api/v1/study-sessions/{session_id}        # faite, non faite, auto-évaluation

GET    /api/v1/progress                           # données du dashboard
```

Les ressources imbriquées ne descendent que d'un niveau, et seulement pour **créer** ou **lister** dans un parent. Une ressource qui a un identifiant se lit à la racine : `/api/v1/chapters/{chapter_id}`, pas `/api/v1/courses/1/documents/2/chapters/3`.

### Opérations qui ne sont pas du CRUD

Quelques opérations ne se réduisent pas à créer, lire, modifier ou supprimer une ressource. Elles prennent la forme `POST /ressource/{id}/<action>`, et **seules celles listées ici** sont autorisées :

| Route | Ce qu'elle fait |
|---|---|
| `POST /api/v1/chapters/{chapter_id}/split` | Scinde un chapitre en deux à une position donnée |
| `POST /api/v1/chapters/merge` | Fusionne des chapitres consécutifs d'un même document |
| `POST /api/v1/plans/{plan_id}/activate` | Fait d'un brouillon le planning actif |
| `POST /api/v1/plans/{plan_id}/google-sync` | Exporte le planning vers Google Agenda |
| `POST /api/v1/plans/{plan_id}/replan` | Propose une nouvelle version à partir de l'avancement réel |

Ajouter une route à ce tableau se décide en revue, pas au fil du code.

Deux familles de routes échappent aussi au modèle « ressource au pluriel », parce qu'elles suivent un protocole fixé ailleurs :

| Routes | Pourquoi |
|---|---|
| `POST /api/v1/auth/register`, `/login`, `/refresh` | Flux d'authentification, pas des ressources |
| `GET /api/v1/google/authorize`, `GET /api/v1/google/callback`, `DELETE /api/v1/google/credentials` | Flux OAuth de Google ; l'URL de retour est enregistrée dans la console Google (`GOOGLE_REDIRECT_URI`) |
| `GET /api/v1/progress` | Vue calculée pour le dashboard, au singulier : elle n'a pas d'identifiant et ne se crée pas |

### Paramètres

`snake_case` pour les paramètres de chemin et de requête : `?from_date=2026-11-01&course_id=3`. Le corps JSON est en `snake_case` aussi, comme les schémas Pydantic : aucune conversion entre Streamlit et FastAPI.

### Méthodes et codes de réponse

| Méthode | Usage | Code de succès |
|---|---|---|
| `GET` | Lecture | `200` |
| `POST` | Création ou opération listée ci-dessus | `201` (création) ou `200` |
| `PATCH` | Modification partielle | `200` |
| `DELETE` | Suppression | `204` |

`PUT` n'est pas utilisé : aucune ressource n'est remplacée en entier.

| Code | Quand |
|---|---|
| `400` | Requête mal formée |
| `401` | Jeton absent, invalide ou expiré |
| `404` | Ressource inexistante **ou appartenant à un autre utilisateur** |
| `409` | Conflit d'état (activer un planning déjà archivé) |
| `413` | Fichier trop lourd |
| `415` | Type de fichier refusé |
| `422` | Entrée invalide (Pydantic) ou règle métier non respectée |
| `429` | Trop de requêtes (rate limiting) |

Une ressource d'un autre utilisateur répond `404`, jamais `403` : `403` confirmerait que l'identifiant existe.

---

## 6. Format des réponses de l'API

Succès : la ressource, ou la liste, directement. Pas d'enveloppe `data` : FastAPI génère la documentation OpenAPI à partir du `response_model`, et une enveloppe la rendrait moins lisible pour un gain nul.

```json
{ "id": 12, "title": "Intégrales impropres", "estimated_min": 95 }
```

Erreur : toujours la même forme, avec un code stable que le frontend peut tester.

```json
{
  "error": {
    "code": "PLAN_NOT_FEASIBLE",
    "message": "Il manque 6 h 30 avant l'examen d'Analyse 2 du 15 décembre.",
    "details": {
      "shortfalls": [
        { "deadline_id": 4, "missing_min": 390 }
      ]
    }
  }
}
```

| Règle | Détail |
|---|---|
| `code` | `UPPER_SNAKE_CASE`, anglais, ne change jamais une fois publié |
| `message` | Français, lisible tel quel par l'étudiant, sans détail technique |
| `details` | Optionnel, données structurées propres au code |

Codes connus : `VALIDATION_ERROR`, `NOT_FOUND`, `UNAUTHORIZED`, `FILE_TOO_LARGE`, `UNSUPPORTED_FILE_TYPE`, `EXTRACTION_FAILED`, `PLAN_NOT_FEASIBLE`, `GOOGLE_NOT_CONNECTED`, `RATE_LIMITED`. Un nouveau code s'ajoute dans `backend/api/errors.py`, à un seul endroit.

---

## 7. Tests

pytest. L'arborescence reproduit celle de `backend/`, couche par couche : on trouve le test d'un fichier sans chercher.

```text
tests/
├── domain/            # Purs : ni base, ni réseau, ni fichier
│   ├── test_estimation.py
│   ├── test_planner.py
│   └── test_memory.py
├── services/          # Base SQLite en mémoire, intégrations remplacées par des faux
├── repositories/      # Dont les tests d'isolation entre utilisateurs
├── api/               # httpx contre l'application FastAPI
├── integrations/      # Parseurs sur des fichiers d'exemple, Google simulé
└── fixtures/
    ├── documents/     # PDF et Markdown d'exemple, dont des fichiers piégés
    └── factories.py
```

Fonctions de test : `test_<unité>_<scénario>_<résultat attendu>`, en anglais.

```python
# BIEN
def test_plan_when_not_enough_time_reports_missing_minutes(): ...
def test_plan_never_places_session_after_its_deadline(): ...
def test_get_course_of_another_user_returns_404(): ...
def test_pdf_parser_with_scanned_pdf_raises_extraction_error(): ...

# MAL
def test_plan(): ...
def test_1(): ...
def test_ca_marche(): ...
```

Un test d'isolation existe pour **chaque** endpoint qui prend un identifiant : l'utilisateur B demande la ressource de l'utilisateur A et reçoit `404`.

---

## 8. Migrations Alembic

```text
backend/db/migrations/versions/
└── 20261115_1430_create_courses_table.py
```

Format : `AAAAMMJJ_HHMM_<description en snake_case>.py`, réglé par `file_template` dans `alembic.ini`.

| Règle | Pourquoi |
|---|---|
| Une migration déjà fusionnée dans `develop` ne se modifie jamais | Elle a peut-être déjà tourné sur la base d'un autre membre |
| Une erreur de schéma se corrige par une nouvelle migration | Même raison |
| Une migration par pull request au plus | Deux migrations parallèles sur la même révision créent deux têtes ; voir [repartition_taches.md](repartition_taches.md) §5 |
| Toujours relire le fichier généré par `--autogenerate` | Alembic ne détecte ni les renommages ni certaines contraintes SQLite |

---

## 9. Variables d'environnement

`UPPER_SNAKE_CASE`, préfixe `MYPLAN_` pour les réglages propres à l'application. Toutes listées, sans valeur secrète, dans `.env.example`.

```env
MYPLAN_ENV=dev
MYPLAN_DATABASE_URL=sqlite:///./data/myplan.db
MYPLAN_STORAGE_DIR=./storage
MYPLAN_MAX_UPLOAD_BYTES=20971520
MYPLAN_JWT_SECRET_KEY=
MYPLAN_JWT_ACCESS_TTL_MIN=15
MYPLAN_JWT_REFRESH_TTL_DAYS=7
MYPLAN_FERNET_KEY=
MYPLAN_CORS_ORIGINS=http://localhost:8501
MYPLAN_API_BASE_URL=http://localhost:8000

GOOGLE_CLIENT_ID=
GOOGLE_CLIENT_SECRET=
GOOGLE_REDIRECT_URI=http://localhost:8000/api/v1/google/callback

ANTHROPIC_API_KEY=
```

Les variables des services externes gardent le nom que leur bibliothèque attend (`ANTHROPIC_API_KEY`), sans préfixe. Elles sont lues à un seul endroit : `backend/core/config.py` (pydantic-settings).

---

## 10. Git

### Branches

```text
main        Version stable, protégée, jamais de commit direct
develop     Intégration, protégée, reçoit les pull requests

feature/*   Nouvelle fonctionnalité        feature/chapter-detection
fix/*       Correction de bug              fix/planner-dst-shift
docs/*      Documentation seule            docs/conception
chore/*     Outillage, dépendances, CI     chore/ruff-config
test/*      Tests seuls                    test/user-isolation
```

Une branche = une fonctionnalité, partie de `develop` à jour, fusionnée par pull request avec au moins une relecture d'un autre membre.

### Messages de commit

[Conventional Commits](https://www.conventionalcommits.org) : `type(portée): description`, en français, au présent, sans point final.

| Type | Usage |
|---|---|
| `feat` | Nouvelle fonctionnalité |
| `fix` | Correction de bug |
| `refactor` | Restructuration sans changement de comportement |
| `test` | Tests seuls |
| `docs` | Documentation seule |
| `chore` | Configuration, dépendances, CI |
| `perf` | Performance |

Portées : `auth`, `courses`, `ingestion`, `chapters`, `estimation`, `availability`, `deadlines`, `planner`, `calendar`, `progress`, `memory`, `notifications`, `frontend`, `db`, `ci`.

```text
# BIEN
feat(ingestion): détecte les chapitres à partir des signets PDF
fix(planner): ne place plus de session après l'échéance
test(auth): vérifie qu'un utilisateur ne lit pas les cours d'un autre
docs(modele): ajoute les règles de gestion des plannings

# MAL
update
wip
fix bug
feat: planning + correction du login + readme
```

---

## 11. Fichiers et dossiers

| Type | Convention | Exemple |
|---|---|---|
| Documentation | `snake_case.md`, français, dans `docs/` | `docs/modele_donnees.md` |
| Fichiers d'exemple de test | `kebab-case`, décrivant le cas | `scanned-no-text.pdf`, `nested-headings.md` |
| Fichiers uploadés | UUID v4 + extension contrôlée | `storage/3f2a…c9.pdf` |
| Schémas | `snake_case` + `.drawio` et `.png` | `docs/architecture_couches.drawio` |

Le nom d'origine d'un fichier uploadé est stocké en base (`filename_original`) et n'est **jamais** utilisé pour écrire sur le disque.

---

## 12. Docstrings d'en-tête

Chaque fichier de service, de domaine, d'intégration et de router commence par une docstring qui permet de comprendre son rôle sans lire le code. En anglais, comme le code.

### Service

```python
"""
PlanningService
===============
Purpose:
    Generates and activates study plans for one user.

Responsibilities:
    - Load chapters, availabilities, exceptions and deadlines for the user.
    - Call the pure planner (domain/planner.py) and persist the result as a new plan version.
    - Activate a draft plan and archive the previous active one.

Dependencies:
    ChapterRepository, AvailabilityRepository, DeadlineRepository,
    PlanRepository, BusyTimeReader (optional, Google Calendar)

Used by:
    api/routers/plans.py

Raises:
    PlanNotFeasibleError  when the available time is insufficient before a deadline
"""
```

### Domaine

```python
"""
planner
=======
Purpose:
    Places study sessions into free slots so that every chapter is finished before its deadline.

Pure:
    No database, no network, no clock. "now" is a parameter.

Inputs:
    chapters: list[ChapterToPlan], free_slots: list[FreeSlot], settings: StudySettings, now: datetime

Output:
    PlanResult (sessions) or PlanResult with shortfalls when the plan is not feasible.
    Never returns a partial plan silently.
"""
```

### Router

```python
"""
Router: /api/v1/plans
=====================
Endpoints:
    POST  /api/v1/plans                         Generate a new draft plan
    GET   /api/v1/plans/{plan_id}/study-sessions List the sessions of a plan
    POST  /api/v1/plans/{plan_id}/activate      Make a draft the active plan
    POST  /api/v1/plans/{plan_id}/google-sync   Export the plan to Google Calendar

Security:
    Authenticated user only. Every plan_id is checked against the current user (404 otherwise).
"""
```

### Page Streamlit

```python
"""
Page: Planning
==============
Purpose:
    Shows the active plan as a list and as a week/month calendar,
    and lets the student mark a session as done or missed.

Calls:
    planning_api.get_active_plan, planning_api.update_study_session

Notes:
    - Displays times in the user's timezone; the API sends UTC.
    - Never renders user content with unsafe_allow_html.
"""
```
