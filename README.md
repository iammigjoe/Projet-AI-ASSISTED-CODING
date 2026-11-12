# MyPlan

MyPlan transforme les cours d'un étudiant (PDF ou Markdown) en planning de révision. L'application découpe chaque cours en chapitres, estime le temps nécessaire pour chacun et les place dans les créneaux où l'étudiant est réellement disponible, en finissant avant chaque examen ou rendu de projet. Le planning part ensuite dans Google Agenda. Un dashboard suit la progression, le planning se réajuste en cas d'avance ou de retard, et un modèle de mémorisation indique quand réviser pour retenir durablement.

**Stack** : Streamlit (interface), FastAPI (API), SQLite via SQLAlchemy (persistance), Google Calendar API (export), APScheduler (tâches en arrière-plan).

**Statut** : en conception. Les spécifications sont écrites pour être données telles quelles à un assistant de code ; le développement suit l'ordre décrit plus bas.

## Architecture

Six couches, et une règle : **les dépendances ne descendent jamais**. Streamlit ne parle qu'à FastAPI, jamais à SQLite ; l'API ne parle qu'aux services ; les services orchestrent les trois couches du bas (domaine, persistance, intégrations) ; le domaine ne dépend de rien.

Les specs écrivent « chaque couche ne parle qu'à la couche juste en dessous ». Prise à la lettre, la règle obligerait les services à passer par le domaine pour lire la base, alors que le domaine doit justement rester sans I/O : les trois couches du bas sont côte à côte sous les services, pas empilées.

```text
┌──────────────────────────────────────────────────────────┐
│ 1. PRÉSENTATION        Streamlit                         │
├──────────────────────────────────────────────────────────┤
│ 2. API / TRANSPORT     FastAPI : routers, schémas        │
│                        Pydantic, auth, rate limiting     │
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

| Couche | Rôle | Contenu |
|---|---|---|
| 1. Présentation | Affichage et formulaires, sans règle métier ni accès à la base | connexion, upload, édition des chapitres, disponibilités, échéances, calendrier, dashboard, préférences |
| 2. API | Authentification, autorisation, validation des entrées, codes d'erreur | endpoints REST, schémas Pydantic, dépendance `get_current_user`, contrôle de propriété de chaque ressource |
| 3. Services métier | Enchaîner les étapes d'un cas d'usage | `IngestionService`, `PlanningService`, `ProgressService`, `CalendarSyncService`, `NotificationService`, `MemoryService` |
| 4. Domaine | Logique pure, testable sans base ni réseau | estimation du temps, planificateur, détection de conflits, calcul d'avance ou de retard, courbe d'oubli, révisions espacées |
| 5. Persistance | Lecture et écriture, toujours filtrées par `user_id` | `UserRepository`, `CourseRepository`, `ChapterRepository`, `StudySessionRepository`…, fichiers uploadés, migrations Alembic |
| 6. Intégrations | Tout ce qui est externe ou asynchrone | parsing PDF et Markdown, OAuth et API Google Calendar, résumés par LLM, scheduler, emails, journalisation |

Pour savoir où placer une fonction : une formule ou une règle (« combien de temps », « où placer ») va dans le **domaine** ; un appel à un service externe, dans les **intégrations** ; un enchaînement de plusieurs étapes, dans les **services**.

### Parcours d'un cours

| Étape | Ce qui se passe | Couche |
|---|---|---|
| 1. Upload | Contrôle de la taille, du type réel (*magic bytes*) et stockage sous un nom généré | API, intégrations |
| 2. Extraction | PDF vers texte (PyMuPDF), Markdown vers texte structuré ; erreur claire si le PDF est vide ou scanné | intégrations |
| 3. Chapitres | Titres `#` et `##` en Markdown ; signets ou table des matières en PDF, sinon heuristique sur les titres | intégrations (lecture), domaine (détection) |
| 4. Validation | L'étudiant renomme, fusionne, scinde ou supprime des chapitres avant de planifier | présentation |
| 5. Estimation | `temps = (mots / vitesse_lecture) × coefficient_difficulté × coefficient_objectif`, modifiable à la main | domaine |
| 6. Planification | Sessions réparties dans les créneaux libres, terminées avant chaque échéance | domaine, services |
| 7. Export | Une session = un événement Google Agenda, mis à jour sans doublon | intégrations |
| 8. Suivi | Session *faite* ou *non faite*, auto-évaluation, replanification proposée | présentation, services |

## Fonctionnalités

| Priorité | Signification | Fonctionnalités |
|---|---|---|
| **P0** | MVP : sans cela, l'application ne rend pas son service | comptes, matières, upload PDF et Markdown, extraction, détection et validation des chapitres, estimation du temps, profil d'étude, disponibilités, échéances, génération et affichage du planning, suivi des sessions |
| **P1** | v1 utilisable au quotidien | export Google Agenda idempotent, dashboard, fuseaux horaires, lecture de l'agenda pour éviter les conflits, extraction asynchrone, suppression et export des données (RGPD), historique des plannings |
| **P2** | Valeur ajoutée | replanification automatique validée par l'étudiant, rappels avant chaque session, résumés de chapitres par LLM, probabilité de mémorisation, auto-évaluation, révisions espacées, préférences de notification |
| **P3** | Plus tard | OCR, quiz et flashcards, import `.docx` et `.pptx`, partage de planning, application mobile, vitesse de lecture apprise, Outlook et iCal, passage à PostgreSQL |

Le détail et les critères d'acceptation de chaque fonctionnalité sont dans les [spécifications](Spec.md).

## Décisions techniques

| Décision | Pourquoi |
|---|---|
| **Streamlit ne parle qu'à FastAPI** | Toute règle d'accès vit dans l'API : un seul endroit à sécuriser et à tester. L'interface peut être remplacée plus tard (mobile, PWA) sans toucher au reste. Les clients HTTP de `frontend/api/` sont le seul point de contact. |
| **Domaine pur, sans base ni réseau** | L'estimation, le planificateur et la courbe d'oubli sont les parties où une erreur se voit le moins et coûte le plus. Sans I/O, elles se testent unitairement, vite et sur des cas limites précis. |
| **Validation manuelle des chapitres avant de planifier** | La détection automatique se trompera, surtout sur les PDF sans signets. Un planning bâti sur de mauvais chapitres serait faux de bout en bout ; l'étudiant corrige d'abord. |
| **Formule d'estimation transparente et modifiable** | L'étudiant voit d'où vient chaque durée et peut la corriger. Une estimation opaque qu'on ne peut pas ajuster ferait perdre confiance dans tout le planning. |
| **Un planning impossible est signalé, pas produit** | Quand le temps manque, l'application l'annonce (« il manque X h avant le … ») au lieu de tasser les sessions ou de dépasser l'échéance en silence. |
| **Suivi des sessions dès le MVP** | Sans savoir ce qui a été fait, ni le dashboard, ni la replanification, ni le modèle de mémorisation ne peuvent fonctionner. |
| **Instants en UTC, disponibilités en heure locale** | Une session ou une échéance est un instant : stockée en UTC, affichée dans le fuseau de l'étudiant, exportée telle quelle vers Google. « Lundi 18 h - 20 h » est une heure de l'étudiant : stockée en UTC, elle se décalerait d'une heure à chaque changement d'heure. Voir le [modèle de données](docs/modele_donnees.md) §5. |
| **`google_event_id` gardé pour chaque session** | Régénérer le planning met à jour ou supprime les événements existants au lieu d'en créer de nouveaux : jamais de doublons dans l'agenda. |
| **Replanification proposée, pas appliquée** | Le planning de l'étudiant ne change pas sans qu'il le voie. La proposition est validée avant de toucher aux sessions et à l'agenda. |
| **Mémorisation : `R = e^(−t/S)`, nourrie par l'auto-évaluation** | `t` est le temps depuis la dernière révision, `S` la stabilité, qui augmente à chaque révision réussie. Un modèle purement temporel ignorerait ce que l'étudiant a réellement retenu ; la note de fin de session alimente `S`. Une révision est insérée quand `R` passe sous un seuil (70 % par défaut). |
| **Scheduler en arrière-plan pour les rappels** | Streamlit ne peut pas envoyer de message de lui-même. APScheduler suffit pour un serveur unique ; Celery attendra un besoin réel. |
| **Résumés générés une fois et stockés** | Un résumé ne change pas tant que le chapitre ne change pas : le stocker évite de payer et d'attendre un nouvel appel au LLM. |
| **SQLite en mode WAL** | Suffisant pour un MVP sur un seul serveur. SQLite n'accepte qu'une écriture à la fois : le mode WAL laisse les lectures continuer pendant une écriture, et les transactions restent courtes. Le passage à PostgreSQL est prévu en P3, facilité par SQLAlchemy et Alembic. |
| **LLM derrière une interface remplaçable** | Le fournisseur peut changer sans toucher aux services. Le texte des cours quitte alors le serveur : l'étudiant en est informé. |

## Sécurité

| Couche | Mesures |
|---|---|
| Présentation | Aucun secret ni token côté Streamlit ; tout contenu affiché est échappé, en particulier le texte extrait des PDF ; pas de `unsafe_allow_html` avec du contenu utilisateur |
| API | JWT à courte durée de vie avec refresh ; mots de passe hachés en argon2 ; **autorisation par ressource** contre les IDOR ; validation Pydantic stricte ; rate limiting sur la connexion et l'upload (`slowapi`) ; CORS restrictif ; HTTPS en production |
| Upload | Taille maximale ; liste blanche de types vérifiée par *magic bytes* ; nom de fichier généré, jamais celui de l'utilisateur ; stockage hors dossier public ; protection contre le path traversal ; parsing avec timeout et limite mémoire contre les PDF piégés |
| Persistance | Requêtes paramétrées uniquement ; **chaque requête filtrée par `user_id`** dans les repositories ; base SQLite hors dépôt Git ; tokens Google **chiffrés** au repos (Fernet) |
| Intégrations | Scope Google minimal (`calendar.events`) ; refresh token chiffré et révocable ; le texte des cours envoyé au LLM est traité comme une donnée non fiable (prompt injection), et sa sortie est validée avant usage ; secrets dans `.env`, jamais commité |
| Transverse | Journaux sans donnée sensible ; audit des connexions et des exports ; suppression des données sur demande (RGPD) ; dépendances vérifiées avec `pip-audit` ; tests d'autorisation |

## Modèle de données

| Table | Contenu |
|---|---|
| `users`, `user_settings` | compte, fuseau horaire, vitesse de lecture, durée max d'une session, pause, préférences de notification |
| `courses`, `documents`, `chapters` | matière (nom, couleur, difficulté), fichier uploadé et son statut d'extraction, chapitres avec nombre de mots, durée estimée et durée corrigée |
| `availabilities`, `availability_exceptions` | créneaux hebdomadaires récurrents, jours bloqués et créneaux ajoutés |
| `deadlines`, `deadline_chapters` | examens et rendus, avec date, importance et chapitres concernés |
| `plans`, `study_sessions` | versions successives du planning ; sessions avec statut (`planned`, `done`, `missed`), auto-évaluation et `google_event_id` |
| `memory_states` | stabilité et dernière révision par chapitre ; la rétention se calcule à la lecture |
| `google_credentials` | refresh token chiffré et scope accordé |
| `notifications`, `summaries` | rappels programmés et envoyés, résumés générés par partie de chapitre |

## Ordre de développement

1. **Socle sécurisé** : authentification, modèles, repositories, isolation par `user_id`
2. **Ingestion** : upload, extraction, chapitres, correction manuelle
3. **Domaine pur** : estimation et planificateur, testés unitairement
4. **Disponibilités, échéances, planning, vue calendrier**
5. **Export Google et dashboard**
6. **Scheduler, notifications, replanification**
7. **Mémorisation et auto-évaluation**

## Questions ouvertes

- Un seul utilisateur ou plusieurs comptes dès le départ ? Le choix pèse sur l'authentification et l'isolation des données.
- Les résumés passent-ils par un LLM externe ? Si oui, les cours quittent le serveur, et il faut le dire à l'utilisateur.
- Quel canal de notification en premier : email, Telegram, autre ?
- Les sessions replanifiées remplacent-elles les événements Google déjà créés, ou sont-elles d'abord proposées ?
- Le modèle de mémorisation est-il seulement temporel, ou nourri par l'auto-évaluation et des quiz ?

## Technologies

| Besoin | Choix |
|---|---|
| Interface | Streamlit, `streamlit-calendar` |
| API | FastAPI, Pydantic v2, Uvicorn |
| Base de données | SQLite, SQLAlchemy 2.x, Alembic |
| Authentification | `pyjwt`, `passlib[argon2]` |
| PDF et Markdown | PyMuPDF, `markdown-it-py` |
| Google | `google-auth-oauthlib`, `google-api-python-client` |
| Tâches en arrière-plan | APScheduler |
| Chiffrement | `cryptography` (Fernet) |
| Rate limiting | `slowapi` |
| Résumés | API Anthropic ou autre, derrière une interface |
| Tests | pytest, httpx |

## Structure du dépôt

```text
myplan/
├── frontend/              # Couche 1 : Streamlit
│   ├── app.py
│   ├── pages/
│   └── api/               # Clients HTTP par domaine, seul contact avec FastAPI
├── backend/
│   ├── api/               # Couche 2 : routers, schémas, dépendances (auth)
│   ├── services/          # Couche 3 : cas d'usage
│   ├── domain/            # Couche 4 : estimation, planificateur, mémorisation (purs)
│   ├── repositories/      # Couche 5 : accès aux données, filtrés par user_id
│   ├── integrations/      # Couche 6 : Google, LLM, parseurs, scheduler
│   ├── core/              # Configuration, sécurité, journalisation
│   └── db/                # Modèles et migrations
├── data/                  # Base SQLite (non versionnée)
├── storage/               # Fichiers uploadés, hors accès public (non versionnés)
├── tests/
├── docs/                  # Conception : conventions, modèle de données, classes, répartition
├── Spec.md                # Spécifications fonctionnelles détaillées
└── .env.example           # Variables d'environnement attendues, sans secret
```

## Documentation

| Document | Contenu |
|---|---|
| [Conventions de nommage](docs/conventions_de_nommage.md) | Nommage du code, de la base, des routes, des tests et des branches ; format des erreurs de l'API |
| [Modèle de données](docs/modele_donnees.md) | Dictionnaire, règles de gestion, MCD, MLD et choix physiques SQLite ; écarts avec les specs et questions ouvertes |
| [Diagrammes de classes](docs/diagramme_classes.md) | SOLID appliqué aux classes prévues : où sont les interfaces, et où il n'y en a volontairement pas |
| [Répartition des tâches](docs/repartition_taches.md) | Quatre lots verticaux, contrats à fixer ensemble, dépendances, relectures croisées, calendrier par phase |

## Équipe

| Membre | GitHub |
|---|---|
| Abraham Miguel Tala | [@iammigjoe](https://github.com/iammigjoe) |
| Marc Steven Mouthoud | [@majin-m](https://github.com/majin-m) |
| Debbioui Houria    | [@Houria-Deb](https://github.com/debbioui) |
| Aminata Yasmine Savane | [@Aminata20011](https://github.com/Aminata20011) |
