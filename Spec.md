# MyPlan

> **Objectif** : MyPlan transforme les cours d'un étudiant (PDF / Markdown) en un planning de révision personnalisé. L'application extrait les chapitres, estime le temps nécessaire pour chacun, les répartit dans les créneaux réellement disponibles de l'étudiant en tenant compte des échéances (examens, rendus de projets), puis exporte le tout vers Google Agenda. Un dashboard suit la progression, le planning se réajuste automatiquement en cas d'avance ou de retard, et un modèle de mémorisation indique quand réviser pour retenir durablement.

**Stack** : Streamlit (front) · FastAPI (API) · SQLite (persistance)
**Cible** : MVP assisté par IA (specs écrites pour être données telles quelles à un assistant de code)

---

## 1. Légende des priorités

| Niveau | Signification |
|---|---|
| **P0** | Indispensable au MVP : sans cela, l'application ne rend pas son service principal |
| **P1** | Indispensable à une v1 utilisable au quotidien (sécurité, robustesse, confort) |
| **P2** | Valeur ajoutée annoncée (notifications, replanification, mémorisation) |
| **P3** | Améliorations futures |

Les fonctionnalités marquées **(implicite)** ne sont pas écrites dans le brief initial mais en découlent nécessairement.

---

## 2. Spécifications fonctionnelles

### P0 : MVP

| ID | Fonctionnalité | Détails / critères d'acceptation |
|---|---|---|
| P0-01 | **Comptes utilisateurs et authentification** (implicite) | Inscription, connexion, déconnexion. Chaque donnée appartient à un utilisateur. Sans cela, ni sécurité ni multi-étudiants. |
| P0-02 | **Gestion des matières / cours** (implicite) | Créer une matière (nom, couleur, niveau de difficulté perçu). Les documents et chapitres sont rattachés à une matière. |
| P0-03 | **Upload de documents PDF et Markdown** | Formats `.pdf` et `.md` uniquement, taille max définie, validation du type réel (pas seulement l'extension), stockage sous nom généré. |
| P0-04 | **Extraction du texte** (implicite) | PDF → texte (PyMuPDF/pdfplumber), Markdown → texte structuré. Erreur claire si le PDF est vide ou scanné (OCR en P3). |
| P0-05 | **Détection des chapitres** | Markdown : titres `#`/`##`. PDF : table des matières/signets, sinon heuristique sur les titres. Résultat : liste ordonnée (titre, nombre de mots/pages). |
| P0-06 | **Validation manuelle des chapitres** (implicite) | L'extraction automatique se trompera : l'étudiant peut renommer, fusionner, scinder, supprimer un chapitre avant de planifier. |
| P0-07 | **Estimation du temps d'étude par chapitre** | Formule transparente : `temps = (mots / vitesse_lecture) × coefficient_difficulté × coefficient_objectif`. Valeur modifiable à la main. |
| P0-08 | **Paramétrage du profil d'étude** (implicite) | Vitesse de lecture, durée max d'une session, pause entre sessions, niveau de maîtrise souhaité. Valeurs par défaut raisonnables. |
| P0-09 | **Saisie des disponibilités** | Créneaux récurrents hebdomadaires (ex. lundi 18h-20h) + exceptions ponctuelles (jour bloqué, créneau ajouté). |
| P0-10 | **Gestion des échéances** | Examens et rendus de projet : date, matière associée, chapitres concernés, importance. |
| P0-11 | **Génération du planning** | Algorithme qui répartit les sessions dans les créneaux libres, termine avant chaque échéance, respecte la durée max de session. Si c'est impossible : message explicite (« il manque X h avant le … ») au lieu d'un planning faux. |
| P0-12 | **Visualisation du planning** | Vue liste et calendrier semaine/mois dans Streamlit. |
| P0-13 | **Suivi minimal des sessions** (implicite) | Marquer une session *faite* / *non faite*. Indispensable pour tout dashboard et toute replanification. |

### P1 : v1 utilisable

| ID | Fonctionnalité | Détails |
|---|---|---|
| P1-01 | **Export Google Agenda** | OAuth2 Google, scope minimal (`calendar.events`), création d'événements. Une session = un événement. |
| P1-02 | **Synchronisation idempotente** (implicite) | Stocker l'`event_id` Google de chaque session : régénérer le planning met à jour/supprime les anciens événements, jamais de doublons. |
| P1-03 | **Dashboard de suivi** | Avancement par matière et par chapitre, heures prévues vs réalisées, jours restants avant échéance, sessions en retard. |
| P1-04 | **Fuseaux horaires** (implicite) | Heures stockées en UTC, affichées dans le fuseau de l'étudiant ; export Google cohérent. |
| P1-05 | **Détection et gestion des conflits** (implicite) | Option de lire le Google Agenda pour éviter les créneaux déjà occupés (lecture seule). |
| P1-06 | **Gestion de l'upload asynchrone** (implicite) | L'extraction ne bloque pas l'interface : statut `en cours / terminé / échec`. |
| P1-07 | **Modification et suppression des données** (implicite) | Supprimer un cours, un document, un compte ; suppression en cascade ; export des données (RGPD). |
| P1-08 | **Historique des plannings** (implicite) | Garder les versions précédentes pour comparer ou revenir en arrière. |

### P2 : valeur ajoutée

| ID | Fonctionnalité | Détails |
|---|---|---|
| P2-01 | **Replanification automatique** | Avance ou retard détectés → redistribution du temps restant sur les créneaux futurs, en priorisant les échéances proches. L'étudiant valide la proposition avant application (pas de modification silencieuse). |
| P2-02 | **Rappels de lecture** | Notification avant chaque session (email en MVP de la notif ; push/Telegram plus tard). Streamlit ne pouvant pas pousser de message seul, un **planificateur de tâches en arrière-plan** est nécessaire. |
| P2-03 | **Notification de résumé** | Avant/pendant une session : résumé de la partie du chapitre en cours, généré par LLM, stocké pour ne pas le régénérer. |
| P2-04 | **Calcul de probabilité de mémorisation** | Modèle de courbe d'oubli : `R = e^(−t/S)` où `t` = temps depuis la dernière révision, `S` = stabilité (augmente à chaque révision réussie). Affichage par chapitre et suggestion de révisions espacées. |
| P2-05 | **Auto-évaluation après session** (implicite) | Sans retour de l'étudiant (note 1-5, ou mini-quiz), le calcul de mémorisation est faux. Cette donnée alimente `S`. |
| P2-06 | **Sessions de révision espacée dans le planning** (implicite) | Le planning insère des sessions de rappel quand `R` passe sous un seuil (ex. 70 %). |
| P2-07 | **Préférences de notification** (implicite) | Canal, heure, fréquence, désactivation. |

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

Principe : **chaque couche ne parle qu'à la couche juste en dessous**. Streamlit n'accède jamais à SQLite directement, il passe uniquement par FastAPI.

```
┌──────────────────────────────────────────────────────────┐
│ 1. PRÉSENTATION        Streamlit                         │
├──────────────────────────────────────────────────────────┤
│ 2. API / TRANSPORT     FastAPI (routers, schémas Pydantic│
│                        auth, rate limiting, CORS)        │
├──────────────────────────────────────────────────────────┤
│ 3. SERVICES MÉTIER     orchestration des cas d'usage     │
├──────────────────────────────────────────────────────────┤
│ 4. DOMAINE (cœur)      algorithmes purs, sans I/O        │
├──────────────────────────────────────────────────────────┤
│ 5. PERSISTANCE         repositories, SQLite, fichiers    │
├──────────────────────────────────────────────────────────┤
│ 6. INTÉGRATIONS/INFRA  Google API, LLM, scheduler, email │
└──────────────────────────────────────────────────────────┘
```

### Répartition des fonctionnalités par couche

| Couche | Responsabilité | Fonctionnalités concernées |
|---|---|---|
| **1. Présentation (Streamlit)** | Affichage, formulaires, état de session UI. **Aucune règle métier, aucun accès DB.** | Login/inscription (P0-01), upload (P0-03), édition des chapitres (P0-06), saisie des disponibilités et échéances (P0-09/10), calendrier (P0-12), dashboard (P1-03), préférences (P2-07) |
| **2. API (FastAPI)** | Authentification, autorisation, validation des entrées, codes d'erreur, limitation de débit | Endpoints REST de toutes les fonctions ; validation Pydantic ; dépendance `get_current_user` ; contrôle de propriété de chaque ressource |
| **3. Services métier** | Orchestrer un cas d'usage de bout en bout | `IngestionService` (upload → extraction → chapitres), `PlanningService` (génération, replanification), `ProgressService` (suivi, stats dashboard), `CalendarSyncService` (export idempotent), `NotificationService`, `MemoryService` |
| **4. Domaine** | Logique pure, testable sans base ni réseau | Estimation du temps (P0-07), algorithme de planification (P0-11), détection de conflits, calcul de retard/avance (P2-01), courbe d'oubli et stabilité (P2-04), règles de révision espacée (P2-06) |
| **5. Persistance** | Lecture/écriture isolées derrière des interfaces | Repositories (`UserRepo`, `CourseRepo`, `ChapterRepo`, `SessionRepo`…), stockage des fichiers uploadés, migrations (Alembic) |
| **6. Intégrations / infra** | Tout ce qui est externe ou asynchrone | Parsing PDF/MD (P0-04), OAuth + API Google Calendar (P1-01), appel LLM pour résumés (P2-03), scheduler APScheduler/Celery (P2-02), envoi d'emails, journalisation |

> Règle pratique pour l'IA de code : si une fonction contient une formule ou une règle (« combien de temps », « où placer »), elle va en **couche 4**. Si elle appelle un service externe, **couche 6**. Si elle enchaîne plusieurs étapes, **couche 3**.

---

## 4. Sécurité multicouche

| Couche | Mesures |
|---|---|
| **Présentation** | Aucun secret ni token stocké côté Streamlit ; jeton de session en mémoire serveur ; échappement de tout contenu affiché (notamment le texte extrait des PDF) ; ne pas utiliser `unsafe_allow_html` avec du contenu utilisateur |
| **API** | Authentification par JWT à courte durée de vie (+ refresh) ; mots de passe hachés avec **argon2** ou bcrypt ; **autorisation par ressource** (un utilisateur ne lit/modifie que ses données, protection contre les IDOR) ; validation stricte Pydantic ; rate limiting (login, upload) ; CORS restrictif ; en-têtes de sécurité ; HTTPS en production |
| **Upload** | Taille maximale ; liste blanche de types ; vérification des *magic bytes* ; nom de fichier généré (jamais celui de l'utilisateur) ; stockage hors dossier public ; protection contre le path traversal ; parsing avec timeout et limites mémoire (PDF piégés) |
| **Services / domaine** | Principe du moindre privilège ; aucune requête construite à partir d'entrées brutes ; erreurs métier distinctes des erreurs techniques |
| **Persistance** | Requêtes paramétrées uniquement (ORM SQLAlchemy ou `?` placeholders) ; **chaque requête filtrée par `user_id`** dans la couche repository ; fichier SQLite hors dépôt Git avec permissions restreintes ; sauvegardes ; tokens Google **chiffrés** au repos (Fernet) |
| **Intégrations** | Scope Google minimal ; stockage chiffré du refresh token + possibilité de révoquer ; **prompt injection** : le texte des cours envoyé au LLM est traité comme donnée non fiable, sortie du LLM validée avant usage ; secrets via variables d'environnement (`.env`, jamais commités) |
| **Transverse** | Journalisation sans données sensibles ; audit des connexions et exports ; suppression des données sur demande (RGPD) ; mise à jour des dépendances (pip-audit) ; tests de sécurité sur l'autorisation |

---

## 5. Modèle de données (aperçu)

| Table | Champs principaux |
|---|---|
| `users` | id, email, password_hash, timezone, created_at |
| `user_settings` | user_id, reading_speed, max_session_min, break_min, notif_prefs |
| `courses` | id, user_id, name, color, difficulty |
| `documents` | id, course_id, filename_original, storage_path, type, status, uploaded_at |
| `chapters` | id, document_id, title, position, word_count, estimated_min, estimated_min_override |
| `availabilities` | id, user_id, weekday, start, end, valid_from, valid_to |
| `availability_exceptions` | id, user_id, date, start, end, kind (blocked/added) |
| `deadlines` | id, user_id, course_id, title, type (exam/project), due_at, importance |
| `deadline_chapters` | deadline_id, chapter_id |
| `plans` | id, user_id, version, created_at, status |
| `study_sessions` | id, plan_id, chapter_id, start, end, status (planned/done/missed), self_rating, google_event_id |
| `memory_state` | chapter_id, stability, last_review_at, retention_estimate |
| `google_credentials` | user_id, encrypted_refresh_token, scope |
| `notifications` | id, user_id, session_id, type, scheduled_at, sent_at |
| `summaries` | chapter_id, part_index, content, generated_at |

---

## 6. Technologies et bibliothèques suggérées

| Besoin | Choix |
|---|---|
| Front | Streamlit (+ `streamlit-calendar` pour la vue calendrier) |
| API | FastAPI, Pydantic v2, Uvicorn |
| Base de données | SQLite via SQLAlchemy 2.x + Alembic (mode WAL activé) |
| Auth | `python-jose` ou `pyjwt`, `passlib[argon2]` |
| PDF / Markdown | PyMuPDF (ou pdfplumber), `markdown-it-py` |
| Google | `google-auth-oauthlib`, `google-api-python-client` |
| Planification en arrière-plan | APScheduler (MVP) |
| Chiffrement | `cryptography` (Fernet) |
| Rate limiting | `slowapi` |
| LLM (résumés) | API Anthropic ou autre, derrière une interface remplaçable |
| Tests | pytest, httpx (tests API), tests unitaires sur la couche domaine |

**Point d'attention SQLite** : une seule écriture à la fois. Suffisant pour un MVP mono-serveur ; activer WAL et garder les transactions courtes.

---

## 7. Structure de projet proposée

```
myplan/
├── frontend/              # Couche 1 : Streamlit
│   ├── app.py
│   ├── pages/
│   └── api_client.py      # seul point de contact avec FastAPI
├── backend/
│   ├── api/               # Couche 2 : routers, schemas, deps (auth)
│   ├── services/          # Couche 3
│   ├── domain/            # Couche 4 : estimation, planner, memory (purs)
│   ├── repositories/      # Couche 5
│   ├── integrations/      # Couche 6 : google, llm, parsers, scheduler
│   ├── core/              # config, sécurité, logging
│   └── db/                # modèles, migrations
├── storage/               # fichiers uploadés (hors accès public)
├── tests/
└── .env.example
```

---

## 8. Ordre de développement conseillé

1. **Socle sécurisé** : auth, modèles, repositories, isolation par `user_id` (P0-01, P0-02)
2. **Ingestion** : upload, extraction, chapitres, correction manuelle (P0-03 → P0-06)
3. **Domaine pur** : estimation + planificateur, testés unitairement (P0-07, P0-11)
4. **Disponibilités, échéances, planning, vue calendrier** (P0-08 → P0-13)
5. **Export Google + dashboard** (P1)
6. **Scheduler, notifications, replanification** (P2-01, P2-02)
7. **Mémorisation et auto-évaluation** (P2-04 → P2-06)

---

## 9. Questions à trancher avant de coder

- Un seul utilisateur (outil perso) ou multi-comptes dès le départ ? (impacte fortement l'auth et l'isolation)
- Les résumés passent-ils par un LLM externe ? Si oui, les cours quittent le serveur : à signaler à l'utilisateur.
- Quel canal de notification en premier : email, Telegram, autre ?
- Les sessions replanifiées écrasent-elles les événements Google déjà créés, ou sont-elles proposées d'abord ?
- Le modèle de mémorisation est-il purement temporel ou nourri par une auto-évaluation/quiz ?
