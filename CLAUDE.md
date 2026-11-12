# CLAUDE.md — mémoire du projet pour Claude Code

## Projet

MyPlan, notre version du sujet StudyPlan : import de cours (PDF, Markdown) → chapitres et heures → planning hebdomadaire → export `.ics` → tableau de bord. FastAPI + Streamlit + SQLite. **Le produit n'appelle aucune IA.**

Spécification : @SPEC.md. Lire aussi, selon la tâche : @docs/conventions_de_nommage.md, @docs/modele_donnees.md, @docs/securite.md, @docs/repartition_taches.md.

## Commandes

- Installer : `pip install -r requirements-dev.txt`, puis `python scripts/init_env.py`
- Base : `alembic upgrade head`
- API : `uvicorn backend.main:app --reload`
- Interface : `streamlit run frontend/app.py`
- Tests : `pytest -q` (après **chaque** modification)
- Lint : `ruff check . && ruff format --check .`

## Contrat d'API (figé : étendre, jamais casser)

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

Pas de préfixe. Toutes ces routes exigent `Authorization: Bearer` (`CurrentUser`). `type` : `exam` ou `assignment` ; `weight` : 0 à 100 ; une date passée → 422. Erreurs : `{"error": {"code", "message", "details"?}}`. Détail : SPEC.md §3.

## Règles

- Planifier d'abord, puis une étape à la fois ; petits commits `type(portée): description` en français après chaque étape verte.
- Rester dans le périmètre de fichiers du lot en cours (docs/repartition_taches.md §2) ; signaler toute modification hors périmètre.
- Ne jamais ajouter de dépendance, supprimer ou affaiblir un test, ni toucher à `.env` sans demander. **Aucune bibliothèque d'IA ou de LLM** dans `requirements.txt`.
- Secrets uniquement par variables d'environnement, lues dans `backend/core/config.py`.
- Chaque méthode de repository prend `user_id` en premier argument ; une ressource d'un autre utilisateur répond `404`. Un test d'isolation par route qui prend un identifiant.
- Domaine pur (`backend/domain/`) : ni base, ni réseau, ni horloge ; `now` est un paramètre.
- Instants en UTC avec fuseau (`UtcDateTime` refuse les datetime naïves) ; disponibilités en heure locale (`LocalTime`).
- Réponses de l'API par un schéma `Read`, jamais un modèle SQLAlchemy. Textes reçus typés avec `backend/api/schemas/common.py`.
- Pages Streamlit dans `frontend/views/`, **jamais** `frontend/pages/` ; cadre commun `frontend/components/ui.py` ; tout texte saisi ou importé affiché avec `escape_markdown` ; jamais de HTML brut.
- Migrations : une par pull request ; **relire et tester sur une base non vide** tout fichier produit par `--autogenerate` ; ne jamais modifier une migration déjà dans `develop`.
- En-têtes, docstrings et commentaires en français (conventions §12), identifiants en anglais.
- Noter tout échange marquant avec l'IA dans `AI_LOG.md`, échecs compris.
