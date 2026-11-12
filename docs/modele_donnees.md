# Modèle de données : approche Merise

Décrit les données de MyPlan, du dictionnaire jusqu'au schéma physique SQLite. Le point de départ est le tableau des tables des specs (§5) ; ce document le précise colonne par colonne, et corrige ce qui ne tiendrait pas une fois codé. **Rien n'est encore implémenté** : chaque choix est une décision de conception, à vérifier contre les modèles SQLAlchemy dès qu'ils existent. Les écarts avec les specs sont signalés à leur emplacement ; les questions encore ouvertes sont regroupées en §6.

Conventions de nommage appliquées : [conventions_de_nommage.md](conventions_de_nommage.md) §4.

> **Réaligné sur le sujet StudyPlan le 12/11/2026** (migration `20261112_1311_align_studyplan_contract`) :
>
> | Changement | Pourquoi |
> |---|---|
> | Échéances : `weight` 0-100 remplace `importance`, `due_date` (date) remplace `due_at`, type `assignment` remplace `project` | Contrat d'API du sujet |
> | `deadline_chapters` supprimée : une échéance porte sur toute sa matière | Contrat ; tranche aussi §6.6 |
> | `availability_exceptions` supprimée, `valid_from` / `valid_to` retirés | Le contrat ne prévoit que des créneaux hebdomadaires |
> | `user_settings.session_minutes` (60) remplace `max_session_min` (90) ; pause à 0 par défaut | Contrat : `PUT /availability {session_minutes}` |
> | `plans.week` : un planning par semaine ISO | Contrat : `POST /plan/generate {week}` |
> | `study_sessions.google_event_id` supprimé ; `google_credentials`, `summaries`, `notifications`, `memory_states` non créées | Export `.ics` au lieu de Google ; aucune IA dans le produit ; touches optionnelles |
>
> Les sections ci-dessous décrivent l'état actuel. Les tables jamais créées restent décrites en fin de §1, marquées comme telles.

---

## 1. Dictionnaire de données

Types SQLite : `INTEGER`, `REAL`, `TEXT`, `BLOB`. Un booléen est un `INTEGER` à 0 ou 1. Une date ou une heure est un `TEXT` au format ISO 8601 (voir §5). Toutes les tables d'entité portent aussi `created_at` et `updated_at` (instants UTC), non répétés ci-dessous.

### UTILISATEUR (`users`)

| Propriété | Type | Contraintes | Remarque |
|---|---|---|---|
| `id` | INTEGER | PK | |
| `email` | TEXT | NOT NULL, UNIQUE | Stocké en minuscules : `Alice@x.fr` et `alice@x.fr` sont le même compte |
| `password_hash` | TEXT | NOT NULL | argon2, jamais le mot de passe |
| `timezone` | TEXT | NOT NULL, défaut `Europe/Paris` | Nom IANA, pas un décalage (`+01:00`) : un décalage ne suit pas les changements d'heure |
| `token_version` | INTEGER | NOT NULL, défaut `0`, ≥ 0 | Inscrite dans chaque jeton ; l'incrémenter révoque tous les jetons émis (déconnexion, mot de passe changé, [securite.md](securite.md)) |
| `deleted_at` | TEXT | NULL | Suppression demandée : le compte est bloqué tout de suite, ses lignes sont supprimées ensuite (RG15) |

### PARAMÈTRES (`user_settings`)

| Propriété | Type | Contraintes | Remarque |
|---|---|---|---|
| `user_id` | INTEGER | PK, FK → `users` | Relation (1,1) : la clé primaire est la clé étrangère |
| `reading_speed_wpm` | INTEGER | NOT NULL, défaut `200`, > 0 | Mots par minute |
| `session_minutes` | INTEGER | NOT NULL, défaut `60`, entre 15 et 240 | Durée de chaque session du planning (contrat : `PUT /availability`) |
| `break_min` | INTEGER | NOT NULL, défaut `0`, ≥ 0 | Pause entre deux sessions ; 0 pour remplir un créneau de 2 h avec deux sessions d'une heure (données de démo) |
| `mastery_goal` | TEXT | NOT NULL, défaut `standard` | `discovery` / `standard` / `mastery` : donne le coefficient d'objectif (P0-07) |
| `retention_threshold` | REAL | NOT NULL, défaut `0.70`, entre 0 et 1 | Seuil de déclenchement d'une révision (P2-06) |
| `notif_prefs` | TEXT | NOT NULL, défaut `{}` | JSON : canal, délai avant session, activé ou non (P2-07) |

> Écart avec les specs : `mastery_goal` et `retention_threshold` n'y figurent pas, mais P0-07 et P0-08 citent un « niveau de maîtrise souhaité » et P2-06 un seuil de 70 %. Sans colonne, ces valeurs seraient écrites en dur.

### MATIÈRE (`courses`)

| Propriété | Type | Contraintes | Remarque |
|---|---|---|---|
| `id` | INTEGER | PK | |
| `user_id` | INTEGER | NOT NULL, FK → `users` | Seul lien de propriété : tout ce qui descend d'une matière appartient à son utilisateur |
| `name` | TEXT | NOT NULL, 1 à 100 caractères | |
| `color` | TEXT | NOT NULL | `#RRGGBB`, vérifié par `CHECK` |
| `difficulty` | INTEGER | NOT NULL, défaut `3`, entre 1 et 5 | Difficulté perçue : donne le coefficient de difficulté |

Unicité de `(user_id, name)` : deux matières du même nom chez un même étudiant rendraient le dashboard illisible.

### DOCUMENT (`documents`)

| Propriété | Type | Contraintes | Remarque |
|---|---|---|---|
| `id` | INTEGER | PK | |
| `course_id` | INTEGER | NOT NULL, FK → `courses` | |
| `filename_original` | TEXT | NOT NULL | Affiché à l'étudiant, **jamais** utilisé pour écrire sur le disque |
| `storage_key` | TEXT | NOT NULL, UNIQUE | UUID v4 + extension. Remplace `storage_path` des specs : voir §5 |
| `type` | TEXT | NOT NULL | `pdf` / `markdown`, déduit des *magic bytes*, pas de l'extension |
| `size_bytes` | INTEGER | NOT NULL | |
| `sha256` | TEXT | NOT NULL | Empreinte du fichier : repère un même cours envoyé deux fois |
| `status` | TEXT | NOT NULL, défaut `pending` | `pending` / `processing` / `ready` / `failed` (P1-06) |
| `error_code` | TEXT | NULL | Renseigné si `failed` : `EMPTY_TEXT`, `SCANNED_PDF`, `TIMEOUT`… |
| `uploaded_at` | TEXT | NOT NULL | |

> Écart avec les specs : `error_code` est indispensable à P0-04 (« erreur claire si le PDF est vide ou scanné ») et P1-06 (statut `échec`). Sans lui, `failed` ne dit pas quoi faire.

### CHAPITRE (`chapters`)

| Propriété | Type | Contraintes | Remarque |
|---|---|---|---|
| `id` | INTEGER | PK | |
| `document_id` | INTEGER | NOT NULL, FK → `documents` | |
| `title` | TEXT | NOT NULL | Modifiable par l'étudiant (P0-06) |
| `position` | INTEGER | NOT NULL, ≥ 0 | Ordre dans le document |
| `word_count` | INTEGER | NOT NULL, ≥ 0 | |
| `page_start` / `page_end` | INTEGER | NULL | PDF uniquement ; sert à scinder et à retrouver le passage à résumer |
| `estimated_min` | INTEGER | NOT NULL | Calculé par la formule de P0-07 |
| `estimated_min_override` | INTEGER | NULL, > 0 | Valeur saisie à la main ; prioritaire si renseignée |
| `is_validated` | INTEGER | NOT NULL, défaut `0` | Booléen : l'étudiant a relu le découpage (P0-06) |

Unicité de `(document_id, position)`.

La durée utilisée par le planificateur est `COALESCE(estimated_min_override, estimated_min)`. Les deux sont gardées : si la vitesse de lecture change, `estimated_min` est recalculé sans écraser la correction de l'étudiant.

### DISPONIBILITÉ (`availabilities`)

| Propriété | Type | Contraintes | Remarque |
|---|---|---|---|
| `id` | INTEGER | PK | |
| `user_id` | INTEGER | NOT NULL, FK → `users` | |
| `weekday` | INTEGER | NOT NULL, entre 0 (lundi) et 6 | Convention de `datetime.weekday()` ; `monday` à `sunday` dans le contrat |
| `starts_local` | TEXT | NOT NULL | `HH:MM`, **heure locale** de l'étudiant |
| `ends_local` | TEXT | NOT NULL | `HH:MM`, > `starts_local` |

`PUT /availability` remplace tous les créneaux de l'utilisateur en une transaction.

> Écart avec la première version : `start` / `end` deviennent `starts_local` / `ends_local`. Le suffixe dit que ce n'est **pas** de l'UTC, contrairement à tous les autres horaires (§5).

### ÉCHÉANCE (`deadlines`)

| Propriété | Type | Contraintes | Remarque |
|---|---|---|---|
| `id` | INTEGER | PK | |
| `user_id` | INTEGER | NOT NULL, FK → `users` | |
| `course_id` | INTEGER | NOT NULL, FK → `courses` | Doit appartenir au même utilisateur (RG4) |
| `title` | TEXT | NOT NULL | « Midterm exam », « Docker lab submission » |
| `type` | TEXT | NOT NULL | `exam` / `assignment` (contrat) |
| `due_date` | TEXT | NOT NULL | Date locale `AAAA-MM-JJ` ; `date` dans le contrat ; jamais dans le passé à la création (422) |
| `weight` | INTEGER | NOT NULL, entre 0 et 100 | Avec la proximité de la date, donne la priorité d'une matière dans le planning |

### PLANNING (`plans`)

| Propriété | Type | Contraintes | Remarque |
|---|---|---|---|
| `id` | INTEGER | PK | |
| `user_id` | INTEGER | NOT NULL, FK → `users` | |
| `week` | TEXT | NOT NULL, format `AAAA-Www` | Semaine ISO couverte (contrat : `POST /plan/generate {week}`) |
| `version` | INTEGER | NOT NULL, ≥ 1 | Unique par utilisateur |
| `status` | TEXT | NOT NULL, défaut `draft` | `draft` / `active` / `archived` |
| `origin` | TEXT | NOT NULL | `generated` / `replanned` : distingue P0-11 de P2-01 dans l'historique (P1-08) |
| `parent_plan_id` | INTEGER | NULL, FK → `plans` | Version dont celle-ci découle |
| `activated_at` | TEXT | NULL | |

### SESSION D'ÉTUDE (`study_sessions`)

| Propriété | Type | Contraintes | Remarque |
|---|---|---|---|
| `id` | INTEGER | PK | |
| `plan_id` | INTEGER | NOT NULL, FK → `plans` | |
| `chapter_id` | INTEGER | NOT NULL, FK → `chapters` | |
| `kind` | TEXT | NOT NULL, défaut `study` | `study` / `review` : une révision espacée (P2-06) est une session comme une autre |
| `starts_at` / `ends_at` | TEXT | NOT NULL | Instants UTC, `ends_at` > `starts_at` |
| `status` | TEXT | NOT NULL, défaut `planned` | `planned` / `done` / `missed` |
| `self_rating` | INTEGER | NULL, entre 1 et 5 | Seulement si `done` (P2-05) |
| `completed_at` | TEXT | NULL | Instant où l'étudiant l'a marquée faite |

> Écart avec la première version : `start` / `end` deviennent `starts_at` / `ends_at` (`END` est réservé en SQL) ; `kind` et `completed_at` sont ajoutés. `done` dans le contrat correspond à `status = 'done'`.

### ÉTAT DE MÉMORISATION (`memory_states`) : non créée

| Propriété | Type | Contraintes | Remarque |
|---|---|---|---|
| `chapter_id` | INTEGER | PK, FK → `chapters` | (1,1) avec le chapitre, créé à la première session faite |
| `stability_days` | REAL | NOT NULL, > 0 | Paramètre `S` |
| `last_review_at` | TEXT | NOT NULL | Instant UTC |
| `review_count` | INTEGER | NOT NULL, défaut `0` | |

> Écart avec les specs : `retention_estimate` est **retiré**. `R = e^(−t/S)` dépend de `t`, le temps écoulé depuis la dernière révision : la valeur stockée serait fausse une minute après avoir été écrite. `R` se calcule à la lecture, à partir de `stability_days` et `last_review_at`. La table est aussi passée au pluriel, comme les autres.

### IDENTIFIANTS GOOGLE (`google_credentials`) : non créée

| Propriété | Type | Contraintes | Remarque |
|---|---|---|---|
| `user_id` | INTEGER | PK, FK → `users` | |
| `encrypted_refresh_token` | BLOB | NOT NULL | Chiffré par Fernet, clé dans `MYPLAN_FERNET_KEY` |
| `scope` | TEXT | NOT NULL | Scopes réellement accordés, à comparer aux scopes demandés |
| `calendar_id` | TEXT | NOT NULL, défaut `primary` | Agenda cible de l'export |
| `revoked_at` | TEXT | NULL | |

### NOTIFICATION (`notifications`) : non créée

| Propriété | Type | Contraintes | Remarque |
|---|---|---|---|
| `id` | INTEGER | PK | |
| `user_id` | INTEGER | NOT NULL, FK → `users` | |
| `study_session_id` | INTEGER | NULL, FK → `study_sessions` | NULL pour une notification qui ne vise pas une session |
| `type` | TEXT | NOT NULL | `reminder` / `summary` |
| `channel` | TEXT | NOT NULL | `email` (MVP de la notification) |
| `scheduled_at` | TEXT | NOT NULL | |
| `sent_at` | TEXT | NULL | NULL = pas encore envoyée |
| `attempts` | INTEGER | NOT NULL, défaut `0` | Évite de renvoyer en boucle une notification qui échoue |

> Écart avec les specs : `session_id` devient `study_session_id`, pour suivre la règle des clés étrangères (`<entité>_id`) et lever l'ambiguïté avec les autres « sessions » (voir le glossaire des [conventions](conventions_de_nommage.md)). `channel` et `attempts` sont ajoutés.

### RÉSUMÉ (`summaries`) : non créée

| Propriété | Type | Contraintes | Remarque |
|---|---|---|---|
| `chapter_id` | INTEGER | PK, FK → `chapters` | |
| `part_index` | INTEGER | PK, ≥ 0 | |
| `content` | TEXT | NOT NULL | Sortie du LLM, validée avant stockage |
| `source_sha256` | TEXT | NOT NULL | Empreinte du texte résumé : si le chapitre est scindé ou fusionné, le résumé est périmé |
| `model` | TEXT | NOT NULL | Modèle qui l'a produit |
| `generated_at` | TEXT | NOT NULL | Tient lieu de `created_at` |

Un résumé ne se modifie jamais : périmé, il est remplacé (RG14). La table n'a donc ni `created_at` ni `updated_at`, seulement `generated_at`.

---

## 2. Règles de gestion

| # | Règle |
|---|---|
| **RG1** | Un utilisateur possède 0 à N matières ; une matière appartient à exactement 1 utilisateur. |
| **RG2** | Une matière contient 0 à N documents ; un document appartient à exactement 1 matière. |
| **RG3** | Un document contient 0 à N chapitres (0 tant que l'extraction n'est pas finie ou si elle a échoué) ; un chapitre appartient à exactement 1 document. |
| **RG4** | Une échéance concerne exactement 1 matière **du même utilisateur**, et donc tous ses chapitres. Sa date n'est jamais dans le passé à la création. |
| **RG5** | La durée d'un chapitre est `estimated_min_override` s'il est renseigné, `estimated_min` sinon. |
| **RG6** | Un utilisateur a 0 ou 1 planning `active` **par semaine**. Générer le planning d'une semaine archive le planning actif précédent de cette semaine, dans la même transaction. |
| **RG7** | Une session appartient à exactement 1 planning et porte sur exactement 1 chapitre. Elle dure `session_minutes`, tient entièrement dans un créneau de disponibilité ; deux sessions d'un même planning ne se chevauchent pas et sont séparées d'au moins `break_min`. |
| **RG8** | Une session `study` d'une matière se termine avant le début (minuit, heure locale) du jour de sa **plus proche** échéance. Les matières aux échéances les plus proches et les plus lourdes passent en premier. Si le temps manque, le manque est signalé (P0-11). |
| **RG9** | Seule une session `done` peut porter une `self_rating`. Une session passée et non marquée reste `planned` : `missed` est un choix de l'étudiant ou de la replanification, jamais un effet du temps qui passe. |
| **RG10** | L'export `.ics` contient un `VEVENT` par session, avec un identifiant stable (`UID`) dérivé de l'identifiant de la session : réimporter le fichier met à jour les événements au lieu de les doubler. |
| **RG11** | Une replanification ne touche que les sessions futures et `planned`. Les sessions `done` et `missed` d'un planning restent telles quelles, même archivé. |
| **RG12** | L'avancement d'un chapitre est la somme des durées de ses sessions `done`, **tous plannings confondus**. |
| **RG13** | *(Touche optionnelle, table non créée.)* L'état de mémorisation d'un chapitre est créé à sa première session `done`, puis mis à jour à chaque session `done` avec auto-évaluation. |
| ~~**RG14**~~ | ~~Résumés par LLM~~ : abandonné, le produit n'appelle aucune IA. |
| **RG15** | Supprimer un compte supprime toutes ses données (RGPD), fichiers envoyés compris. |

RG12 a une conséquence de conception : comme chaque nouvelle version de planning recrée ses sessions, l'avancement ne peut pas se lire dans le planning actif seul, sinon générer une nouvelle version remettrait l'avancement à zéro.

---

## 3. Modèle Conceptuel de Données (MCD)

Notation Merise, cardinalités (min,max) de chaque côté de l'association.

```text
UTILISATEUR (1,1) ──── RÈGLE ────── (1,1) PARAMÈTRES

UTILISATEUR (0,N) ──── POSSÈDE ──── (1,1) MATIÈRE
MATIÈRE     (0,N) ──── CONTIENT ─── (1,1) DOCUMENT
DOCUMENT    (0,N) ──── DÉCOUPE ──── (1,1) CHAPITRE

UTILISATEUR (0,N) ──── DÉCLARE ──── (1,1) DISPONIBILITÉ

UTILISATEUR (0,N) ──── FIXE ─────── (1,1) ÉCHÉANCE
MATIÈRE     (0,N) ──── ÉVALUE ───── (1,1) ÉCHÉANCE

UTILISATEUR (0,N) ──── GÉNÈRE ───── (1,1) PLANNING
PLANNING    (0,1) ──── DÉRIVE ───── (0,N) PLANNING        (version parente)
PLANNING    (0,N) ──── PRÉVOIT ──── (1,1) SESSION
CHAPITRE    (0,N) ──── ÉTUDIÉ ───── (1,1) SESSION


```

Aucune association N-N depuis l'alignement sur le sujet : une échéance porte sur sa matière entière, et `CONCERNE` (table `deadline_chapters`) a disparu.

`ÉCHÉANCE` dépend deux fois de l'utilisateur : directement (`FIXE`) et par la matière (`ÉVALUE`). La redondance est voulue : elle permet de filtrer les échéances par `user_id` sans jointure, comme toutes les tables que l'étudiant gère directement. RG4 impose que les deux chemins mènent au même utilisateur. La base ne sait pas le vérifier seule : le service charge la matière et les chapitres **par le repository, avec le `user_id` courant**, avant d'écrire l'échéance. Une matière ou un chapitre d'un autre utilisateur n'est alors pas trouvé, et la requête échoue en `404`.

---

## 4. Modèle Logique de Données (MLD)

`#` = clé primaire, `→` = clé étrangère.

```text
users (#id, email, password_hash, timezone, token_version, deleted_at, created_at, updated_at)

user_settings (#user_id→users, reading_speed_wpm, session_minutes, break_min,
               mastery_goal, retention_threshold, notif_prefs, created_at, updated_at)

courses (#id, user_id→users, name, color, difficulty, created_at, updated_at)

documents (#id, course_id→courses, filename_original, storage_key, type, size_bytes,
           sha256, status, error_code, uploaded_at, created_at, updated_at)

chapters (#id, document_id→documents, title, position, word_count, page_start, page_end,
          estimated_min, estimated_min_override, is_validated, created_at, updated_at)

availabilities (#id, user_id→users, weekday, starts_local, ends_local, created_at, updated_at)

deadlines (#id, user_id→users, course_id→courses, title, type, due_date, weight,
           created_at, updated_at)

plans (#id, user_id→users, week, version, status, origin, parent_plan_id→plans,
       activated_at, created_at, updated_at)

study_sessions (#id, plan_id→plans, chapter_id→chapters, kind, starts_at, ends_at,
                status, self_rating, completed_at, created_at, updated_at)
```

---

## 5. Modèle physique : décisions et justifications

### Instants en UTC, horaires récurrents en heure locale

Les specs (P1-04) demandent des heures stockées en UTC. C'est juste pour un **instant** : une session, une échéance, un envoi de notification. C'est faux pour une **disponibilité récurrente**.

« Lundi 18 h - 20 h » est une heure de l'étudiant, pas un instant. Stocké en UTC (17 h - 19 h en hiver), le créneau deviendrait 19 h - 21 h à l'heure de Paris après le passage à l'heure d'été, fin mars : toutes les disponibilités se décaleraient d'une heure sans que personne ne les ait modifiées.

| Donnée | Stockage | Colonnes |
|---|---|---|
| Instant | UTC, `AAAA-MM-JJTHH:MM:SSZ` | tout ce qui finit par `_at` |
| Heure récurrente | locale, `HH:MM` | `starts_local`, `ends_local` |
| Date | locale, `AAAA-MM-JJ` | `due_date` |

La conversion se fait à un seul endroit : la fonction du domaine qui calcule les créneaux libres d'une période, avec le fuseau de `users.timezone` (`zoneinfo`). Elle doit être testée sur les deux semaines de changement d'heure, et sur la nuit où 2 h - 3 h existe deux fois.

### Instants stockés en texte, avec un type qui refuse les heures naïves

SQLite n'a pas de type date. Le `DateTime` de SQLAlchemy y écrit un texte **sans fuseau** et relit une `datetime` naïve : un instant écrit en heure de Paris serait relu comme s'il était en UTC, sans erreur.

Un `TypeDecorator` (`UtcDateTime`, dans `backend/db/types.py`) est utilisé pour toutes les colonnes `_at` :

- à l'écriture, il refuse une `datetime` naïve et convertit en UTC ;
- à la lecture, il rend une `datetime` avec `tzinfo=UTC`.

Le format ISO 8601 en UTC a une autre propriété utile : l'ordre alphabétique est l'ordre chronologique. `ORDER BY starts_at` et `WHERE starts_at > ?` restent justes sur du texte.

### Clés étrangères activées à chaque connexion

SQLite **ignore** les clés étrangères par défaut, `ON DELETE CASCADE` compris. Sans réglage, supprimer une matière laisserait ses documents, ses chapitres et ses sessions orphelins, en silence, et l'export RGPD comme la suppression de compte (P1-07) seraient faux.

Un écouteur `connect` de SQLAlchemy exécute à chaque connexion :

```sql
PRAGMA foreign_keys = ON;
PRAGMA journal_mode = WAL;
PRAGMA busy_timeout = 5000;
```

`WAL` laisse les lectures continuer pendant une écriture (le planificateur en arrière-plan écrit pendant que Streamlit lit) ; `busy_timeout` fait attendre une écriture concurrente au lieu d'échouer aussitôt. Un test vérifie que `PRAGMA foreign_keys` vaut `1` sur une connexion de l'application.

### Suppressions en cascade

| Suppression de | Emporte | Mécanisme |
|---|---|---|
| `users` | tout ce qui lui appartient | `ON DELETE CASCADE` sur chaque `user_id` (RG15) |
| `courses` | documents, chapitres, échéances | `ON DELETE CASCADE` |
| `documents` | chapitres, fichier sur le disque | `ON DELETE CASCADE` ; le fichier est supprimé par le service, après la transaction |
| `chapters` | sessions, état de mémorisation, résumés, liens aux échéances | `ON DELETE CASCADE` ; à restreindre une fois le chapitre étudié (§6.5) |
| `plans` | sessions | `ON DELETE CASCADE` ; un planning n'est supprimé qu'avec son utilisateur, sinon il est archivé |
| `study_sessions` | rien : `notifications.study_session_id` passe à NULL | `ON DELETE SET NULL` |

La base ne sait pas supprimer un fichier sur le disque : ce nettoyage est fait par les services, et c'est pourquoi aucune suppression ne passe par une requête SQL écrite à la main.

### Pas de `user_id` sur les documents ni les chapitres

La propriété d'un document se lit par sa matière, celle d'un chapitre par son document. Ajouter `user_id` partout simplifierait les requêtes, mais créerait une deuxième source de vérité qui pourrait diverger de la première (un document rattaché à la matière d'un utilisateur, avec le `user_id` d'un autre).

Les repositories font donc la jointure jusqu'à `courses.user_id`. Elle est écrite une fois, dans une fonction commune, et testée.

Les échéances, elles, ont un `user_id` : voir le MCD (§3) et RG4.

### Un seul planning actif par utilisateur et par semaine, garanti par la base

RG6 est tenue par un index unique partiel, que SQLite accepte :

```sql
CREATE UNIQUE INDEX uq_plans_user_id_week_active
    ON plans (user_id, week) WHERE status = 'active';
```

Le service archive l'ancien planning et active le nouveau dans la même transaction ; si deux requêtes tentent d'activer deux plannings en même temps, la seconde échoue au lieu de laisser deux plannings actifs.

### Énumérations en texte vérifié

Chaque colonne à ensemble fini (`status`, `type`, `kind`…) est un `TEXT` avec une contrainte `CHECK (status IN ('planned', 'done', 'missed'))`. La liste vient de l'énumération Python (`SessionStatus`) : un seul endroit à modifier.

### Durées en minutes entières

`estimated_min`, `session_minutes`, `break_min` : `INTEGER`. L'API exprime la charge en heures (`hours`, contrat) ; la conversion se fait à la sortie. Le planificateur travaille en minutes ; un `REAL` ferait apparaître des sessions de 47,999 minutes.

`stability_days` est le seul `REAL` : la stabilité de la courbe d'oubli est un paramètre continu.

### Le fichier est désigné par une clé, pas par un chemin

Les specs prévoient `storage_path`. Un chemin complet en base lie les données à l'emplacement du dossier sur une machine donnée, et un chemin modifié en base pourrait pointer hors du dossier de stockage.

`storage_key` ne contient que `UUID.ext`. Le chemin est reconstruit par `LocalFileStorage` (`MYPLAN_STORAGE_DIR / storage_key`), qui vérifie que le résultat reste dans le dossier.

---

## 6. Questions ouvertes

### 6.1 Que devient `google_event_id` quand le planning change de version ? : sans objet

> **Sans objet depuis l'alignement sur le sujet** : l'export `.ics` remplace la synchronisation Google ; un `UID` stable par session évite les doublons à la réimportation (RG10). Texte d'origine conservé ci-dessous.

Chaque version de planning recrée ses sessions. Si le `google_event_id` reste sur l'ancienne session, le nouvel export ne le voit pas et crée un doublon : exactement ce que P1-02 interdit.

Deux options :

| Option | Principe | Coût |
|---|---|---|
| A. Reprise de l'identifiant | À l'activation, chaque nouvelle session reprend le `google_event_id` de l'ancienne qui porte sur le même chapitre ; le sync met à jour l'événement. Les événements non repris sont supprimés | Il faut définir quand deux sessions « se correspondent » |
| B. Table de synchronisation | Une table `calendar_events (user_id, google_event_id, study_session_id)` que le sync compare au planning actif | Une table de plus, mais la règle est plus simple : tout ce qui n'est pas dans le planning actif est supprimé |

**Proposition : B.** Elle sépare l'état de Google de l'état du planning, et reste valable si d'autres calendriers arrivent (P3). À trancher avant de coder P1-02.

### 6.2 Les sessions passées et non marquées

RG9 laisse une session passée en `planned` tant que l'étudiant n'a rien dit. Le dashboard affiche donc « en retard » ce qui est `planned` et fini. À confirmer : faut-il au contraire passer automatiquement en `missed` après un délai (24 h) ? Le choix change le calcul de retard de P2-01.

### 6.3 La découpe d'un chapitre en parties pour les résumés : sans objet

> **Sans objet** : les résumés par LLM sont abandonnés (le produit n'appelle aucune IA).

`summaries.part_index` suppose qu'un chapitre est découpé en parties, mais rien ne dit comment (par page, par nombre de mots, par sous-titre). La règle doit être fixée avant P2-03, et stockée si elle peut changer.

### 6.4 MyPlan ne doit pas se voir lui-même comme « occupé » : sans objet

> **Sans objet** : MyPlan ne lit plus d'agenda externe ; les créneaux libres viennent seulement de `PUT /availability`.

P1-05 lit l'agenda pour éviter les créneaux occupés ; P1-01 écrit les sessions dans l'agenda. Si les deux visent le même agenda (`calendar_id = primary`), la génération suivante lira les sessions exportées comme des créneaux occupés : le planning se repousserait lui-même, et pourrait se déclarer infaisable.

| Option | Principe |
|---|---|
| A. Agenda dédié | L'export écrit dans un agenda « MyPlan » créé pour l'occasion ; la lecture des créneaux occupés l'ignore. L'étudiant peut aussi masquer ou supprimer cet agenda d'un coup |
| B. Marquage des événements | Chaque événement exporté porte une propriété privée (`extendedProperties.private.myplan_session`) ; la lecture écarte les événements marqués |

**Proposition : A.** La règle tient en une ligne, et elle ne dépend pas d'une propriété qu'un autre outil pourrait effacer. À trancher avec la question 6.1, avant P1-01. Dans les deux cas, le contrat de `BusyTimeReader` l'impose ([diagramme_classes.md](diagramme_classes.md) §4).

### 6.5 Modifier un chapitre déjà étudié

P0-06 permet de fusionner, scinder et supprimer des chapitres « avant de planifier ». Rien n'empêche de le faire **après**. Or supprimer un chapitre emporte, par cascade, ses sessions faites, son état de mémorisation et ses résumés : l'avancement (RG12) recule sans que l'étudiant ait rien désappris.

Proposition : un chapitre qui a au moins une session `done` ne peut plus être fusionné, scindé ni supprimé ; seuls son titre et sa durée restent modifiables. Le supprimer reste possible en supprimant le document entier, avec une confirmation qui dit ce qui sera perdu.

### 6.6 Échéances sans chapitres, chapitres sans échéance : tranché

> **Tranché par le contrat du sujet** : une échéance porte sur toute sa matière. Reste à préciser par le lot C : une matière sans échéance est planifiée après les autres.

RG4 impose au moins un chapitre par échéance. Mais un étudiant connaît souvent la date de l'examen avant d'avoir envoyé ses cours, et un chapitre peut n'être lié à aucune échéance.

À trancher :

- une échéance sans chapitre porte-t-elle sur **tous** les chapitres de sa matière (ce qui permettrait de passer RG4 à « 0 à N ») ?
- un chapitre sans échéance est-il planifié après tous les autres, ou pas du tout ?

Le planificateur (lot C de la [répartition](repartition_taches.md)) ne peut pas être écrit sans ces deux réponses.

### 6.7 Un compte, ou plusieurs ? ✅ Tranché le 12/11/2026

**Un seul compte au départ.** Le modèle ne change pas :

| Élément | Décision | Pourquoi |
|---|---|---|
| Table `users` et colonnes `user_id` | Conservées | Elles ne coûtent presque rien, et évitent une migration de toutes les tables le jour où un deuxième compte arrive |
| Filtre par `user_id` dans les repositories | Conservé | Même raison ; c'est aussi ce qui rend les requêtes justes quand le deuxième compte arrivera |
| Tests d'isolation entre utilisateurs | Conservés | Ils fabriquent deux utilisateurs en base de test, ce que l'inscription fermée n'empêche pas ; sans eux, l'ouverture à plusieurs comptes ne serait pas vérifiée |
| Inscription | Ouverte tant que `users` est vide, fermée ensuite (`403`, code `REGISTRATION_CLOSED`) | Le premier lancement crée le compte ; personne d'autre ne peut en créer un |
| Connexion | Obligatoire | L'API est joignable sur le réseau : sans connexion, n'importe qui sur le réseau lirait les cours, le planning et les échéances |

Ouvrir plusieurs comptes plus tard consistera à rouvrir l'inscription : aucune table ni requête ne change.
