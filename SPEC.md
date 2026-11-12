# SPEC — MyPlan (sujet : StudyPlan)

> **Objectif** : l'étudiant importe ses cours (PDF ou Markdown) et ses échéances. MyPlan en tire des chapitres et une charge en heures, construit un planning de révision hebdomadaire dans ses créneaux libres, l'exporte en calendrier `.ics` et suit l'avancement dans un tableau de bord. **Le produit n'appelle aucune API d'IA** : l'IA sert à le construire, pas à le faire tourner.

**Stack** : Streamlit (front) · FastAPI (API) · SQLite (persistance)
**Cadre** : sujet commun StudyPlan (Jour 2, ~4 h de développement, démo de 8 min). Le sujet officiel, sa grille et les données de démo viennent du kit du cours ; les données sont copiées dans [`sample_data/`](sample_data/).
**Équipe** : 4 personnes, un lot vertical chacune (§9).

Ce document a d'abord été écrit **avant le code** (commit `e7431bb`), puis réaligné sur le sujet officiel le 12/11/2026 quand l'équipe a reçu le kit : contrat d'API imposé, export `.ics` au lieu de Google Agenda, aucune bibliothèque d'IA. Les écarts sont détaillés en §10.

### Documents de référence

Ce document dit **quoi** construire. Ceux de `docs/` disent **comment**, et font foi en cas de doute sur un nom, une table ou une interface :

| Document | Fait foi pour |
|---|---|
| [docs/conventions_de_nommage.md](docs/conventions_de_nommage.md) | Noms (code, tables, routes, tests, branches, commits), format des erreurs, commentaires |
| [docs/modele_donnees.md](docs/modele_donnees.md) | Tables, colonnes, contraintes, règles de gestion |
| [docs/diagramme_classes.md](docs/diagramme_classes.md) | Classes, interfaces et leurs contrats |
| [docs/repartition_taches.md](docs/repartition_taches.md) | Lots, responsables, relectures, calendrier |
| [docs/securite.md](docs/securite.md) | Protections en place et règles de sécurité |
| [CLAUDE.md](CLAUDE.md), [.github/copilot-instructions.md](.github/copilot-instructions.md) | Consignes données aux assistants de code, contrat d'API compris |
| [AI_LOG.md](AI_LOG.md) | Journal de notre usage de l'IA, échecs compris |

Quand ce document et un document de `docs/` divergent, l'écart est corrigé des deux côtés dans la même pull request.

---

## 1. Problème et utilisateur

Un étudiant a plusieurs matières, des examens et des rendus à des dates différentes, et peu de créneaux libres. Il ne sait pas combien de temps chaque cours demande ni dans quel ordre réviser. **MyPlan lui dit quoi réviser, quand, et s'il est en avance ou en retard.**

---

## 2. MVP : les 5 blocs du sujet (tous obligatoires)

| Bloc | Fonctionnalité | Critères d'acceptation | Lot |
|---|---|---|---|
| **1** | **Importer ses cours** | Envoi d'un PDF ou d'un Markdown sur `POST /courses` → matière créée, avec ses chapitres (titres `#`/`##` en Markdown, texte du PDF) et une charge en heures. Règle : `heures = max(1, mots / (vitesse_lecture × 60) × coefficient_difficulté × coefficient_objectif)`, vitesse 200 mots/min par défaut, **minimum 1 h par chapitre** ; modifiable à la main. Type réel du fichier vérifié (*magic bytes*), taille maximale, nom généré. | B |
| **2** | **Échéances et disponibilités** | Créer, lister (triées par date), supprimer des échéances : matière, titre, type `exam` ou `assignment`, date, poids de 0 à 100. **Une date passée est refusée (422).** Créneaux hebdomadaires par jour (`"18:00-20:00"`) et durée des sessions (`session_minutes`) en un seul `PUT /availability`. | C |
| **3** | **Planning hebdomadaire** | `POST /plan/generate {week}` place des sessions de `session_minutes` **dans les créneaux libres uniquement**, **sans chevauchement**, **jamais après l'échéance** de la matière ; les matières aux échéances les plus proches et les plus lourdes passent en premier. Module Python pur (`backend/domain/planner.py`), testé unitairement. | C |
| **4** | **Export `.ics`** | `GET /plan.ics` renvoie `text/calendar`, un `VEVENT` par session, matière et chapitre dans le titre, heures justes en Europe/Paris. S'importe sans erreur dans Google Agenda et Outlook. | D |
| **5** | **Front de suivi** | Écrans : import, échéances, planning de la semaine, tableau de bord. Le tableau de bord montre l'avancement en % par matière, les sessions faites et en retard, les 3 prochaines échéances. Une session se marque faite. | tous (D pour le tableau de bord) |

En plus du sujet, et déjà en place : **compte protégé** (inscription du compte unique, connexion, déconnexion, P0-01), modification des matières et du profil d'étude. Voir §3.

### Détail des fonctionnalités

| ID | Lot | Fonctionnalité | Détails | État |
|---|---|---|---|---|
| P0-01 | A | Compte et authentification | **Un seul compte** : inscription ouverte tant qu'aucun compte n'existe, puis fermée (403). Connexion obligatoire pour toutes les routes du contrat. | ✅ |
| P0-02 | A | Matières | Liste avec avancement (`hours_total`, `hours_done`, `progress`), modification du nom, de la couleur, de la difficulté (1 à 5), suppression en cascade. | ✅ |
| P0-03 | B | Import d'un cours | `POST /courses` multipart : PDF ou Markdown → matière + document + chapitres. | Validation et stockage faits ; route et enregistrement en base à faire |
| P0-04 | B | Extraction du texte | `pypdf` pour le PDF, `markdown-it-py` pour le Markdown ; erreur claire si le PDF est vide ou scanné. | ✅ |
| P0-05 | B | Détection des chapitres | Markdown : titres `#`/`##` (le `#` de niveau 1 donne le nom de la matière). PDF : signets, sinon heuristique. Détection pure, testable sans fichier. | ✅ |
| P0-06 | B | Correction des chapitres | Renommer, fusionner, scinder, supprimer avant de planifier. | à faire |
| P0-07 | B | Charge en heures | Formule du bloc 1, valeur modifiable à la main. | Calcul fait ; modification à la main à faire |
| P0-08 | A | Profil d'étude | Vitesse de lecture, durée des sessions, pause, niveau visé. | ✅ |
| P0-09 | C | Disponibilités | `PUT /availability` remplace tous les créneaux ; heures **locales**, pas UTC. | à faire |
| P0-10 | C | Échéances | `POST/GET/DELETE /deadlines` ; date passée → 422. | à faire |
| P0-11 | C | Planificateur | `POST /plan/generate {week}`, `GET /plan?week=`. Si le temps manque : message explicite (« il manque X h avant le … ») au lieu d'un planning faux. | à faire |
| P0-12 | C | Vue du planning | Liste et calendrier de la semaine. | à faire |
| P0-13 | D | Suivi des sessions | `PATCH /sessions/{id} {done}`. | à faire |
| P0-14 | D | Export `.ics` | `GET /plan.ics` avec `icalendar`. | à faire |
| P0-15 | D | Tableau de bord | Avancement par matière, sessions faites et en retard, 3 prochaines échéances. | à faire |

---

## 3. Contrat d'API

**Figé**. Les routes du sujet sont reprises **à l'identique, sans préfixe** ; on peut ajouter des routes et des champs, jamais en retirer ni en renommer.

### Routes du sujet (minimum imposé)

```
POST   /courses              multipart file -> {id, name, chapters:[{id,title,hours}], hours_total}
GET    /courses              -> [{id, name, hours_total, hours_done, progress}]
POST   /deadlines            {course_id, title, type, date, weight} -> 201
GET    /deadlines            -> list sorted by date
DELETE /deadlines/{id}       -> 204
PUT    /availability         {session_minutes, slots:{monday:["18:00-20:00"], ...}}
POST   /plan/generate        {week: "2026-W47"} -> [{id, course_id, chapter_id, start, end, done}]
GET    /plan?week=2026-W47   -> sessions of the week
PATCH  /sessions/{id}        {done: true}
GET    /plan.ics             -> text/calendar
```

| Route | Précisions de MyPlan | Lot | État |
|---|---|---|---|
| `POST /courses` | Champ `file` ; nom de la matière = titre `#` du Markdown ou nom du fichier ; `hours` en heures, à une décimale | B | à faire |
| `GET /courses` | En plus : `color`, `difficulty` ; `progress` en pourcentage de 0 à 100 | A | ✅ |
| `POST /deadlines` | `type` : `exam` ou `assignment` ; `date` : `AAAA-MM-JJ`, aujourd'hui ou plus tard, sinon 422 ; `weight` : 0 à 100 | C | à faire |
| `PUT /availability` | Clés `monday` à `sunday` ; créneaux `HH:MM-HH:MM`, sans chevauchement ; remplace tous les créneaux ; `session_minutes` de 15 à 240 | C | à faire |
| `POST /plan/generate` | `week` au format ISO `AAAA-Www` ; remplace le planning de la semaine ; `start` et `end` en ISO 8601 avec fuseau | C | à faire |
| `PATCH /sessions/{id}` | `done` : `true` ou `false` | D | à faire |
| `GET /plan.ics` | `?week=` optionnel ; sans lui, toutes les sessions à venir | D | à faire |

### Extensions de MyPlan

```
POST   /auth/register        {email, password, timezone} -> 201 {access_token, refresh_token, ...}
POST   /auth/login           {email, password} -> {access_token, refresh_token, ...}
POST   /auth/refresh         {refresh_token} -> {access_token, refresh_token, ...}
POST   /auth/logout          -> 204 (révoque tous les jetons)
GET    /auth/me              -> {id, email, timezone}
GET    /courses/{id}         -> une matière et son avancement
PATCH  /courses/{id}         {name?, color?, difficulty?}
DELETE /courses/{id}         -> 204
GET    /settings             -> profil d'étude
PATCH  /settings             {reading_speed_wpm?, session_minutes?, break_min?, mastery_goal?, retention_threshold?}
```

### Règles communes à toutes les routes

| Règle | Détail |
|---|---|
| **Authentification** | Toutes les routes, sauf `/auth/register`, `/auth/login` et `/auth/refresh`, exigent `Authorization: Bearer <access_token>`. Sans jeton : `401`. Dans `/docs`, bouton « Authorize ». |
| **Isolation** | Une ressource d'un autre utilisateur répond `404`, jamais `403`. |
| **Erreurs** | Toujours `{"error": {"code", "message", "details"?}}`, message en français ([conventions](docs/conventions_de_nommage.md) §6). |
| **Heures** | Instants en ISO 8601 avec fuseau ; créneaux de disponibilité en heure locale de l'étudiant. |

---

## 4. Notre touche

Sujet §6 : une touche personnelle, **après** les 5 blocs.

| Candidate | Où on en est | Lot |
|---|---|---|
| **Compte sécurisé** : connexion, attente après échecs, jetons révocables, XSS neutralisé, en-têtes de sécurité | ✅ en place ([securite.md](docs/securite.md)) | A |
| **Replanification des sessions manquées** : une session passée non faite est replacée dans les créneaux libres suivants | à faire, après les 5 blocs | C |
| **Révision espacée** : une session de rappel quand la mémorisation d'un chapitre baisse (`R = e^(−t/S)`) | à faire, si le temps le permet | D |

La touche présentée en démo est à choisir en équipe (première question de §8).

---

## 5. Hors périmètre

| Abandonné | Pourquoi |
|---|---|
| Résumés de chapitres par LLM | Le sujet interdit toute API et toute bibliothèque d'IA dans le produit |
| Synchronisation Google Agenda (OAuth) | Remplacée par l'export `.ics`, demandé par le sujet et importable partout |
| Exceptions de disponibilité (jour bloqué, créneau ajouté) | Hors contrat ; les créneaux hebdomadaires suffisent au MVP |
| Échéances liées à des chapitres précis | Le contrat lie une échéance à une matière entière |
| Notifications par email, OCR, quiz, application mobile | Au-delà des ~4 h de développement |

---

## 6. Stack et contraintes

| Besoin | Choix |
|---|---|
| Front | Streamlit ≥ 1.36 (`st.navigation`), pages dans **`frontend/views/`** (jamais `pages/`), `streamlit-calendar` |
| API | FastAPI, Pydantic v2, pydantic-settings, Uvicorn |
| Base de données | SQLite, SQLAlchemy 2.x, Alembic (mode batch, clés étrangères activées) |
| PDF et Markdown | **`pypdf`**, `markdown-it-py` |
| Calendrier | **`icalendar`** |
| Sécurité | `pyjwt`, `argon2-cffi`, `cryptography` (Fernet), `slowapi` |
| Qualité | `ruff`, `pip-audit`, pytest, httpx |

Contraintes : **aucune bibliothèque d'IA ou de LLM** dans `requirements.txt` ; chapitres et charge viennent de règles simples. Versions figées, Python 3.12 ou plus récent.

---

## 7. Modèle de données (aperçu)

Le détail est dans [docs/modele_donnees.md](docs/modele_donnees.md). Toutes les tables d'entité ont aussi `created_at` et `updated_at`.

| Table | Champs principaux |
|---|---|
| `users` | id, email, password_hash, timezone, token_version, deleted_at |
| `user_settings` | user_id, reading_speed_wpm, session_minutes, break_min, mastery_goal, retention_threshold |
| `courses` | id, user_id, name, color, difficulty |
| `documents` | id, course_id, filename_original, storage_key, type, size_bytes, sha256, status, error_code |
| `chapters` | id, document_id, title, position, word_count, estimated_min, estimated_min_override |
| `availabilities` | id, user_id, weekday, starts_local, ends_local |
| `deadlines` | id, user_id, course_id, title, type (exam/assignment), due_date, weight |
| `plans` | id, user_id, week, version, status, origin |
| `study_sessions` | id, plan_id, chapter_id, kind, starts_at, ends_at, status (planned/done/missed), self_rating |
| `memory_states`, `notifications`, `summaries`, `google_credentials` | Prévues dans la première version de la spec, **non créées** : hors périmètre (§5) ou touche optionnelle |

---

## 8. Plan de tests et questions ouvertes

### Ce qui est testé

Le sujet demande au moins 10 tests pertinents. Au 12/11/2026 : **231 tests verts** sur le socle, la sécurité, l'authentification, les matières, le frontend et l'import (lecteurs, détection, estimation).

| Comportement | Où | Cas limites couverts |
|---|---|---|
| Planificateur | `tests/domain/test_planner.py` (lot C) | aucun créneau, temps insuffisant, échéance passée, chevauchements, changement d'heure |
| Export `.ics` | `tests/api/test_plan_ics.py` (lot D) | fuseau Europe/Paris, un VEVENT par session, semaine vide |
| Import | `tests/integrations/` (lot B) | PDF vide ou scanné, faux PDF, Markdown sans titre, fichier trop lourd |
| API | `tests/api/` | un test d'isolation (`404`) par route qui prend un identifiant ; date passée → 422 |
| Sécurité | `tests/api/test_protections.py`, `test_auth.py` | force brute, jetons révoqués, XSS, taille des requêtes |

### Questions ouvertes

| Question | Statut |
|---|---|
| Quelle touche présenter en démo ? | Ouverte (§4) |
| Une session passée et non marquée devient-elle `missed` d'elle-même ? | Ouverte ([modèle](docs/modele_donnees.md) §6.2) ; utile pour « sessions en retard » du tableau de bord |
| Que peut-on modifier sur un chapitre déjà étudié ? | Proposé : titre et durée seulement ([modèle](docs/modele_donnees.md) §6.5) |
| Un seul compte ou plusieurs ? | Tranché : un seul au départ, `user_id` conservé partout |

---

## 9. Équipe et développement

### Lots et responsables

Chaque lot possède un domaine de bout en bout : route, service, domaine, repositories, pages Streamlit et tests. Détail : [docs/repartition_taches.md](docs/repartition_taches.md).

| Lot | Responsable | Blocs du sujet | Routes du contrat | Relu par |
|---|---|---|---|---|
| A. Socle et sécurité | Marc Steven Mouthoud | compte, matières, cadre du front | `GET /courses`, `/auth/*`, `/settings` | Aminata Yasmine Savane |
| B. Import | Abraham Miguel Tala | 1 | `POST /courses` | Marc Steven Mouthoud |
| C. Planification | Houria Debbioui | 2, 3 | `/deadlines`, `PUT /availability`, `/plan/generate`, `GET /plan` | Abraham Miguel Tala |
| D. Agenda et suivi | Aminata Yasmine Savane | 4, 5 (tableau de bord) | `PATCH /sessions/{id}`, `GET /plan.ics` | Houria Debbioui |

### Où créer ses pages Streamlit

Dans **`frontend/views/`**, jamais dans `frontend/pages/` : Streamlit exécuterait ce dossier sans la vérification de connexion de `frontend/app.py`. Une page apparaît dans le menu dès que son fichier existe.

| Lot | `frontend/views/` | `frontend/api/` |
|---|---|---|
| A | `login.py`, `courses.py`, `settings.py` ✅ | `auth_api.py`, `courses_api.py` ✅ |
| B | `documents.py` (import) | `documents_api.py` |
| C | `availabilities.py`, `deadlines.py`, `plan.py` | `planning_api.py` |
| D | `dashboard.py`, composant `components/session_card.py` | `progress_api.py` |

Chaque page utilise `frontend/components/ui.py` (en-tête, erreurs, messages, suppression, dates) et `frontend/security.py`. Les pages du lot A sont des exemples à copier.

### Règles de travail

| Règle | Détail |
|---|---|
| Branches | `develop` reçoit les pull requests ; une branche `feature/*` par fonctionnalité |
| Commits | Petits, `type(portée): description` en français ; **chaque membre commite** (critère du sujet) |
| Migrations | Une par pull request au plus ; une migration fusionnée ne se modifie jamais ; relire tout `--autogenerate` (voir [AI_LOG.md](AI_LOG.md)) |
| Assistant de code | Lui donner [CLAUDE.md](CLAUDE.md) ou [.github/copilot-instructions.md](.github/copilot-instructions.md), et noter chaque échange marquant dans [AI_LOG.md](AI_LOG.md) |
| Fin d'une tâche | Tests verts, test d'isolation pour chaque route à identifiant, conventions respectées, documentation à jour |

### Livrables du sujet

| Livrable | État |
|---|---|
| `README.md` : lancer back et front en moins de 5 min | ✅ |
| `SPEC.md` écrit avant le code | ✅ (ce fichier) |
| `.github/copilot-instructions.md` et `CLAUDE.md` avec le contrat d'API | ✅ |
| Au moins 10 tests pytest pertinents, tous verts | ✅ (231) ; à compléter pour le planificateur et le `.ics` |
| `AI_LOG.md` : au moins 5 entrées, dont un échec de l'IA | ✅ ; chaque membre ajoute les siennes |
| Historique Git propre, **chaque membre commite** | En cours : lots A et B dans `develop` ; C et D ont commencé sur leurs branches |
| Démo live : import → planning → `.ics` → tableau de bord | Dépend des lots B, C, D |

---

## 10. Écarts avec la première version de cette spec

| Première version | Aujourd'hui | Raison |
|---|---|---|
| Routes sous `/api/v1/` | Sans préfixe | Contrat du sujet |
| Matière créée à la main, document importé ensuite | Matière créée par l'import (`POST /courses` avec un fichier) | Contrat du sujet |
| Échéance : importance 1-3, type `project`, instant UTC, chapitres liés | Poids 0-100, type `assignment`, date simple, matière entière | Contrat du sujet |
| Planning global jusqu'aux échéances | Planning par semaine ISO | Contrat du sujet |
| Export et synchronisation Google Agenda | Export `.ics` | Bloc 4 du sujet |
| Résumés par LLM (`anthropic`) | Retirés | Le sujet interdit toute IA dans le produit |
| PyMuPDF | `pypdf` | Recommandé par le sujet ; PyMuPDF est sous licence AGPL |
| `Spec.md` | `SPEC.md` | Nom exigé par le sujet |
