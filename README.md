# MyPlan

MyPlan est notre version du sujet **StudyPlan** : l'étudiant importe ses cours (PDF ou Markdown) et ses échéances, MyPlan en tire des chapitres et une charge en heures, construit un planning de révision hebdomadaire dans ses créneaux libres, l'exporte en calendrier `.ics` et suit l'avancement dans un tableau de bord. **Le produit n'appelle aucune API d'IA** : l'IA a servi à le construire, pas à le faire tourner.

**Stack** : FastAPI (API), Streamlit (interface), SQLite via SQLAlchemy et Alembic (persistance), `pypdf` et `markdown-it-py` (import), `icalendar` (export), pytest et ruff (qualité).

**Où en est le projet** : socle, sécurité, compte, matières et cadre de l'interface sont faits (lot A). L'import, le planificateur, l'export `.ics` et le tableau de bord sont en cours (lots B, C, D). Le détail par bloc est dans [SPEC.md](SPEC.md) §2.

## Démarrage rapide

Python 3.12 ou plus récent. Depuis la racine du dépôt :

```bash
python -m venv .venv
.venv\Scripts\activate                # Windows ; macOS ou Linux : source .venv/bin/activate
pip install -r requirements-dev.txt
python scripts/init_env.py            # crée .env avec des clés secrètes générées
alembic upgrade head                  # crée la base data/myplan.db
```

Puis, dans deux terminaux (venv activé dans chacun) :

```bash
uvicorn backend.main:app --reload     # API : http://localhost:8000 (documentation : /docs)
streamlit run frontend/app.py         # interface : http://localhost:8501
```

Au premier lancement, l'onglet **« Créer le compte »** de la page de connexion crée le compte unique de l'application.

Dans la documentation interactive (`/docs`), toutes les routes du contrat demandent un jeton : appeler `POST /auth/login`, copier `access_token`, puis le coller dans **Authorize**.

### Vérifier

```bash
pytest                                # tests, tous verts
ruff check . && ruff format --check . # lint et mise en forme
pip-audit -r requirements.txt         # failles connues dans les dépendances
```

## Démo

Les données de démo du sujet sont dans [`sample_data/`](sample_data/) : 3 cours Markdown (statistiques, machine learning, cloud et MLOps), [`deadlines.csv`](sample_data/deadlines.csv) (6 échéances, du 24 novembre au 18 décembre 2026) et [`availability.json`](sample_data/availability.json) (créneaux de la semaine, sessions de 60 minutes).

Parcours de démo du sujet : **import → planning → `.ics` → tableau de bord**.

1. Importer les 3 cours de `sample_data/` (page Importer, plusieurs fichiers à la fois).
2. Saisir les échéances de `deadlines.csv` et les créneaux de `availability.json` (pages Échéances et Disponibilités).
3. Générer le planning de la semaine (page Planning), marquer une session faite.
4. Télécharger le `.ics` et l'ouvrir dans Google Agenda ou Outlook.
5. Montrer l'avancement par matière (page Tableau de bord).

## Contrat d'API

Le contrat du sujet est repris **à l'identique, sans préfixe** ; MyPlan l'étend sans jamais le casser. Détail des champs, des erreurs et des extensions : [SPEC.md](SPEC.md) §3.

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

Extension principale : **toutes ces routes demandent un jeton** (`Authorization: Bearer …`), obtenu par `POST /auth/login`. Sans jeton, la réponse est `401`.

## Architecture

Six couches, et une règle : **les dépendances ne descendent jamais**. Streamlit ne parle qu'à FastAPI, jamais à SQLite ; l'API ne parle qu'aux services ; les services orchestrent les trois couches du bas ; le domaine ne dépend de rien.

```text
┌──────────────────────────────────────────────────────────┐
│ 1. PRÉSENTATION        Streamlit (frontend/)             │
├──────────────────────────────────────────────────────────┤
│ 2. API                 FastAPI : routes, schémas,        │
│                        authentification, protections     │
├──────────────────────────────────────────────────────────┤
│ 3. SERVICES            un service par cas d'usage        │
├──────────────────┬───────────────────┬───────────────────┤
│ 4. DOMAINE       │ 5. PERSISTANCE    │ 6. INTÉGRATIONS   │
│ planificateur,   │ repositories,     │ pypdf, Markdown,  │
│ estimation (pur) │ SQLite            │ icalendar         │
└──────────────────┴───────────────────┴───────────────────┘
```

Pour savoir où placer une fonction : une formule ou une règle (« combien de temps », « où placer ») va dans le **domaine** ; un appel à une bibliothèque de fichiers ou de calendrier, dans les **intégrations** ; un enchaînement de plusieurs étapes, dans les **services**.

## Décisions techniques

| Décision | Pourquoi |
|---|---|
| **Contrat du sujet repris à l'identique** | « Étendez-le, ne le cassez jamais » : nos routes en plus (`/auth/*`, `PATCH /courses/{id}`, `/settings`) n'en modifient aucune. Le préfixe `/api/v1` d'abord prévu a été retiré pour coller au contrat. |
| **Connexion obligatoire, même sur les routes du contrat** | L'API est joignable sur le réseau et contient les cours et le planning de l'étudiant. La grille du sujet valorise une sécurité vérifiée. |
| **Un seul compte** | Outil personnel : l'inscription se ferme dès le premier compte. `user_id` reste dans toutes les tables pour ouvrir plusieurs comptes sans migration. |
| **Domaine pur, testé sans base ni réseau** | Le planificateur et l'estimation sont là où une erreur se voit le moins et coûte le plus ; sans I/O, ils se testent vite et sur des cas limites précis. `now` est un paramètre : un test ne dépend pas du jour où il tourne. |
| **Instants en UTC, disponibilités en heure locale** | Une session ou une échéance est un instant ; « lundi 18 h - 20 h » est une heure de l'étudiant. Stockée en UTC, elle se décalerait d'une heure à chaque changement d'heure. |
| **Un planning par semaine ISO** | Contrat : `POST /plan/generate {week}`. Régénérer une semaine archive la version précédente ; un seul planning actif par semaine (index unique partiel). |
| **`.ics` au lieu d'une synchronisation Google** | Bloc 4 du sujet : un fichier qui s'importe partout, sans OAuth ni jeton tiers à protéger. Un `UID` stable par session évite les doublons à la réimportation. |
| **Aucune bibliothèque d'IA** | Exigé par le sujet. Les résumés par LLM d'abord prévus ont été retirés. |
| **`pypdf` plutôt que PyMuPDF** | Recommandé par le sujet ; PyMuPDF est sous licence AGPL. |
| **Migrations relues à la main** | `--autogenerate` a produit une migration qui échouait sur toute base non vide et oubliait des contraintes ; elle a été réécrite ([AI_LOG.md](AI_LOG.md)). |
| **Pages dans `frontend/views/`, pas `pages/`** | Streamlit exécute directement un dossier `pages/`, sans la vérification de connexion de `frontend/app.py`. Trouvé en testant ; un test l'empêche de revenir. |

## Sécurité

| Menace | Protection |
|---|---|
| Force brute sur la connexion | Limite par IP ; attente exponentielle après 5 échecs, par email et par IP ; même réponse que l'email existe ou non |
| Vol de jeton | Jeton d'accès de 15 min ; jetons révocables d'un coup (déconnexion) ; types d'accès et de rafraîchissement non interchangeables |
| Accès aux données d'un autre | `user_id` tiré du jeton uniquement, filtré dans chaque requête ; `404` pour une ressource d'un autre |
| XSS (titre de chapitre, nom de matière) | Texte nettoyé à l'entrée, échappé à l'affichage ; HTML brut interdit dans le frontend, vérifié par un test |
| Fichiers piégés, saturation | Taille maximale, type vérifié par *magic bytes*, nom de stockage généré ; limite de requêtes par IP |

Détail, limites connues et règles par lot : [docs/securite.md](docs/securite.md).

## Structure du dépôt

```text
myplan/
├── frontend/                        # Couche 1 : interface Streamlit, sans règle métier ni accès à la base
│   ├── app.py                       # Point d'entrée : connexion obligatoire, menu (titres français)
│   ├── views/                       # Pages, un fichier par écran ; jamais de dossier « pages/ »
│   ├── components/                  # Cadre commun (ui.py) et composants réutilisés
│   └── api/                         # Clients HTTP par domaine, seul contact avec FastAPI
├── backend/
│   ├── main.py                      # Application FastAPI : protections, erreurs, routes
│   ├── api/                         # Couche 2 : routes, schémas, authentification, protections
│   ├── services/                    # Couche 3 : cas d'usage
│   ├── domain/                      # Couche 4 : planificateur, estimation, règles (pur)
│   ├── repositories/                # Couche 5 : requêtes, toujours filtrées par user_id
│   ├── integrations/                # Couche 6 : lecture des fichiers, export .ics
│   ├── core/                        # Configuration, sécurité, horloge
│   └── db/                          # Modèles SQLAlchemy, types, migrations Alembic
├── tests/                           # Tests pytest, même découpage que backend/ et frontend/
├── sample_data/                     # Données de démo du sujet (3 cours, échéances, disponibilités)
├── scripts/init_env.py              # Crée .env avec des clés secrètes générées
├── docs/                            # Conception : conventions, modèle de données, classes, répartition, sécurité
├── SPEC.md                          # Spécification : MVP, contrat d'API, touche, hors périmètre
├── AI_LOG.md                        # Journal de notre usage de l'IA, échecs compris
├── CLAUDE.md                        # Consignes pour Claude Code
├── .github/
│   ├── copilot-instructions.md      # Consignes pour GitHub Copilot, contrat d'API compris
│   └── workflows/ci.yml             # CI : ruff, une seule tête Alembic, pytest, pip-audit
├── data/                            # Base SQLite locale (non versionnée)
├── storage/                         # Fichiers importés, nommés par UUID (non versionnés)
├── requirements.txt                 # Dépendances, versions figées ; aucune bibliothèque d'IA
├── requirements-dev.txt             # pytest, ruff, pip-audit
├── pyproject.toml                   # Configuration de ruff et pytest
├── alembic.ini                      # Configuration des migrations
├── .streamlit/config.toml           # Pas de trace d'erreur dans le navigateur, XSRF actif
└── .env.example                     # Variables d'environnement attendues, sans secret
```

## Documentation

| Document | Contenu |
|---|---|
| [SPEC.md](SPEC.md) | Les 5 blocs, le contrat d'API, notre touche, le hors-périmètre, les livrables |
| [AI_LOG.md](AI_LOG.md) | Notre usage de l'IA : prompts, vérifications, échecs détectés |
| [Conventions de nommage](docs/conventions_de_nommage.md) | Nommage, routes, format des erreurs, commentaires et docstrings |
| [Modèle de données](docs/modele_donnees.md) | Dictionnaire, règles de gestion, MCD, MLD, choix physiques SQLite |
| [Diagrammes de classes](docs/diagramme_classes.md) | SOLID appliqué : où sont les interfaces, et où il n'y en a volontairement pas |
| [Sécurité](docs/securite.md) | Protections en place, limites connues, règles par lot |
| [Répartition des tâches](docs/repartition_taches.md) | Lots, responsables, sprints, relectures croisées |

## Équipe

| Membre | Lot | GitHub |
|---|---|---|
| Marc Steven Mouthoud | A. Socle et sécurité | [@majin-m](https://github.com/majin-m) |
| Abraham Miguel Tala | B. Import | [@iammigjoe](https://github.com/iammigjoe) |
| Houria Debbioui | C. Planification | [@Houria-Deb](https://github.com/debbioui) |
| Aminata Yasmine Savane | D. Agenda et suivi | [@Aminata20011](https://github.com/Aminata20011) |
