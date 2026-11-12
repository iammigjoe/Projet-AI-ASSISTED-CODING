# MyPlan

> **Objectif** : MyPlan transforme les cours d'un étudiant (PDF / Markdown) en un planning de révision personnalisé. L'application extrait les chapitres, estime le temps nécessaire pour chacun, les répartit dans les créneaux réellement disponibles de l'étudiant en tenant compte des échéances (examens, rendus de projets), puis exporte le tout vers Google Agenda. Un dashboard suit la progression, le planning se réajuste automatiquement en cas d'avance ou de retard, et un modèle de mémorisation indique quand réviser pour retenir durablement.

**Stack** : Streamlit (front) · FastAPI (API) · SQLite (persistance)
**Cible** : MVP assisté par IA (specs écrites pour être données telles quelles à un assistant de code)
**Équipe** : 4 personnes, un lot vertical chacune (§10)

### Documents de référence

Ces specs disent **quoi** construire. Les documents de `docs/` disent **comment**, et font foi en cas de doute sur un nom, une table ou une interface :

| Document | Fait foi pour |
|---|---|
| [docs/conventions_de_nommage.md](docs/conventions_de_nommage.md) | Noms (code, tables, routes, tests, branches, commits), format des erreurs de l'API |
| [docs/modele_donnees.md](docs/modele_donnees.md) | Tables, colonnes, contraintes, règles de gestion RG1 à RG15, questions ouvertes |
| [docs/diagramme_classes.md](docs/diagramme_classes.md) | Classes, interfaces et leurs contrats |
| [docs/repartition_taches.md](docs/repartition_taches.md) | Lots, responsables, contrats de la phase 0, relectures, calendrier |

Quand ces specs et un document de `docs/` divergent, l'écart est corrigé des deux côtés dans la même pull request.

---

## 1. Légende des priorités

| Niveau | Signification |
|---|---|
| **P0** | Indispensable au MVP : sans cela, l'application ne rend pas son service principal |
| **P1** | Indispensable à une v1 utilisable au quotidien (sécurité, robustesse, confort) |
| **P2** | Valeur ajoutée annoncée (notifications, replanification, mémorisation) |
| **P3** | Améliorations futures |

Les fonctionnalités marquées **(implicite)** ne sont pas écrites dans le brief initial mais en découlent nécessairement.

La colonne **Lot** indique le lot responsable (§10) : A socle et sécurité, B ingestion, C planification, D agenda et suivi.

---

## 2. Spécifications fonctionnelles

### P0 : MVP

| ID | Lot | Fonctionnalité | Détails / critères d'acceptation |
|---|---|---|---|
| P0-01 | A | **Comptes utilisateurs et authentification** (implicite) | Inscription, connexion, déconnexion. Chaque donnée appartient à un utilisateur. Sans cela, ni sécurité ni multi-étudiants. Email stocké en minuscules. |
| P0-02 | A | **Gestion des matières / cours** (implicite) | Créer une matière (nom, couleur, niveau de difficulté perçu de 1 à 5). Nom unique par utilisateur. Les documents et chapitres sont rattachés à une matière. |
| P0-03 | B | **Upload de documents PDF et Markdown** | Formats `.pdf` et `.md` uniquement, taille max définie (`MYPLAN_MAX_UPLOAD_BYTES`), validation du type réel par *magic bytes* (pas seulement l'extension), stockage sous un nom généré (UUID). |
| P0-04 | B | **Extraction du texte** (implicite) | PDF → texte (PyMuPDF), Markdown → texte structuré, avec limite de temps. Erreur claire si le PDF est vide ou scanné (OCR en P3) : le document passe en `failed` avec un code (`EMPTY_TEXT`, `SCANNED_PDF`, `TIMEOUT`). |
| P0-05 | B | **Détection des chapitres** | Markdown : titres `#`/`##`. PDF : table des matières/signets, sinon heuristique sur les titres. Résultat : liste ordonnée (titre, nombre de mots/pages). La lecture du fichier (intégration) est séparée de la détection (domaine pur, testable sans fichier). |
| P0-06 | B | **Validation manuelle des chapitres** (implicite) | L'extraction automatique se trompera : l'étudiant peut renommer, fusionner, scinder, supprimer un chapitre avant de planifier. Ce qui reste permis une fois un chapitre étudié est à trancher (§9). |
| P0-07 | B | **Estimation du temps d'étude par chapitre** | Formule transparente : `temps = (mots / vitesse_lecture) × coefficient_difficulté × coefficient_objectif`, en minutes entières. Valeur modifiable à la main (`estimated_min_override`), jamais écrasée par un recalcul. |
| P0-08 | A | **Paramétrage du profil d'étude** (implicite) | Vitesse de lecture (200 mots/min), durée max d'une session (90 min), pause entre sessions (15 min), niveau de maîtrise souhaité (`standard`). Valeurs par défaut entre parenthèses. |
| P0-09 | C | **Saisie des disponibilités** | Créneaux récurrents hebdomadaires (ex. lundi 18h-20h) + exceptions ponctuelles (jour bloqué, créneau ajouté). Stockés en **heure locale** de l'étudiant, pas en UTC, sinon ils se décalent au changement d'heure. |
| P0-10 | C | **Gestion des échéances** | Examens et rendus de projet : date, matière associée, chapitres concernés, importance (1 à 3). La matière et les chapitres appartiennent au même utilisateur (RG4). |
| P0-11 | C | **Génération du planning** | Algorithme qui répartit les sessions dans les créneaux libres, termine chaque chapitre avant la plus proche de ses échéances, respecte la durée max de session et la pause entre sessions. Si c'est impossible : message explicite (« il manque X h avant le … », erreur `PLAN_NOT_FEASIBLE`) au lieu d'un planning faux. L'heure courante est un paramètre de l'algorithme. |
| P0-12 | C | **Visualisation du planning** | Vue liste et calendrier semaine/mois dans Streamlit, heures affichées dans le fuseau de l'étudiant. |
| P0-13 | D | **Suivi minimal des sessions** (implicite) | Marquer une session *faite* / *non faite*. Indispensable pour tout dashboard et toute replanification. L'avancement d'un chapitre compte les sessions faites de **toutes** les versions du planning (RG12). |

### P1 : v1 utilisable

| ID | Lot | Fonctionnalité | Détails |
|---|---|---|---|
| P1-01 | D | **Export Google Agenda** | OAuth2 Google, scope minimal (`calendar.events`), création d'événements. Une session = un événement. |
| P1-02 | D | **Synchronisation idempotente** (implicite) | Garder l'`event_id` Google de chaque session : régénérer le planning met à jour/supprime les anciens événements, jamais de doublons. Comment l'identifiant passe d'une version de planning à la suivante est à trancher (§9). |
| P1-03 | D | **Dashboard de suivi** | Avancement par matière et par chapitre, heures prévues vs réalisées, jours restants avant échéance, sessions en retard. |
| P1-04 | A | **Fuseaux horaires** (implicite) | **Instants** (sessions, échéances, notifications) stockés en UTC ; **horaires récurrents** (disponibilités) en heure locale ; tout est affiché dans le fuseau de l'étudiant (nom IANA, ex. `Europe/Paris`) ; export Google cohérent. |
| P1-05 | D | **Détection et gestion des conflits** (implicite) | Option de lire le Google Agenda pour éviter les créneaux déjà occupés (lecture seule). Les sessions exportées par MyPlan ne doivent jamais compter comme occupées (§9). |
| P1-06 | B | **Gestion de l'upload asynchrone** (implicite) | L'extraction ne bloque pas l'interface : statut `pending / processing / ready / failed`, avec le code d'erreur en cas d'échec. |
| P1-07 | A | **Modification et suppression des données** (implicite) | Supprimer un cours, un document, un compte ; suppression en cascade ; export des données (RGPD). Les événements Google créés par MyPlan sont supprimés avant les lignes en base (RG15). |
| P1-08 | C | **Historique des plannings** (implicite) | Garder les versions précédentes pour comparer ou revenir en arrière. Un seul planning actif par utilisateur (RG6). |

### P2 : valeur ajoutée

| ID | Lot | Fonctionnalité | Détails |
|---|---|---|---|
| P2-01 | C | **Replanification automatique** | Avance ou retard détectés → redistribution du temps restant sur les créneaux futurs, en priorisant les échéances proches. Seules les sessions futures et prévues bougent (RG11). L'étudiant valide la proposition avant application (pas de modification silencieuse). |
| P2-02 | A | **Rappels de lecture** | Notification avant chaque session (email en MVP de la notif ; push/Telegram plus tard). Streamlit ne pouvant pas pousser de message seul, un **planificateur de tâches en arrière-plan** est nécessaire. |
| P2-03 | B | **Notification de résumé** | Avant/pendant une session : résumé de la partie du chapitre en cours, généré par LLM, stocké pour ne pas le régénérer, et régénéré si le texte du chapitre change (RG14). |
| P2-04 | D | **Calcul de probabilité de mémorisation** | Modèle de courbe d'oubli : `R = e^(−t/S)` où `t` = temps depuis la dernière révision, `S` = stabilité (augmente à chaque révision réussie). `R` est calculé à la lecture, jamais stocké. Affichage par chapitre et suggestion de révisions espacées. |
| P2-05 | D | **Auto-évaluation après session** (implicite) | Sans retour de l'étudiant (note 1-5, ou mini-quiz), le calcul de mémorisation est faux. Cette donnée alimente `S`. |
| P2-06 | C | **Sessions de révision espacée dans le planning** (implicite) | Le planning insère des sessions de rappel quand `R` passe sous un seuil (`retention_threshold`, 70 % par défaut). |
| P2-07 | A | **Préférences de notification** (implicite) | Canal, heure, fréquence, désactivation. |

### P3 : plus tard

- OCR pour PDF scannés
- Quiz/flashcards générés à partir des chapitres
- Import `.docx`, `.pptx`, liens web
- Partage de planning, mode groupe
- Application mobile / PWA, notifications push
- Apprentissage de la vitesse de lecture réelle à partir de l'historique
- Autres calendriers (Outlook, iCal)
- Passage de SQLite à PostgreSQL

---

## 3. Architecture multicouche

Principe : **les dépendances ne descendent jamais**. Streamlit ne parle qu'à FastAPI, jamais à SQLite ; l'API ne parle qu'aux services ; les services orchestrent les trois couches du bas ; le domaine ne dépend de rien. Les couches 4, 5 et 6 sont côte à côte sous les services, pas empilées : le domaine reste sans I/O.

```
┌──────────────────────────────────────────────────────────┐
│ 1. PRÉSENTATION        Streamlit                         │
├──────────────────────────────────────────────────────────┤
│ 2. API / TRANSPORT     FastAPI (routers, schémas Pydantic│
│                        auth, rate limiting, CORS)        │
├──────────────────────────────────────────────────────────┤
│ 3. SERVICES MÉTIER     orchestration des cas d'usage     │
├──────────────────┬───────────────────┬───────────────────┤
│ 4. DOMAINE       │ 5. PERSISTANCE    │ 6. INTÉGRATIONS   │
│ algorithmes purs │ repositories,     │ Google, LLM,      │
│ sans I/O         │ SQLite, fichiers  │ scheduler, email  │
└──────────────────┴───────────────────┴───────────────────┘
```

### Répartition des fonctionnalités par couche

| Couche | Responsabilité | Fonctionnalités concernées |
|---|---|---|
| **1. Présentation (Streamlit)** | Affichage, formulaires, état de session UI. **Aucune règle métier, aucun accès DB.** Clients HTTP dans `frontend/api/`, un fichier par domaine | Login/inscription (P0-01), upload (P0-03), édition des chapitres (P0-06), saisie des disponibilités et échéances (P0-09/10), calendrier (P0-12), dashboard (P1-03), préférences (P2-07) |
| **2. API (FastAPI)** | Authentification, autorisation, validation des entrées, codes d'erreur, limitation de débit | Endpoints REST sous `/api/v1/` ; validation Pydantic ; dépendance `get_current_user` ; contrôle de propriété de chaque ressource ; réponses toujours par un schéma `Read`, jamais un modèle SQLAlchemy |
| **3. Services métier** | Orchestrer un cas d'usage de bout en bout | `IngestionService` (upload → extraction → chapitres), `PlanningService` (génération, replanification), `ProgressService` (suivi, stats dashboard), `CalendarSyncService` (export idempotent), `NotificationService`, `MemoryService`, `SummaryService` |
| **4. Domaine** | Logique pure, testable sans base ni réseau ni horloge | Estimation du temps (P0-07), détection des chapitres (P0-05), créneaux libres et planificateur (P0-11), calcul de retard/avance (P2-01), courbe d'oubli et stabilité (P2-04), règles de révision espacée (P2-06) |
| **5. Persistance** | Lecture/écriture, **chaque méthode prend `user_id` en premier argument** | Repositories (`UserRepository`, `CourseRepository`, `ChapterRepository`, `StudySessionRepository`…), stockage des fichiers uploadés, migrations (Alembic) |
| **6. Intégrations / infra** | Tout ce qui est externe ou asynchrone, derrière une interface (`Protocol`) | Parsing PDF/MD (`DocumentParser`), Google Calendar (`BusyTimeReader`, `CalendarWriter`), LLM (`LlmClient`), notifications (`NotificationChannel`), scheduler APScheduler (P2-02), journalisation |

> Règle pratique pour l'IA de code : si une fonction contient une formule ou une règle (« combien de temps », « où placer », « qu'est-ce qu'un titre »), elle va en **couche 4**. Si elle appelle un service externe, **couche 6**. Si elle enchaîne plusieurs étapes, **couche 3**. Interfaces seulement là où une deuxième implémentation est annoncée ; pas d'interface pour le planificateur ni pour les repositories ([diagramme_classes.md](docs/diagramme_classes.md)).

---

## 4. Sécurité multicouche

| Couche | Mesures |
|---|---|
| **Présentation** | Aucun secret ni token stocké côté Streamlit ; jeton de session en mémoire serveur ; échappement de tout contenu affiché (notamment le texte extrait des PDF) ; ne pas utiliser `unsafe_allow_html` avec du contenu utilisateur |
| **API** | Authentification par JWT à courte durée de vie (+ refresh) ; mots de passe hachés avec **argon2** ; **autorisation par ressource** (un utilisateur ne lit/modifie que ses données, protection contre les IDOR) : une ressource d'un autre utilisateur répond `404`, jamais `403` ; `user_id` toujours tiré de `get_current_user`, jamais de la requête ; validation stricte Pydantic ; rate limiting (login, upload) ; CORS restrictif ; en-têtes de sécurité ; HTTPS en production |
| **Upload** | Taille maximale ; liste blanche de types ; vérification des *magic bytes* ; nom de fichier généré (jamais celui de l'utilisateur) ; stockage hors dossier public ; protection contre le path traversal (la base stocke une clé, pas un chemin) ; parsing avec timeout et limites mémoire (PDF piégés) |
| **Services / domaine** | Principe du moindre privilège ; aucune requête construite à partir d'entrées brutes ; erreurs métier distinctes des erreurs techniques |
| **Persistance** | Requêtes paramétrées uniquement (ORM SQLAlchemy) ; **chaque requête filtrée par `user_id`** dans la couche repository (seule exception : les méthodes `_for_all_users` du scheduler) ; `PRAGMA foreign_keys = ON` à chaque connexion, sinon les cascades ne s'appliquent pas ; fichier SQLite hors dépôt Git avec permissions restreintes ; sauvegardes ; tokens Google **chiffrés** au repos (Fernet) |
| **Intégrations** | Scope Google minimal ; stockage chiffré du refresh token + possibilité de révoquer ; **prompt injection** : le texte des cours envoyé au LLM est traité comme donnée non fiable, sortie du LLM validée avant usage ; secrets via variables d'environnement (`.env`, jamais commités) |
| **Transverse** | Journalisation sans données sensibles ; audit des connexions et exports ; suppression des données sur demande (RGPD) ; mise à jour des dépendances (pip-audit) ; un test d'isolation entre utilisateurs pour chaque endpoint qui prend un identifiant |

---

## 5. Modèle de données (aperçu)

Le détail (types, contraintes, règles de gestion, MCD, MLD) est dans [docs/modele_donnees.md](docs/modele_donnees.md). Toutes les tables d'entité ont aussi `created_at` et `updated_at`. Les colonnes `_at` sont des instants UTC ; les colonnes `_local` des heures locales.

| Table | Champs principaux |
|---|---|
| `users` | id, email, password_hash, timezone, deleted_at |
| `user_settings` | user_id, reading_speed_wpm, max_session_min, break_min, mastery_goal, retention_threshold, notif_prefs |
| `courses` | id, user_id, name, color, difficulty |
| `documents` | id, course_id, filename_original, storage_key, type, size_bytes, sha256, status, error_code, uploaded_at |
| `chapters` | id, document_id, title, position, word_count, page_start, page_end, estimated_min, estimated_min_override, is_validated |
| `availabilities` | id, user_id, weekday, starts_local, ends_local, valid_from, valid_to |
| `availability_exceptions` | id, user_id, date, starts_local, ends_local, kind (blocked/added) |
| `deadlines` | id, user_id, course_id, title, type (exam/project), due_at, importance |
| `deadline_chapters` | deadline_id, chapter_id |
| `plans` | id, user_id, version, status (draft/active/archived), origin, parent_plan_id, activated_at |
| `study_sessions` | id, plan_id, chapter_id, kind (study/review), starts_at, ends_at, status (planned/done/missed), self_rating, completed_at, google_event_id |
| `memory_states` | chapter_id, stability_days, last_review_at, review_count |
| `google_credentials` | user_id, encrypted_refresh_token, scope, calendar_id, revoked_at |
| `notifications` | id, user_id, study_session_id, type, channel, scheduled_at, sent_at, attempts |
| `summaries` | chapter_id, part_index, content, source_sha256, model, generated_at |

Écarts avec la première version de ces specs, justifiés dans le modèle de données : `start`/`end` → `starts_at`/`ends_at` ou `starts_local`/`ends_local` (`END` est réservé en SQL, et les disponibilités sont en heure locale) ; `storage_path` → `storage_key` ; `retention_estimate` retiré (il dépend de l'heure de lecture) ; `memory_state` → `memory_states` ; `session_id` → `study_session_id`.

---

## 6. Technologies et bibliothèques suggérées

| Besoin | Choix |
|---|---|
| Front | Streamlit ≥ 1.36 (`st.navigation` pour des titres de pages en français) + `streamlit-calendar` pour la vue calendrier |
| API | FastAPI, Pydantic v2, pydantic-settings, Uvicorn |
| Base de données | SQLite via SQLAlchemy 2.x + Alembic (mode WAL, clés étrangères activées) |
| Auth | `pyjwt`, `passlib[argon2]` |
| PDF / Markdown | PyMuPDF, `markdown-it-py` |
| Google | `google-auth-oauthlib`, `google-api-python-client` |
| Planification en arrière-plan | APScheduler (MVP) |
| Chiffrement | `cryptography` (Fernet) |
| Rate limiting | `slowapi` |
| LLM (résumés) | API Anthropic ou autre, derrière l'interface `LlmClient` |
| Qualité | `ruff` (format et lint), `pip-audit` |
| Tests | pytest, httpx (tests API), tests unitaires sur la couche domaine |

**Point d'attention SQLite** : une seule écriture à la fois. Suffisant pour un MVP mono-serveur ; activer WAL, `busy_timeout`, et garder les transactions courtes. SQLite n'a pas de type date : un type `UtcDateTime` refuse les `datetime` sans fuseau.

---

## 7. Structure de projet

```
myplan/
├── frontend/              # Couche 1 : Streamlit
│   ├── app.py             # Point d'entrée et menu (st.navigation)
│   ├── pages/             # Une page par écran, noms en anglais
│   ├── components/        # Morceaux d'interface réutilisés
│   └── api/               # Un client HTTP par domaine, seul contact avec FastAPI
├── backend/
│   ├── api/               # Couche 2 : routers, schemas, deps (auth), errors
│   ├── services/          # Couche 3
│   ├── domain/            # Couche 4 : estimation, chapter_detection, planner, memory (purs)
│   ├── repositories/      # Couche 5
│   ├── integrations/      # Couche 6 : google, llm, parsers, notifications, scheduler
│   ├── core/              # config, sécurité, logging, container (branchement des implémentations)
│   └── db/                # modèles, types, migrations
├── data/                  # base SQLite (non versionnée)
├── storage/               # fichiers uploadés (hors accès public, non versionnés)
├── tests/                 # même arborescence que backend/, plus fixtures/
├── docs/                  # conventions, modèle de données, classes, répartition
└── .env.example
```

---

## 8. Ordre de développement

L'ordre est découpé en phases, chacune terminée par une démonstration de bout en bout ([répartition](docs/repartition_taches.md) §7). Dans chaque phase, les quatre lots avancent en parallèle.

| Phase | Contenu | Fonctionnalités |
|---|---|---|
| **0. Contrats** | Squelette, CI, modèles et première migration, objets du domaine partagés, format des erreurs, fabriques de test, branche `develop` ; trancher les questions qui bloquent (§9) | — |
| **1. MVP** | Socle sécurisé et isolation par `user_id` ; ingestion ; estimation et planificateur testés unitairement ; disponibilités, échéances, planning, vue calendrier ; suivi des sessions | P0-01 → P0-13 |
| **2. v1** | Export Google, dashboard, fuseaux, conflits, extraction asynchrone, RGPD, historique | P1-01 → P1-08 |
| **3. Valeur ajoutée** | Scheduler, notifications, replanification, résumés, mémorisation et auto-évaluation | P2-01 → P2-07 |

---

## 9. Questions à trancher

| Question | Statut | Bloque |
|---|---|---|
| Un seul utilisateur (outil perso) ou multi-comptes dès le départ ? | Ouverte. Le modèle est écrit pour plusieurs comptes, ce qui ne coûte presque rien | Lot A, phase 0 |
| Les résumés passent-ils par un LLM externe ? Si oui, les cours quittent le serveur : à signaler à l'utilisateur | Ouverte. L'interface `LlmClient` permet un modèle local | Lot B, phase 3 |
| Quel canal de notification en premier : email, Telegram, autre ? | Proposé : email | Lot A, phase 3 |
| Les sessions replanifiées écrasent-elles les événements Google déjà créés, ou sont-elles proposées d'abord ? | Tranché par P2-01 : proposées d'abord, exportées après validation | — |
| Le modèle de mémorisation est-il purement temporel ou nourri par une auto-évaluation/quiz ? | Tranché par P2-05 : nourri par l'auto-évaluation ; quiz en P3 | — |
| Une échéance sans chapitre porte-t-elle sur toute sa matière ? Un chapitre sans échéance est-il planifié ? | Ouverte ([modèle](docs/modele_donnees.md) §6.6) | Lot C, phase 1 |
| Que peut-on encore modifier sur un chapitre déjà étudié ? | Proposé : titre et durée seulement ([modèle](docs/modele_donnees.md) §6.5) | Lot B, phase 1 |
| Une session passée et non marquée devient-elle `missed` d'elle-même ? | Ouverte ([modèle](docs/modele_donnees.md) §6.2) | Lot D et C, phases 1 et 3 |
| Comment l'`event_id` Google passe-t-il d'une version de planning à la suivante ? | Proposé : table de synchronisation ([modèle](docs/modele_donnees.md) §6.1) | Lot D, fin de phase 1 |
| Comment éviter que MyPlan lise ses propres sessions comme « occupées » ? | Proposé : agenda Google dédié ([modèle](docs/modele_donnees.md) §6.4) | Lot D, fin de phase 1 |
| Comment découper un chapitre en parties pour les résumés ? | Ouverte ([modèle](docs/modele_donnees.md) §6.3) | Lot B, phase 3 |

Une question tranchée est reportée ici et dans le document concerné, dans la même pull request.

---

## 10. Développement en équipe

### Lots et responsables (MVP)

Chaque lot possède un domaine **de bout en bout** : router, service, domaine, repositories, pages Streamlit et tests. Détail des fichiers possédés et des livrables par phase : [docs/repartition_taches.md](docs/repartition_taches.md).

| Lot | Responsable | Fonctionnalités | Relu par |
|---|---|---|---|
| A. Socle et sécurité | Marc Steven Mouthoud | P0-01, P0-02, P0-08, P1-04, P1-07, P2-02, P2-07 | Aminata Yasmine Savane |
| B. Ingestion | Abraham Miguel Tala | P0-03 → P0-07, P1-06, P2-03 | Marc Steven Mouthoud |
| C. Planification | Houria Debbioui | P0-09 → P0-12, P1-08, P2-01, P2-06 | Abraham Miguel Tala |
| D. Agenda et suivi | Aminata Yasmine Savane | P0-13, P1-01, P1-02, P1-03, P1-05, P2-04, P2-05 | Houria Debbioui |

Attribution tirée au sort pour le MVP, puis lots A et D échangés ; revue avant la phase 2.

### Contrats entre lots

Fixés ensemble en phase 0, dans une seule pull request relue par tous. Ensuite, un changement de contrat passe par une pull request dédiée, relue par les lots concernés.

| Contrat | Fichier | Entre |
|---|---|---|
| Modèles et première migration | `backend/db/models/` | tous |
| Énumérations | `backend/domain/enums.py` | tous |
| `ParsedDocument`, `DetectedChapter` | `backend/domain/documents.py` | B → C |
| `ChapterToPlan`, `FreeSlot`, `PlannedSession`, `PlanResult` | `backend/domain/planning.py` | B → C → D |
| Format des erreurs | `backend/api/errors.py` | tous |
| Client HTTP commun | `frontend/api/base.py` | tous |
| Fabriques de test | `tests/fixtures/factories.py` | tous |

Chaque lot code contre ces contrats avec des données de test, sans attendre que les autres lots soient finis.

### Règles de travail

| Règle | Détail |
|---|---|
| Branches | `main` stable, `develop` intégration, une branche `feature/*`, `fix/*`, `docs/*`… par fonctionnalité, partie de `develop` à jour |
| Pull requests | Vers `develop`, relue par le binôme du tableau ci-dessus, CI verte |
| Commits | `type(portée): description`, en français ([conventions](docs/conventions_de_nommage.md) §10) |
| Migrations | Une par pull request au plus ; `alembic heads` doit afficher une seule tête avant la fusion ; relue par le lot A |
| Fichiers partagés | `main.py`, `container.py`, `enums.py`, `errors.py`, `requirements.txt` : ajouts à la fin de la section du lot, une ligne par entrée |
| Périmètre | Chacun modifie les fichiers de son lot ; toute modification hors périmètre est signalée dans la pull request |

### Fin d'une tâche

Une pull request est fusionnée seulement si :

- les tests passent, et les tests du domaine couvrent les cas limites (échéance passée, aucun créneau, chapitre de zéro mot, changement d'heure) ;
- chaque endpoint qui prend un identifiant a son test d'isolation (`404` pour un autre utilisateur) ;
- les noms respectent les [conventions](docs/conventions_de_nommage.md) ;
- la documentation touchée est à jour : ces specs, le modèle de données si une table change, le diagramme de classes si une interface change.

### Consignes pour l'assistant de code

À donner avec chaque demande, en plus de ces specs :

1. Les [conventions de nommage](docs/conventions_de_nommage.md) et les fichiers de contrat ci-dessus.
2. Le lot concerné et son périmètre de fichiers : l'assistant ne modifie rien en dehors sans le dire.
3. Les règles qui ne se devinent pas : `user_id` en premier argument de chaque méthode de repository ; `now` en paramètre dans le domaine ; instants en UTC avec fuseau, disponibilités en heure locale ; réponse API toujours par un schéma `Read` ; en-tête encadré, sections, docstrings et commentaires en français selon le [§12 des conventions](docs/conventions_de_nommage.md#12-commentaires-et-docstrings).
4. Le code produit est relu comme un code humain : l'assistant ne connaît que les décisions écrites dans `docs/` et ici.
