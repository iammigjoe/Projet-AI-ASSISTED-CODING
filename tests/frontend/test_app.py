"""
===============================================================================
Tests : app (frontend)
===============================================================================
Objectif :
    Faire tourner les pages Streamlit du lot A contre la vraie API de test :
    connexion obligatoire, inscription, matières, paramètres, renouvellement
    du jeton, déconnexion, et affichage sans interprétation des noms saisis.

Lot :
    A (socle et sécurité)
===============================================================================
"""

from pathlib import Path

import httpx
import pytest
import streamlit as st
from sqlalchemy import select
from sqlalchemy.orm import sessionmaker
from streamlit.testing.v1 import AppTest

from backend.db.models import User
from backend.services.course_service import CourseService
from frontend.api.base import ApiClient
from frontend.session import refresh_tokens
from frontend.state import ACCESS_TOKEN, API_CLIENT

APP = Path(__file__).resolve().parents[2] / "frontend" / "app.py"
EMAIL = "etudiant@exemple.fr"
PASSWORD = "une phrase de passe solide"

# =============================================================================
# Fonctions internes
# =============================================================================


@pytest.fixture
def app_test(client):
    """L'application Streamlit, dont le client HTTP parle à l'API de test."""
    at = AppTest.from_file(str(APP), default_timeout=30)

    def relay(request: httpx.Request) -> httpx.Response:
        # Chaque requête du frontend est rejouée sur le TestClient de l'API.
        response = client.request(
            request.method,
            request.url.path,
            params=request.url.params,
            headers=request.headers,
            content=request.content,
        )
        return httpx.Response(
            response.status_code, headers=response.headers, content=response.content
        )

    # Même câblage que get_client(), seul le transport change.
    at.session_state[API_CLIENT] = ApiClient(
        "http://testserver",
        token_getter=lambda: st.session_state.get(ACCESS_TOKEN),
        refresher=refresh_tokens,
        transport=httpx.MockTransport(relay),
    )
    return at.run()


def _register(at: AppTest) -> AppTest:
    at.text_input(key="register_email").input(EMAIL)
    at.text_input(key="register_password").input(PASSWORD)
    at.text_input[4].input(PASSWORD)  # confirmation
    _button(at, "Créer le compte").click()
    return at.run()


def _button(at: AppTest, label: str):
    return next(button for button in at.button if button.label == label)


def _texts(at: AppTest) -> str:
    parts = [element.value for element in (*at.markdown, *at.caption, *at.title, *at.success)]
    parts += [element.label for element in at.expander]
    return "\n".join(str(part) for part in parts)


# =============================================================================
# Connexion
# =============================================================================


def test_without_session_only_login_page_is_shown(app_test):
    assert app_test.title[0].value == "MyPlan"
    assert [tab.label for tab in app_test.tabs] == ["Se connecter", "Créer le compte"]
    assert not app_test.exception


def test_register_logs_in_and_opens_courses(app_test):
    at = _register(app_test)

    assert not at.exception
    assert at.title[0].value == "Matières"
    assert ACCESS_TOKEN in at.session_state


def test_wrong_password_shows_api_message(app_test):
    at = _register(app_test)
    _button(at, "Se déconnecter").click()
    at.run()

    at.text_input[0].input(EMAIL)
    at.text_input[1].input("pas le bon mot de passe")
    _button(at, "Se connecter").click()
    at.run()

    assert at.error[0].value == "Email ou mot de passe incorrect\\."


def test_mismatched_confirmation_is_caught_before_api(app_test):
    app_test.text_input(key="register_email").input(EMAIL)
    app_test.text_input(key="register_password").input(PASSWORD)
    app_test.text_input[4].input("autre chose encore")
    _button(app_test, "Créer le compte").click()
    app_test.run()

    assert app_test.error[0].value == "Les deux mots de passe ne correspondent pas."


def test_logout_returns_to_login_with_message(app_test):
    at = _register(app_test)

    _button(at, "Se déconnecter").click()
    at.run()

    assert at.title[0].value == "MyPlan"
    assert "déconnecté" in at.success[0].value


def test_expired_access_token_is_refreshed_transparently(app_test):
    at = _register(app_test)
    at.session_state[ACCESS_TOKEN] = "jeton-expire"

    at.run()

    assert not at.exception
    assert at.title[0].value == "Matières"
    assert at.session_state[ACCESS_TOKEN] != "jeton-expire"


# =============================================================================
# Matières et paramètres
# =============================================================================


def _add_course(engine, name: str) -> None:
    """Crée une matière pour le compte inscrit, comme le fera l'import (lot B)."""
    session = sessionmaker(bind=engine)()
    user = session.scalar(select(User))
    CourseService(session).create(user.id, name)
    session.close()


def test_courses_page_shows_progress(app_test, engine):
    at = _register(app_test)
    _add_course(engine, "Analyse 2")

    at.run()

    labels = [expander.label for expander in at.expander]
    assert any("Analyse 2" in label and "0 %" in label for label in labels), labels


def test_course_name_with_markup_is_displayed_inert(app_test, engine):
    at = _register(app_test)
    _add_course(engine, "[piège](javascript:alert(1))")

    at.run()

    labels = [expander.label for expander in at.expander]
    assert any(r"\[piège\]\(javascript\:alert\(1\)\)" in label for label in labels), labels


def test_settings_page_saves_changes(app_test):
    at = _register(app_test)
    at.switch_page("views/settings.py").run()

    at.number_input[1].set_value(60)
    _button(at, "Enregistrer").click()
    at.run()

    assert not at.exception
    assert at.success[0].value == "Paramètres enregistrés\\."
    assert at.number_input[1].value == 60


# =============================================================================
# Contournement de la connexion
# =============================================================================


def test_frontend_has_no_pages_directory():
    # Streamlit exécuterait directement les fichiers d'un dossier pages/ (conventions §3).
    assert not (APP.parent / "pages").exists()


def test_page_cannot_be_opened_without_login(app_test):
    # Sans connexion, seule la page de connexion est enregistrée : les autres
    # n'existent pas pour Streamlit, et ne peuvent pas être ouvertes.
    with pytest.raises(ValueError, match="Could not find a navigation page"):
        app_test.switch_page("views/courses.py")

    assert app_test.title[0].value == "MyPlan"


# =============================================================================
# Import de cours (bloc 1)
# =============================================================================

SAMPLE_DATA = APP.parents[1] / "sample_data"
FIXTURES = APP.parents[1] / "tests" / "fixtures" / "documents"


def _upload(at: AppTest, *files: tuple[str, bytes, str]) -> AppTest:
    at.switch_page("views/documents.py").run()
    at.get("file_uploader")[0].set_value(list(files)).run()
    _button(at, "Importer").click()
    return at.run()


def _sample(name: str) -> tuple[str, bytes, str]:
    return (name, (SAMPLE_DATA / name).read_bytes(), "text/markdown")


def test_import_page_creates_course_with_chapters(app_test):
    at = _register(app_test)

    at = _upload(at, _sample("statistics.md"))

    assert not at.exception
    assert "Statistics for Data Science" in at.success[0].value
    assert "4 chapitre" in at.success[0].value
    assert len(at.dataframe[0].value) == 4


def test_import_page_imports_several_files_and_reports_each_failure(app_test):
    at = _register(app_test)
    fake_pdf = ("fake.pdf", (FIXTURES / "fake.pdf").read_bytes(), "application/pdf")

    at = _upload(at, _sample("statistics.md"), fake_pdf, _sample("statistics.md"))

    assert len(at.success) == 1
    assert len(at.error) == 2
    assert all(r"fake\.pdf" in e.value or r"statistics\.md" in e.value for e in at.error)


def test_imported_course_appears_on_courses_page(app_test):
    at = _register(app_test)
    at = _upload(at, _sample("cloud_mlops.md"))

    at.switch_page("views/courses.py").run()

    assert any("Cloud" in expander.label for expander in at.expander)
