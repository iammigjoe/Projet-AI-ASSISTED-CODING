"""
===============================================================================
Module : login_throttle
===============================================================================
Objectif :
    Freiner les attaques par force brute sur la connexion : après quelques
    échecs, chaque nouvel essai doit attendre de plus en plus longtemps.

Responsabilités :
    - Compter les échecs par clé : l'email visé, et l'adresse IP d'origine.
    - Laisser FREE_ATTEMPTS essais libres, puis imposer une attente qui double
      à chaque échec (30 s, 1 min, 2 min…), plafonnée à MAX_DELAY.
    - Ne jamais bloquer un compte définitivement : un blocage définitif
      permettrait à n'importe qui de verrouiller le compte de l'étudiant.
    - Oublier une clé après une connexion réussie, ou après RESET_AFTER sans échec.

Utilisé par :
    AuthService (connexion), via la dépendance get_login_throttle.

Exemple d'utilisation :
    keys = (f"email:{email}", f"ip:{client_ip}")
    if (wait := throttle.retry_after(keys, now)) > 0:
        raise TooManyAttemptsError(wait)
    ...
    throttle.record_failure(keys, now)  # ou throttle.record_success(keys)

Notes :
    - État en mémoire du processus : suffisant pour le serveur unique du MVP
      (Spec §6), remis à zéro au redémarrage. Plusieurs processus demanderaient
      un stockage partagé (Redis).

Lot :
    A (socle et sécurité)
===============================================================================
"""

import math
import threading
from collections.abc import Iterable
from dataclasses import dataclass
from datetime import datetime, timedelta

# =============================================================================
# Constantes
# =============================================================================

FREE_ATTEMPTS = 5
BASE_DELAY = timedelta(seconds=30)
MAX_DELAY = timedelta(minutes=15)
RESET_AFTER = timedelta(hours=1)
# Au-delà, les clés les plus anciennes sont oubliées : la mémoire reste bornée
# même si un attaquant varie les emails ou les adresses.
MAX_TRACKED_KEYS = 10_000

# =============================================================================
# Types
# =============================================================================


@dataclass
class _Record:
    failures: int
    last_failure_at: datetime


# =============================================================================
# API publique
# =============================================================================


class LoginThrottle:
    """Compteur d'échecs de connexion avec attente exponentielle, sûr entre threads."""

    def __init__(self) -> None:
        self._records: dict[str, _Record] = {}
        self._lock = threading.Lock()

    def retry_after(self, keys: Iterable[str], now: datetime) -> int:
        """Renvoie le nombre de secondes à attendre avant un nouvel essai.

        Args:
            keys: Clés concernées par l'essai (email, adresse IP).
            now: Instant de l'essai.

        Returns:
            0 si l'essai est permis, sinon l'attente la plus longue parmi les clés.
        """
        with self._lock:
            waits = [self._wait(self._records.get(key), now) for key in keys]
        return max(waits, default=0)

    def record_failure(self, keys: Iterable[str], now: datetime) -> None:
        """Enregistre un échec de connexion pour chaque clé."""
        with self._lock:
            for key in keys:
                record = self._records.get(key)
                if record is None or now - record.last_failure_at > RESET_AFTER:
                    record = _Record(failures=0, last_failure_at=now)
                record.failures += 1
                record.last_failure_at = now
                self._records[key] = record
            self._forget_oldest()

    def record_success(self, keys: Iterable[str]) -> None:
        """Oublie les échecs des clés après une connexion réussie."""
        with self._lock:
            for key in keys:
                self._records.pop(key, None)

    def reset(self) -> None:
        """Oublie tout ; réservé aux tests."""
        with self._lock:
            self._records.clear()

    # --- Fonctions internes -------------------------------------------------

    @staticmethod
    def _wait(record: _Record | None, now: datetime) -> int:
        if record is None or record.failures < FREE_ATTEMPTS:
            return 0
        if now - record.last_failure_at > RESET_AFTER:
            return 0
        exponent = record.failures - FREE_ATTEMPTS
        delay = min(BASE_DELAY * (2**exponent), MAX_DELAY)
        remaining = (record.last_failure_at + delay - now).total_seconds()
        return max(0, math.ceil(remaining))

    def _forget_oldest(self) -> None:
        overflow = len(self._records) - MAX_TRACKED_KEYS
        if overflow <= 0:
            return
        oldest = sorted(self._records, key=lambda key: self._records[key].last_failure_at)
        for key in oldest[:overflow]:
            del self._records[key]


_login_throttle = LoginThrottle()


def get_login_throttle() -> LoginThrottle:
    """Dépendance FastAPI : le compteur unique du processus."""
    return _login_throttle
