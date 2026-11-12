# Répartition des tâches

Proposition de découpage du travail entre les quatre membres de l'équipe, pour que chacun avance sans attendre les autres et que les pull requests se marchent le moins possible dessus. Elle s'appuie sur les priorités des [specs](../SPEC.md), l'[architecture](../README.md#architecture), le [modèle de données](modele_donnees.md) et les [diagrammes de classes](diagramme_classes.md).

Les lots du MVP ont été tirés au sort (§8) ; l'attribution sera revue avant la phase 2.

---

## 1. Principe : des lots verticaux, pas des couches

Un découpage par couche (une personne sur Streamlit, une sur l'API, une sur le domaine, une sur la base) a l'air naturel : il colle au schéma d'architecture. Il fait pourtant attendre tout le monde.

| Découpage | Ce qui se passe |
|---|---|
| **Par couche** | Le frontend attend l'API, qui attend les services, qui attendent les repositories. Une fonctionnalité traverse quatre personnes avant de marcher. Chaque fonctionnalité oblige quatre personnes à se mettre d'accord |
| **Par lot vertical** | Chaque personne possède un domaine fonctionnel **de bout en bout** : son router, son service, son domaine, ses repositories, ses pages Streamlit et ses tests. Elle livre des fonctionnalités qui marchent, et ne dépend des autres que par quelques contrats fixés au départ |

MyPlan se découpe bien verticalement : l'ingestion, la planification et le suivi sont trois chaînes presque indépendantes, reliées par deux objets seulement (le chapitre, la session). Un quatrième lot porte le socle commun.

---

## 2. Les quatre lots

### Vue d'ensemble

Depuis le 12/11/2026, les lots suivent les **5 blocs du sujet StudyPlan** et son contrat d'API ([SPEC.md](../SPEC.md) §2 et §3).

| Lot | Domaine | Blocs du sujet | Routes du contrat | Pages Streamlit, dans `frontend/views/` |
|---|---|---|---|---|
| **A. Socle et sécurité** | Compte, matières, profil, base, sécurité, cadre du front | compte (extension), matières | `GET /courses`, `/auth/*`, `/settings` | `login.py`, `courses.py`, `settings.py`, point d'entrée `frontend/app.py` (**faits**) |
| **B. Import** | Du fichier aux chapitres estimés | 1 | `POST /courses` (multipart) | `documents.py` (écran d'import) |
| **C. Planification** | Disponibilités, échéances, planificateur | 2, 3 | `POST/GET/DELETE /deadlines`, `PUT /availability`, `POST /plan/generate`, `GET /plan` | `availabilities.py`, `deadlines.py`, `plan.py` |
| **D. Agenda et suivi** | Sessions faites, export `.ics`, tableau de bord | 4, 5 | `PATCH /sessions/{id}`, `GET /plan.ics` | `dashboard.py`, composant `frontend/components/session_card.py` |

Les pages se créent dans **`frontend/views/`**, jamais dans un dossier `pages/` : Streamlit exécuterait ce dernier sans passer par la vérification de connexion de `frontend/app.py`. Une page apparaît dans le menu dès que son fichier existe ([SPEC.md](../SPEC.md) §9).

Le planificateur (C) est la pièce la plus délicate et la plus regardée en démo. Le lot A, terminé pour le MVP, peut aider C sur les tests du planificateur, et B ou D sur leurs pages.

### Lot A : socle et sécurité (fait)

| Livré | Où |
|---|---|
| Socle : dépendances, configuration, base SQLite, modèles, migrations, CI | `backend/core/`, `backend/db/`, `.github/workflows/` |
| Sécurité : force brute, XSS, jetons révocables, taille des requêtes, en-têtes | [securite.md](securite.md) |
| Compte unique : inscription, connexion, renouvellement, déconnexion | `backend/api/routers/auth.py` |
| Matières avec avancement (`GET /courses`), profil d'étude (`/settings`) | `backend/api/routers/courses.py`, `settings.py` |
| Front : point d'entrée, connexion, matières, paramètres, cadre commun | `frontend/app.py`, `frontend/views/`, `frontend/components/ui.py` |

Fichiers possédés : `backend/core/`, `backend/db/` (chaque lot fait évoluer les modèles de ses tables), `backend/api/deps.py`, `errors.py`, `middleware.py`, `rate_limit.py`, routers `auth.py`, `courses.py`, `settings.py`, `frontend/app.py`, `frontend/api/base.py`, `frontend/components/ui.py`, `.github/`.

**A est aussi gardien des migrations** : il relit toute pull request qui en contient une (§5).

### Lot B : import (bloc 1)

| Livrable | Détail |
|---|---|
| `POST /courses` multipart | Champ `file` ; crée la matière (nom = titre `#` ou nom du fichier), le document et les chapitres ; répond `{id, name, chapters:[{id,title,hours}], hours_total}` ; `@limiter.limit(UPLOAD_LIMIT)` |
| Validation du fichier | `UploadValidator` : taille, *magic bytes* (`%PDF-`), jamais l'extension seule ; nom de stockage généré |
| Lecture | `PdfParser` avec **`pypdf`** et limite de pages, `MarkdownParser` avec `markdown-it-py` |
| Détection des chapitres | `domain/chapter_detection.py`, pur : titres `##` en Markdown, signets ou heuristique en PDF |
| Charge en heures | `domain/estimation.py` : `max(1 h, mots / (vitesse × 60) × coefficients)` |
| Page d'import | `frontend/views/documents.py`, avec `escape_markdown` pour les titres de chapitres |
| Tests | Les 3 cours de `sample_data/`, un PDF, un faux PDF, un fichier vide, un fichier trop lourd |

Fichiers possédés : `backend/domain/chapter_detection.py`, `estimation.py`, `documents.py`, `backend/services/ingestion_service.py`, `backend/integrations/parsers/`, `storage/`, router `documents.py` (`POST /courses`) et `chapters.py`.

### Lot C : planification (blocs 2 et 3)

| Livrable | Détail |
|---|---|
| Échéances | `POST /deadlines` (date passée → 422, `weight` 0-100, type `exam`/`assignment`), `GET /deadlines` triées par date, `DELETE /deadlines/{id}` → 204 |
| Disponibilités | `PUT /availability {session_minutes, slots}` remplace tous les créneaux ; heures locales |
| Créneaux libres | `domain/free_slots.py` : créneaux de la semaine en heure locale → instants UTC, changements d'heure testés |
| **Planificateur** | `domain/planner.py`, **pur** : sessions de `session_minutes` dans les créneaux libres, sans chevauchement, avant l'échéance ; priorité aux échéances proches et lourdes ; manque signalé |
| Routes du planning | `POST /plan/generate {week}`, `GET /plan?week=` |
| Pages | `availabilities.py`, `deadlines.py`, `plan.py` (vue de la semaine) |
| Tests | Au moins 10 tests du planificateur, sur les données de `sample_data/` et les cas limites |

Fichiers possédés : `backend/domain/planner.py`, `free_slots.py`, `planning.py`, `backend/services/planning_service.py`, routers `deadlines.py`, `availability.py`, `plan.py`.

### Lot D : agenda et suivi (blocs 4 et 5)

| Livrable | Détail |
|---|---|
| Session faite | `PATCH /sessions/{id} {done}` ; composant `session_card.py` utilisé par la page Planning de C |
| **Export `.ics`** | `GET /plan.ics` avec **`icalendar`** : `text/calendar`, un `VEVENT` par session, « Matière — Chapitre » en titre, `UID` stable, heures en Europe/Paris ; tester l'import dans Google Agenda et Outlook |
| Tableau de bord | `dashboard.py` : avancement en % par matière (déjà renvoyé par `GET /courses`), sessions faites et en retard, 3 prochaines échéances |
| Tests | `.ics` valide et relu par `icalendar`, fuseau juste, semaine vide ; isolation de `PATCH /sessions/{id}` |

Fichiers possédés : `backend/domain/progress.py`, `backend/services/progress_service.py`, `backend/integrations/ics/`, routers `sessions.py` et la route `GET /plan.ics`, `frontend/views/dashboard.py`, `frontend/components/session_card.py`.

---

## 3. Phase 0 : ce qu'on fixe ensemble avant de se séparer

Les lots ne sont indépendants que si leurs frontières sont fixées **avant** que chacun écrive son code. Cette phase se fait à quatre, de préférence en une ou deux séances communes, et se termine par une seule pull request relue par tous.

| Contrat | Fichier | Rédigé par | Validé par |
|---|---|---|---|
| Modèles SQLAlchemy de toutes les tables P0, et première migration | `backend/db/models/` | A | tous |
| Énumérations | `backend/domain/enums.py` | A | tous |
| `ParsedDocument`, `DetectedChapter` | `backend/domain/documents.py` | B | C |
| `ChapterToPlan`, `FreeSlot`, `PlannedSession`, `PlanResult` | `backend/domain/planning.py` | C | B, D |
| Format des erreurs et codes connus | `backend/api/errors.py` | A | tous |
| Schémas Pydantic des endpoints P0 | `backend/api/schemas/` | chacun pour son lot | A |
| Client HTTP commun du frontend | `frontend/api/base.py` | A | tous |
| Fabriques de données de test | `tests/fixtures/factories.py` | D | tous |

La phase 0 tranche aussi les questions qui bloqueraient un lot plus tard :

| Question | Bloque | Où |
|---|---|---|
| ~~Échéances sans chapitres, chapitres sans échéance~~ | Tranché par le contrat : une échéance porte sur toute sa matière | [modele_donnees.md](modele_donnees.md) §6.6 |
| Modifier un chapitre déjà étudié | L'édition des chapitres (B) | [modele_donnees.md](modele_donnees.md) §6.5 |
| ~~Un compte ou plusieurs~~ | Tranché : un seul au départ | [SPEC.md](../SPEC.md) §8 |
| Quelle touche présenter en démo | La démo | [SPEC.md](../SPEC.md) §4 |

La branche `develop`, où arrivent toutes les pull requests, existe depuis le 12/11/2026 (lot A).

Une fois cette pull request fusionnée, un changement de contrat se fait par une pull request dédiée, relue par les lots concernés : jamais au détour d'une fonctionnalité.

---

## 4. Dépendances entre lots, et comment ne pas les attendre

```mermaid
flowchart LR
    A["A. Socle<br/>auth, matières, paramètres"]
    B["B. Ingestion<br/>chapitres estimés"]
    C["C. Planification<br/>sessions"]
    D["D. Agenda et suivi<br/>progression, mémorisation"]

    A -->|user_id, matières, paramètres| B
    A -->|user_id, paramètres| C
    B -->|chapitres| C
    C -->|sessions| D
```

| Dépendance | Sans attendre |
|---|---|
| Tout le monde attend l'authentification de A | Phase 0 : un `get_current_user` provisoire qui renvoie l'utilisateur de test, remplacé par le vrai sans changer sa signature |
| C attend les chapitres de B | C construit ses `ChapterToPlan` à la main dans ses tests ; le planificateur ne lit jamais un PDF |
| D attend les sessions de C | D génère des sessions avec la fabrique de la phase 0 |
| D attend les échéances de C pour le tableau de bord (3 prochaines échéances) | D lit `GET /deadlines` dès que C l'expose ; en attendant, des échéances créées en base par les fabriques de test |

La règle qui rend cela possible est déjà dans les diagrammes de classes : le domaine est pur et les intégrations sont derrière des interfaces. Chaque lot peut donc tester son code avec des faux, sans les autres.

---

## 5. Les fichiers partagés, premiers lieux de conflits

Quelques fichiers sont touchés par tous les lots. Ce sont eux qui créent les conflits de fusion, pas le code de chaque lot.

| Fichier | Risque | Règle |
|---|---|---|
| `backend/db/migrations/versions/` | Deux migrations créées en parallèle sur la même révision : Alembic se retrouve avec deux « têtes » et refuse de migrer | Une migration par pull request au plus. Avant la fusion, rebase sur `develop` puis `alembic heads` doit afficher une seule tête : la CI le vérifie. A relit toute migration |
| `backend/main.py` (inscription des routers) | Chaque lot y ajoute une ligne au même endroit | Une ligne par router, triée par ordre alphabétique : deux ajouts tombent rarement sur la même ligne |
| `backend/core/container.py` | Chaque lot y branche ses implémentations | Une section commentée par lot |
| `backend/domain/enums.py`, `backend/api/errors.py` | Ajouts concurrents | Ajouts en fin de section du lot, jamais de réorganisation sans prévenir |
| `requirements.txt` | Ajouts concurrents | Versions figées, une par ligne, ordre alphabétique |
| `frontend/api/` | Un seul `api_client.py` serait modifié dans presque chaque pull request | Un fichier par domaine (voir les [conventions](conventions_de_nommage.md) §3) |

Un fichier `.github/CODEOWNERS` désigne le lot responsable de chaque dossier, pour que GitHub demande automatiquement sa relecture.

---

## 6. Relectures croisées

Chaque pull request est relue par un autre membre. Les binômes de relecture suivent les **frontières** entre lots, là où une erreur coûte le plus :

| Le lot | est relu par | Parce que |
|---|---|---|
| B. Ingestion | A | L'upload est la principale surface d'attaque (fichiers piégés, path traversal, injection de prompt) : le lot sécurité la relit |
| C. Planification | B | B connaît les chapitres et leurs durées, que C consomme |
| D. Agenda et suivi | C | D lit les sessions que C produit, et la replanification de C dépend de la progression de D |
| A. Socle | D | D est le plus gros utilisateur des briques transverses (chiffrement, tâches en arrière-plan, suppression de compte) |

Les binômes tournent à chaque phase, pour que chacun ait lu le code de tous les lots à la fin du projet.

---

## 7. Calendrier : les sprints du Jour 2

Le sujet fixe la journée ([SPEC.md](../SPEC.md), cadre). Le lot A est déjà livré : son responsable aide les autres lots.

| Sprint | A (fait) | B | C | D | Fin de sprint |
|---|---|---|---|---|---|
| **9 h 45 · Sprint 1** | Aide C sur les tests du planificateur | `POST /courses` sur les 3 cours Markdown de `sample_data/`, chapitres, heures | Échéances, `PUT /availability`, **planificateur pur + tests** | `PATCH /sessions/{id}`, `.ics` sur des sessions de test, maquette du tableau de bord | Contrat respecté par chaque route du lot ; tests verts |
| **11 h · Sprint 2** | Relectures, CI | PDF avec `pypdf`, page d'import | `POST /plan/generate`, `GET /plan`, page Planning | Export `.ics` branché, tableau de bord branché sur l'API | **Démo de bout en bout** : import → planning → `.ics` → tableau de bord |
| **13 h 45 · Sprint 3** | Touche, README, `AI_LOG.md` | Cas limites de l'import | Cas limites du planificateur, replanification si choisie | Sessions en retard, test d'import du `.ics` dans un vrai agenda | Touche visible en démo |
| **15 h · Gel du code** | Répétition de la démo, à quatre | | | | Chaque membre présente une partie |

### Fin d'une tâche

Une pull request n'est fusionnée que si :

- les tests du lot passent, et les tests du domaine couvrent les cas limites (échéance déjà passée, aucun créneau, chapitre de zéro mot, changement d'heure) ;
- chaque nouvel endpoint qui prend un identifiant a son test d'isolation (`404` pour un autre utilisateur) ;
- les conventions de nommage sont respectées, ou le document est corrigé dans la même pull request ;
- la documentation touchée est à jour : modèle de données si une table change, diagramme de classes si une interface change.

### Avec un assistant de code

Les specs sont écrites pour être données à un assistant de code. Pour que quatre personnes et quatre assistants produisent un code cohérent :

- chaque demande à l'assistant inclut les [conventions de nommage](conventions_de_nommage.md) et les fichiers de contrat de la phase 0 ;
- l'assistant travaille dans le périmètre de fichiers du lot (§2) ; une modification hors périmètre se signale en pull request ;
- le code produit est relu comme un code humain : l'assistant ne connaît pas les décisions prises en séance tant qu'elles ne sont pas écrites dans `docs/`.

---

## 8. Attribution

### Pour le MVP (phases 0 et 1)

Lots tirés au sort le 12/11/2026, sans tenir compte des profils, puis lots A et D échangés entre Aminata Yasmine Savane et Marc Steven Mouthoud le même jour. L'attribution vaut pour le MVP ; elle sera revue avant la phase 2, avec la rotation des binômes de relecture (§6).

| Lot | Responsable | Ce qu'il livre pour le MVP | Relu par |
|---|---|---|---|
| A. Socle et sécurité | Marc Steven Mouthoud | Fait : socle, sécurité, compte, matières, profil, cadre du front | Aminata Yasmine Savane (D) |
| B. Import | Abraham Miguel Tala | Bloc 1 : `POST /courses`, chapitres, heures, page d'import | Marc Steven Mouthoud (A) |
| C. Planification | Houria Debbioui | Blocs 2 et 3 : échéances, disponibilités, planificateur, page Planning | Abraham Miguel Tala (B) |
| D. Agenda et suivi | Aminata Yasmine Savane | Blocs 4 et 5 : sessions faites, export `.ics`, tableau de bord | Houria Debbioui (C) |

Le sujet note aussi l'équipe : **chaque membre doit commiter**, et chacun présente une partie de la démo.

### Profils

Si l'équipe préfère réattribuer selon les affinités, chaque lot demande un profil un peu différent :

| Lot | Profil le plus à l'aise |
|---|---|
| A. Socle et sécurité | Goût pour la configuration, l'authentification et la CI ; accepte de relire beaucoup de code des autres |
| B. Ingestion | Traitement de données et de texte, formats de fichiers, cas limites |
| C. Planification | Algorithmique, gestion des dates et des fuseaux, tests unitaires minutieux |
| D. Agenda et suivi | APIs externes, OAuth, visualisation de données |
