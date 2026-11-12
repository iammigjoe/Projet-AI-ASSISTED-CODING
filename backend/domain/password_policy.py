"""
===============================================================================
Domaine : password_policy
===============================================================================
Objectif :
    Décider si un mot de passe est acceptable, et dire pourquoi s'il ne l'est pas.

Responsabilités :
    - Longueur d'au moins 12 caractères : c'est la longueur, pas la variété des
      caractères, qui résiste à la force brute (recommandation ANSSI / NIST).
    - Longueur d'au plus 128 caractères : argon2 hache tout ce qu'on lui donne,
      un mot de passe de plusieurs mégaoctets bloquerait le serveur.
    - Refuser les mots de passe les plus courants, ceux qui répètent un seul
      caractère, et ceux qui contiennent l'identifiant de l'email.

Pur :
    Ni base, ni réseau, ni horloge.

Utilisé par :
    AuthService (inscription, changement de mot de passe).

Exemple d'utilisation :
    problems = password_problems("motdepasse", email="alice@exemple.fr")
    if problems:
        raise WeakPasswordError(" ".join(problems))

Lot :
    A (socle et sécurité)
===============================================================================
"""

import unicodedata

# =============================================================================
# Constantes
# =============================================================================

MIN_LENGTH = 12
MAX_LENGTH = 128

# Mots de passe parmi les plus utilisés (listes publiques de fuites), à l'identique
# ou comme base complétée de chiffres. Liste courte volontairement : la longueur
# minimale écarte déjà la plupart des autres.
COMMON_PASSWORDS = frozenset(
    {
        "123456789012",
        "1234567890ab",
        "azertyuiop12",
        "azertyuiopqs",
        "motdepasse12",
        "motdepasse123",
        "password1234",
        "password12345",
        "passwordpassword",
        "qwertyuiop12",
        "qwertyuiopas",
        "iloveyou1234",
        "admin1234567",
        "bonjour12345",
        "soleil123456",
        "doudou123456",
        "loulou123456",
        "marseille1234",
        "football1234",
        "welcome12345",
    }
)

# =============================================================================
# API publique
# =============================================================================


def password_problems(password: str, email: str | None = None) -> list[str]:
    """Liste les raisons pour lesquelles un mot de passe est refusé.

    Args:
        password: Mot de passe proposé, tel que saisi.
        email: Email du compte ; sa partie avant « @ » ne doit pas figurer
            dans le mot de passe.

    Returns:
        Les problèmes, en français, affichables tels quels ; liste vide si le
        mot de passe est acceptable.
    """
    normalized = unicodedata.normalize("NFC", password)
    problems: list[str] = []

    if len(normalized) < MIN_LENGTH:
        problems.append(f"Le mot de passe doit faire au moins {MIN_LENGTH} caractères.")
    if len(normalized) > MAX_LENGTH:
        problems.append(f"Le mot de passe doit faire au plus {MAX_LENGTH} caractères.")
    if normalized and len(set(normalized)) == 1:
        problems.append("Le mot de passe ne doit pas répéter un seul caractère.")
    if normalized.casefold() in COMMON_PASSWORDS:
        problems.append("Ce mot de passe fait partie des plus utilisés : choisissez-en un autre.")

    local_part = (email or "").split("@")[0].casefold()
    if len(local_part) >= 4 and local_part in normalized.casefold():
        problems.append("Le mot de passe ne doit pas contenir votre identifiant.")

    return problems
