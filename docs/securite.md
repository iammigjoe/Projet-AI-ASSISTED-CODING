# Sécurité

Ce que le socle (lot A) met en place contre les attaques courantes, et ce que **chaque lot doit faire** pour en profiter. La section sécurité des [specs](../SPEC.md) (§4) dit quoi protéger ; ce document dit où c'est fait dans le code, et comment s'en servir.

Une protection fournie par le socle ne protège rien si une route ou une page la contourne. Les règles de la §3 sont vérifiées en revue, et deux d'entre elles par des tests automatiques.

---

## 1. Ce qui est en place

| Menace | Protection | Où | Vérifié par |
|---|---|---|---|
| **Force brute sur la connexion** | Limite par adresse IP sur la route de connexion (10/min) ; attente exponentielle après 5 échecs, par email et par IP (30 s, 1 min, 2 min… jusqu'à 15 min) ; jamais de blocage définitif, qui permettrait à n'importe qui de verrouiller le compte | `backend/api/rate_limit.py`, `backend/core/login_throttle.py` | `test_protections.py`, `test_login_throttle.py` |
| **Énumération des comptes** | Même message et même durée de réponse, que l'email existe ou non (`verify_login_password` vérifie un hachage factice) | `backend/core/security.py` | `test_security.py` |
| **Mots de passe faibles** | 12 à 128 caractères, refus des plus courants, d'un seul caractère répété, de l'identifiant de l'email | `backend/domain/password_policy.py` | `test_password_policy.py` |
| **Vol de mot de passe en base** | argon2, sel aléatoire, jamais de comparaison en clair | `backend/core/security.py` | `test_security.py` |
| **Jeton volé ou falsifié** | JWT d'accès de 15 min, signature HS256 uniquement (« none » refusé), type d'accès et de rafraîchissement non interchangeables ; `token_version` du compte : l'incrémenter révoque tous les jetons émis | `backend/core/security.py`, `backend/api/deps.py` | `test_security.py`, `test_deps.py` |
| **Accès aux données d'un autre** (IDOR) | `user_id` tiré du jeton uniquement ; `user_id` en premier argument de chaque méthode de repository ; `404` pour une ressource d'un autre | `backend/api/deps.py`, conventions §2 | test d'isolation par endpoint (à écrire par chaque lot) |
| **XSS stocké** (titre de chapitre, nom de matière) | À l'entrée : texte normalisé, borné, sans caractères de contrôle ni caractères invisibles de direction. À l'affichage : échappement Markdown dans Streamlit ; HTML brut interdit dans `frontend/` | `backend/api/schemas/common.py`, `frontend/security.py` | `test_schemas_common.py`, `test_security.py` (frontend), `test_no_raw_html.py` |
| **Réponse de l'API interprétée comme une page** | `Content-Security-Policy: default-src 'none'`, `X-Content-Type-Options: nosniff`, `X-Frame-Options: DENY` | `backend/api/middleware.py` | `test_protections.py` |
| **Interception** | HSTS en production (HTTPS imposé au navigateur pendant un an) | `backend/api/middleware.py` | `test_protections.py` |
| **En-tête Host forgé** (liens empoisonnés, DNS rebinding) | Seuls les noms de `MYPLAN_ALLOWED_HOSTS` sont servis, sinon `400` | `backend/api/middleware.py` | `test_protections.py` |
| **Saturation du serveur** | Limite globale de 120 requêtes/min par IP ; corps de requête limité à la taille d'un upload (Content-Length **et** octets réellement reçus) | `backend/api/rate_limit.py`, `backend/api/middleware.py` | `test_protections.py` |
| **Fuite d'informations par les erreurs** | Jamais de trace, de SQL ni de valeur saisie dans une réponse ; documentation `/docs` masquée en production | `backend/api/errors.py`, `backend/main.py` | `test_errors.py`, `test_protections.py` |
| **Requête d'un autre site** (CSRF) | Jeton dans l'en-tête `Authorization`, jamais dans un cookie : un autre site ne peut pas l'envoyer à la place de l'étudiant ; CORS limité à `MYPLAN_CORS_ORIGINS` | `backend/main.py` | — |
| **Secrets** | Refus de démarrer sans clé JWT de 32 caractères et clé Fernet valide ; secrets dans `.env`, jamais commité ; aucun service externe, donc aucune clé tierce à protéger | `backend/core/config.py` | `test_config.py` |

---

## 2. Limites connues

| Limite | Conséquence | Quand la lever |
|---|---|---|
| Compteurs de limitation et d'échecs **en mémoire** | Remis à zéro au redémarrage ; ne marchent que sur un seul processus | Si l'API tourne sur plusieurs processus : stockage partagé (Redis) |
| Adresse IP vue **directement** | Derrière un reverse proxy, toutes les requêtes semblent venir du proxy et partagent la même limite | Au déploiement : `uvicorn --proxy-headers --forwarded-allow-ips=<IP du proxy>` |
| Jeton de rafraîchissement **réutilisable** jusqu'à son expiration (7 jours) | Un jeton de rafraîchissement volé reste utilisable tant que l'étudiant ne se déconnecte pas ; la déconnexion le révoque | Rotation stricte (jeton à usage unique), qui demande de stocker les jetons émis |
| Pas de **double authentification** | Un mot de passe volé suffit | P3, si l'application devient multi-comptes |
| Pas de **détection de mots de passe fuités** (Have I Been Pwned) | Seule une courte liste de mots de passe courants est refusée | Appel réseau à ajouter derrière une interface, si l'équipe le juge utile |

---

## 3. Règles pour chaque lot

### Toutes les routes

1. L'utilisateur vient de `CurrentUser`, jamais du corps ni des paramètres.
2. Chaque texte reçu utilise un type de `backend/api/schemas/common.py` : `SingleLineText[n]`, `MultilineText[n]`, `EmailAddress`. Pas de `str` nu sans longueur maximale.
3. Chaque endpoint qui prend un identifiant a son **test d'isolation** : l'utilisateur B demande la ressource de l'utilisateur A et reçoit `404`.

### Connexion et inscription (lot A)

En place dans `backend/api/routers/auth.py` et `backend/services/auth_service.py`. La route de connexion combine les trois protections, dans cet ordre :

```python
@router.post("/auth/login")
@limiter.limit(LOGIN_LIMIT)                              # 1. débit par IP
def login(request: Request, payload: LoginRequest, ...):
    keys = (f"email:{payload.email}", f"ip:{client_ip}")
    if wait := throttle.retry_after(keys, now):          # 2. attente après échecs
        raise ApiError(429, ErrorCode.TOO_MANY_LOGIN_ATTEMPTS, ..., headers={"Retry-After": str(wait)})
    user = users.get_by_email(payload.email)
    if not verify_login_password(payload.password, user.password_hash if user else None):  # 3. temps constant
        throttle.record_failure(keys, now)
        raise ApiError(401, ErrorCode.INVALID_CREDENTIALS, "Email ou mot de passe incorrect.")
    throttle.record_success(keys)
```

Le message d'échec est **le même** que l'email existe ou non. Déconnexion et changement de mot de passe incrémentent `users.token_version`.

### Envoi de fichiers (lot B)

`@limiter.limit(UPLOAD_LIMIT)` sur la route d'upload. La limite de taille globale ne dispense pas `UploadValidator` de vérifier la taille réelle et les *magic bytes*.

### Pages Streamlit (tous les lots)

Les pages se créent dans `frontend/views/`. Un dossier `frontend/pages/` serait exécuté par Streamlit **sans la vérification de connexion** de `frontend/app.py` : il est interdit, et un test le vérifie.

| Afficher | Avec |
|---|---|
| Un texte saisi ou extrait d'un cours, dans `st.markdown`, `st.write`, un titre, un libellé, une infobulle | `escape_markdown(texte)` |
| Un texte brut, sans mise en forme | `st.text`, `st.code` : rien à échapper |
| Un tableau | `st.dataframe` : rien à échapper |
| Du HTML | **Jamais.** `unsafe_allow_html=True`, `st.html` et `components.html` font échouer `test_no_raw_html.py` |

Le texte d'un PDF vient d'un inconnu : un titre de chapitre peut contenir `[cliquez ici](javascript:...)` ou une image qui signale à un tiers que le cours a été ouvert.

### Fichiers importés (lot B)

Le texte d'un PDF ou d'un Markdown vient d'un inconnu. Il n'est jamais exécuté ni interprété : il sert à compter des mots et à repérer des titres. Les titres de chapitres sont stockés tels quels, nettoyés par les types de `schemas/common.py`, et échappés à l'affichage.

Le produit n'appelle **aucune IA** (sujet StudyPlan) : il n'y a donc pas d'injection de prompt possible côté produit.
