"""
===============================================================================
Schémas : common
===============================================================================
Objectif :
    Types de champs partagés par les schémas Pydantic de tous les lots, pour
    que chaque texte reçu soit nettoyé et borné de la même façon.

Responsabilités :
    - Normaliser le texte (Unicode NFC), retirer les espaces en bord.
    - Refuser les caractères de contrôle et les caractères invisibles de
      direction (U+202E…), qui servent à déguiser un nom de fichier ou un lien.
    - Borner chaque longueur : aucun texte reçu n'est illimité.
    - Normaliser les emails (minuscules) avant toute comparaison.
    - Vérifier qu'un fuseau horaire existe dans la base IANA.

Notes :
    Ce nettoyage ne remplace pas l'échappement à l'affichage : le texte reste
    une donnée de l'utilisateur, affichée côté Streamlit par les fonctions de
    frontend/security.py (docs/securite.md).

Utilisé par :
    Les schémas de backend/api/schemas/ de tous les lots.

Exemple d'utilisation :
    class CourseCreate(BaseModel):
        name: SingleLineText[100]

Lot :
    A (socle et sécurité)
===============================================================================
"""

import re
import unicodedata
from typing import Annotated
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from pydantic import AfterValidator, Field

# =============================================================================
# Constantes
# =============================================================================

# Caractères de contrôle C0/C1, sauf tabulation et retour à la ligne (texte long).
_CONTROL_CHARS = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f-\x9f]")
# Contrôle de direction et caractères invisibles (« Trojan Source », noms de fichier inversés).
_INVISIBLE_CHARS = re.compile(r"[​-‏‪-‮⁦-⁩﻿]")
_LINE_BREAKS = re.compile(r"[\t\r\n]")
# Volontairement simple : la seule vraie vérification d'un email est un envoi.
_EMAIL = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")

EMAIL_MAX_LENGTH = 254

# =============================================================================
# Fonctions internes
# =============================================================================


def _clean_multiline(value: str) -> str:
    value = unicodedata.normalize("NFC", value).strip()
    if _CONTROL_CHARS.search(value) or _INVISIBLE_CHARS.search(value):
        raise ValueError("Le texte contient des caractères invisibles ou de contrôle.")
    return value.replace("\r\n", "\n")


def _clean_single_line(value: str) -> str:
    value = _clean_multiline(value)
    if _LINE_BREAKS.search(value):
        raise ValueError("Le texte doit tenir sur une seule ligne.")
    return value


def _check_timezone(value: str) -> str:
    value = _clean_single_line(value)
    try:
        ZoneInfo(value)
    except (ZoneInfoNotFoundError, ValueError) as error:
        raise ValueError("Fuseau horaire inconnu (exemple : Europe/Paris).") from error
    return value


def _clean_email(value: str) -> str:
    value = _clean_single_line(value).lower()
    if len(value) > EMAIL_MAX_LENGTH or not _EMAIL.match(value):
        raise ValueError("Adresse email invalide.")
    return value


# =============================================================================
# API publique
# =============================================================================


class SingleLineText:
    """Texte d'une ligne, nettoyé et borné : SingleLineText[100]."""

    def __class_getitem__(cls, max_length: int) -> object:
        return Annotated[
            str, AfterValidator(_clean_single_line), Field(min_length=1, max_length=max_length)
        ]


class MultilineText:
    """Texte de plusieurs lignes, nettoyé et borné : MultilineText[5000]."""

    def __class_getitem__(cls, max_length: int) -> object:
        return Annotated[
            str, AfterValidator(_clean_multiline), Field(min_length=1, max_length=max_length)
        ]


EmailAddress = Annotated[str, AfterValidator(_clean_email)]

# Couleur d'affichage « #RRGGBB », stockée en majuscules.
HexColor = Annotated[
    str, Field(pattern=r"^#[0-9A-Fa-f]{6}$"), AfterValidator(lambda value: value.upper())
]

# Nom IANA (« Europe/Paris »), pas un décalage : un décalage ne suit pas les changements d'heure.
TimezoneName = Annotated[str, Field(max_length=64), AfterValidator(_check_timezone)]

# Mot de passe : jamais nettoyé (un espace en bord compte), seulement borné ; la
# politique complète est dans backend/domain/password_policy.py.
Password = Annotated[str, Field(min_length=1, max_length=128)]
