"""
===============================================================================
Tests : no_raw_html
===============================================================================
Objectif :
    Interdire dans frontend/ tout moyen d'injecter du HTML ou du JavaScript
    brut dans la page (Spec §4, docs/securite.md). Un échec ici n'est pas à
    contourner : il faut afficher le contenu autrement.

Lot :
    A (socle et sécurité)
===============================================================================
"""

import re
from pathlib import Path

import pytest

FRONTEND = Path(__file__).resolve().parents[2] / "frontend"

FORBIDDEN = {
    "unsafe_allow_html=True": re.compile(r"unsafe_allow_html\s*=\s*True"),
    "st.html(": re.compile(r"\bst\.html\s*\("),
    "components.html(": re.compile(r"\bcomponents(?:\.v1)?\.html\s*\("),
    "components.iframe(": re.compile(r"\bcomponents(?:\.v1)?\.iframe\s*\("),
}


def _python_files() -> list[Path]:
    return sorted(FRONTEND.rglob("*.py"))


def test_frontend_has_python_files_to_scan():
    assert _python_files(), "Aucun fichier à analyser : le chemin du frontend a changé ?"


@pytest.mark.parametrize("pattern_name", FORBIDDEN)
def test_frontend_never_renders_raw_html(pattern_name):
    pattern = FORBIDDEN[pattern_name]
    offenders = [
        f"{path.relative_to(FRONTEND.parent)}:{number}"
        for path in _python_files()
        for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1)
        if pattern.search(line) and not line.lstrip().startswith("#")
    ]

    assert offenders == [], f"{pattern_name} est interdit dans frontend/ : {offenders}"
