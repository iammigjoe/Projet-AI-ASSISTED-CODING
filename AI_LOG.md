# AI_LOG — MyPlan (StudyPlan)

Une entrée par échange marquant avec l'IA. Les échecs comptent : on les note tels qu'ils se sont produits, avec la façon dont on les a repérés.

**Comment on vérifie ce que produit l'IA** :
- **Tests** : 202 tests pytest, lancés après chaque modification. Ils couvrent les cas limites, la sécurité et l'isolation entre utilisateurs.
- **Exécution réelle** : migrations appliquées sur une base qui contient déjà des données, application lancée, appels à l'API.
- **Relecture** : chaque fichier généré est relu.
- **Vérification automatique** : `ruff`, `pip-audit` et la CI.

Chaque membre ajoute ses propres entrées pendant le Jour 2.

---

## Entrée 1 : spécification et documents de conception avant le code

- **Quand / qui :** 12/11/2026 — Marc
- **Outil et mode :** Claude Code, conversation
- **Objectif :** partir de nos specs (`myplan-specs.md`) et produire README, conventions, modèle de données, diagrammes de classes et répartition des tâches avant d'écrire une ligne de code.
- **Prompt :**
  > le projet se trouve dans myplan-specs.md et je voudrais un readme qui imite celui que je t'ai montré avec les contributeurs du repo git pris en comptes, nous sommes 4
  >
  > j'ai besoin de fichier comme ça pour ce projet et d'une proposition de séparation de tâche pour optimiser le travail par équipe
- **Résultat :** README, `Spec.md` et quatre documents dans `docs/`, commités avant tout code (commit `e7431bb`).
- **Vérification :** demande explicite de relecture (« reverifie les docs »).
- **Décision :** gardé, après corrections.
- **Échec de l'IA ? Oui.** La relecture a trouvé une vingtaine d'incohérences dans la première version, dont :
  - **Disponibilités en UTC :** stocker « lundi 18 h - 20 h » en UTC aurait décalé tous les créneaux d'une heure à chaque changement d'heure.
  - **Règle d'architecture contredite :** les diagrammes de l'IA contredisaient la règle « chaque couche ne parle qu'à celle du dessous ».
  - **Valeur périmée en base :** la rétention était stockée alors qu'elle dépend de l'heure de lecture.
  - **Planning qui se gêne lui-même :** l'agenda lu pour éviter les conflits était celui où l'on exporte les sessions.

  Leçon : faire relire par l'IA ce qu'elle vient d'écrire, en lui demandant de chercher les contradictions entre documents.

## Entrée 2 : l'IA a commencé à coder au lieu de préparer l'arborescence

- **Quand / qui :** 12/11/2026 — Marc
- **Outil et mode :** Claude Code
- **Objectif :** créer l'arborescence du projet.
- **Prompt :**
  > Crées l'architecture de documents du projet
- **Résultat :** 141 fichiers Python créés, chacun avec un en-tête rempli d'avance.
- **Vérification :** relecture du résultat par l'équipe.
- **Décision :** rejeté.
  > ne commence pas le développement efface les fichiers
- **Échec de l'IA ? Oui.** Le prompt était ambigu (« architecture de documents »), et l'IA a choisi l'interprétation la plus large au lieu de demander. Les en-têtes remplis d'avance auraient aussi décrit du code qui n'existait pas. Leçon : préciser le livrable attendu, et ne pas accepter des fichiers « à compléter ».

## Entrée 3 : dossier `pages/` de Streamlit, contournement de la connexion

- **Quand / qui :** 12/11/2026 — Marc
- **Outil et mode :** Claude Code, puis tests `streamlit.testing.v1.AppTest`
- **Objectif :** pages Streamlit du lot A (connexion, matières, paramètres).
- **Résultat :** l'IA avait placé les pages dans `frontend/pages/`, le dossier qu'elle avait elle-même fixé dans nos conventions.
- **Vérification :** un test de bout en bout (inscription puis affichage des matières) restait bloqué sur la page de connexion. En cherchant pourquoi, on a trouvé la cause : Streamlit exécute directement tout fichier d'un dossier `pages/` voisin du point d'entrée, **sans passer par `app.py` ni par la vérification de connexion**.
- **Décision :** modifié. Le dossier est renommé `frontend/views/`, et deux tests empêchent le retour en arrière : aucun dossier `pages/`, et aucune page accessible sans connexion. La règle est ajoutée aux conventions, à SPEC.md et aux consignes des assistants.
- **Échec de l'IA ? Oui.** La faille était dans l'interface seulement : l'API restait protégée par les jetons. Leçon : un test qui échoue « bizarrement » peut cacher un vrai défaut, à creuser plutôt qu'à contourner.

## Entrée 4 : migration `--autogenerate` fausse

- **Quand / qui :** 12/11/2026 — Marc
- **Outil et mode :** Alembic `--autogenerate`, puis Claude Code
- **Objectif :** aligner le schéma sur le contrat du sujet (`weight`, `date`, `session_minutes`, semaine ISO).
- **Prompt :**
  > Faut-il réaligner l'API sur le contrat officiel de StudyPlan ? → Oui, contrat exact
- **Résultat :** une migration générée automatiquement.
- **Vérification :** migration appliquée sur une base **qui contient déjà un compte et ses paramètres**, comme la base locale d'un membre de l'équipe.
- **Décision :** rejetée puis réécrite à la main : reprise des données existantes, nouvelles contraintes, retrait des anciennes. Testée dans les deux sens (montée et descente) ; `alembic check` ne trouve aucun écart avec les modèles.
- **Échec de l'IA ? Oui.** Trois défauts dans la migration générée :
  - **Plantage sur une base non vide :** colonnes `NOT NULL` ajoutées sans valeur pour les lignes existantes.
  - **Règles absentes :** nouvelles contraintes CHECK oubliées (`weight` de 0 à 100, format de la semaine).
  - **Contraintes orphelines :** anciennes contraintes CHECK laissées sur des colonnes supprimées.

  Leçon, ajoutée à `CLAUDE.md` : relire et tester sur une base non vide toute migration générée.

## Entrée 5 : protection de la taille des requêtes contournée par un détail d'implémentation

- **Quand / qui :** 12/11/2026 — Marc
- **Outil et mode :** Claude Code
- **Objectif :** refuser en `413` toute requête trop lourde, y compris envoyée en flux sans taille annoncée.
- **Prompt :**
  > renforce la sécurité (passage en force brute, faille xss, etc.
- **Résultat :** un middleware qui compte les octets reçus et lève une exception au-delà de la limite.
- **Vérification :** un test envoie un corps en flux, plus gros que la limite, sans `Content-Length`.
- **Décision :** modifié (`except*` au lieu de `except`).
- **Échec de l'IA ? Oui.** Le test répondait `500` au lieu de `413`. Le middleware de limitation du débit lit le corps dans un groupe de tâches, qui enveloppe l'exception dans un `ExceptionGroup` : le `except` de l'IA ne la rattrapait pas. Sans ce test, la protection n'aurait marché que pour les clients honnêtes.

## Entrée 6 : le sujet officiel arrive après nos specs

- **Quand / qui :** 12/11/2026 — Marc
- **Outil et mode :** Claude Code
- **Objectif :** utiliser les données de démo.
- **Prompt :**
  > les data d'essaie sont censées se trouver ici "C:\Users\marcs\Documents\ai-assisted\ai-coding-kit\project"
- **Résultat :** en lisant le dossier, l'IA a trouvé le sujet officiel (brief, grille, spécification, contrat d'API) et l'a comparé à notre projet.
- **Vérification :** comparaison ligne à ligne avec la grille de notation.
- **Décision :** réalignement complet, après deux décisions de l'équipe : contrat exact, connexion conservée.
- **Échec de l'IA ? Oui, de méthode.** Pendant toute la conception, l'IA a travaillé à partir de nos specs, sans demander s'il existait un sujet imposé. Résultat :
  - **Bibliothèque interdite :** `anthropic` figurait dans `requirements.txt`, alors que le sujet interdit toute bibliothèque d'IA.
  - **Contrat non respecté :** routes sous `/api/v1`, `POST /courses` en JSON au lieu d'un fichier.
  - **Mauvais export :** synchronisation Google au lieu de l'export `.ics`.

  Leçon : commencer par le sujet et la grille, puis seulement écrire la spec.

## Entrée 7 : chaîne Windows abîmée par un script de l'IA

- **Quand / qui :** 12/11/2026 — Marc
- **Outil et mode :** Claude Code, script Python de remplacement de texte
- **Objectif :** ajouter la commande d'activation de l'environnement (`.venv\Scripts\activate`) au README.
- **Résultat :** dans le fichier, `\a` était devenu un caractère de contrôle invisible (BEL) : la commande affichée était fausse.
- **Vérification :** contrôle des octets du fichier (`od -c`) après une sortie suspecte.
- **Décision :** corrigé avant le push.
- **Échec de l'IA ? Oui.** Petit, mais typique : une commande copiée par un nouvel arrivant aurait échoué sans message clair.

## Entrée 8 : faux positifs de l'analyse de sécurité

- **Quand / qui :** 12/11/2026 — Marc
- **Outil et mode :** ruff (règles de sécurité `S`), Claude Code
- **Objectif :** garder la CI propre avec les règles de sécurité de `ruff` activées.
- **Résultat :** `ruff` signalait comme « mot de passe en dur » des noms de clés de session (`"access_token"`), un code d'erreur (`"WEAK_PASSWORD"`) et le type de jeton (`"bearer"`).
- **Vérification :** relecture de chaque alerte.
- **Décision :** gardé avec un `# noqa: S105` justifié en commentaire, ligne par ligne. La règle n'est pas désactivée globalement, pour qu'un vrai secret en dur soit toujours signalé.
- **Échec de l'IA ? Non**, mais un bon exemple de sortie d'outil à ne pas accepter ni rejeter en bloc.
