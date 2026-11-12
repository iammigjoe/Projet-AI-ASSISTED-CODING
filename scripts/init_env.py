"""
===============================================================================
Script : init_env
===============================================================================
Objectif :
    Créer le fichier .env à partir de .env.example, avec des clés secrètes
    générées, pour lancer le projet en une commande.

Responsabilités :
    - Ne jamais écraser un .env existant : il contient peut-être les clés qui
      ont chiffré des données.
    - Générer une clé JWT aléatoire de 64 caractères et une clé Fernet valide.

Exemple d'utilisation :
    python scripts/init_env.py

Lot :
    A (socle et sécurité)
===============================================================================
"""

import secrets
import sys
from pathlib import Path

from cryptography.fernet import Fernet

# =============================================================================
# Constantes
# =============================================================================

ROOT = Path(__file__).resolve().parents[1]
EXAMPLE = ROOT / ".env.example"
TARGET = ROOT / ".env"

# =============================================================================
# API publique
# =============================================================================


def build_env(example: str) -> str:
    """Remplit les clés secrètes vides d'un contenu de .env.example.

    Args:
        example: Contenu de .env.example.

    Returns:
        Le même contenu, avec MYPLAN_JWT_SECRET_KEY et MYPLAN_FERNET_KEY remplies.
    """
    generated = {
        "MYPLAN_JWT_SECRET_KEY": secrets.token_hex(32),
        "MYPLAN_FERNET_KEY": Fernet.generate_key().decode(),
    }
    lines = []
    for line in example.splitlines():
        name, separator, value = line.partition("=")
        if separator and name in generated and not value:
            line = f"{name}={generated[name]}"
        lines.append(line)
    return "\n".join(lines) + "\n"


def main() -> int:
    """Crée .env s'il n'existe pas ; renvoie le code de sortie du script."""
    if TARGET.exists():
        print(".env existe déjà : rien n'est modifié.")
        return 0
    TARGET.write_text(build_env(EXAMPLE.read_text(encoding="utf-8")), encoding="utf-8")
    print(".env créé avec des clés secrètes générées.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
