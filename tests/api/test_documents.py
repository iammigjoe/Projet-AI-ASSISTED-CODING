"""
===============================================================================
Tests : POST /courses (import)
===============================================================================
Objectif :
    Vérifier l'import multipart : matière créée, chapitres, heures, conflits,
    types refusés.

Lot :
    B (ingestion)
===============================================================================
"""

from pathlib import Path

import pytest

from backend.core.config import get_settings

COURSES = "/courses"
SAMPLE = Path(__file__).resolve().parents[2] / "sample_data"
FIXTURES = Path(__file__).resolve().parents[1] / "fixtures" / "documents"


@pytest.fixture
def storage_dir(tmp_path, monkeypatch):
    target = tmp_path / "storage"
    target.mkdir()
    monkeypatch.setenv("MYPLAN_STORAGE_DIR", str(target))
    get_settings.cache_clear()
    yield target
    get_settings.cache_clear()


@pytest.fixture
def alice(make_user):
    return make_user("alice-import@exemple.fr")


def test_import_markdown_creates_course_and_chapters(client, alice, auth_headers, storage_dir):
    path = SAMPLE / "machine_learning.md"
    response = client.post(
        COURSES,
        headers=auth_headers(alice.id),
        files={"file": ("machine_learning.md", path.read_bytes(), "text/markdown")},
    )

    assert response.status_code == 201, response.text
    body = response.json()
    assert body["name"] == "Machine Learning"
    assert len(body["chapters"]) == 5
    assert body["chapters"][0]["title"].startswith("Chapter 1")
    assert body["hours_total"] == sum(c["hours"] for c in body["chapters"])
    assert all(c["hours"] >= 1.0 for c in body["chapters"])
    assert list(storage_dir.iterdir())


def test_import_duplicate_name_returns_409(client, alice, auth_headers, storage_dir):
    path = SAMPLE / "statistics.md"
    headers = auth_headers(alice.id)
    files = {"file": ("statistics.md", path.read_bytes(), "text/markdown")}

    first = client.post(COURSES, headers=headers, files=files)
    second = client.post(COURSES, headers=headers, files=files)

    assert first.status_code == 201
    assert second.status_code == 409
    assert second.json()["error"]["code"] == "CONFLICT"


def test_import_fake_pdf_is_rejected(client, alice, auth_headers, storage_dir):
    # fake.pdf ne contient que du texte : un .pdf qui n'est pas un PDF est refusé,
    # au lieu de devenir une matière vide (revue du lot A, 12/11/2026).
    data = (FIXTURES / "fake.pdf").read_bytes()
    response = client.post(
        COURSES,
        headers=auth_headers(alice.id),
        files={"file": ("notes.pdf", data, "application/pdf")},
    )

    assert response.status_code == 422, response.text
    assert response.json()["error"]["code"] == "UNSUPPORTED_FILE_TYPE"
    assert client.get(COURSES, headers=auth_headers(alice.id)).json() == []


def test_import_markdown_without_headings_is_rejected(client, alice, auth_headers, storage_dir):
    response = client.post(
        COURSES,
        headers=auth_headers(alice.id),
        files={"file": ("notes.md", b"Juste du texte, sans aucun titre.\n", "text/markdown")},
    )

    assert response.status_code == 422, response.text
    assert response.json()["error"]["code"] == "EXTRACTION_FAILED"
    assert "titres" in response.json()["error"]["message"]
    assert client.get(COURSES, headers=auth_headers(alice.id)).json() == []
    assert list(storage_dir.glob("*")) == []


@pytest.mark.parametrize("filename", ["cours.txt", "cours", "cours.md.exe"])
def test_import_with_extension_outside_whitelist_is_rejected(
    client, alice, auth_headers, storage_dir, filename
):
    response = client.post(
        COURSES,
        headers=auth_headers(alice.id),
        files={"file": (filename, b"# Cours\n## Chapitre\ntexte\n", "text/plain")},
    )

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "UNSUPPORTED_FILE_TYPE"


def test_import_binary_rejected(client, alice, auth_headers, storage_dir):
    response = client.post(
        COURSES,
        headers=auth_headers(alice.id),
        files={"file": ("virus.bin", b"\x00\x01\x02\x03", "application/octet-stream")},
    )

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "UNSUPPORTED_FILE_TYPE"


def test_import_requires_auth(client, storage_dir):
    path = SAMPLE / "cloud_mlops.md"
    response = client.post(
        COURSES,
        files={"file": ("cloud_mlops.md", path.read_bytes(), "text/markdown")},
    )

    assert response.status_code == 401


def test_import_empty_file_fails(client, alice, auth_headers, storage_dir):
    response = client.post(
        COURSES,
        headers=auth_headers(alice.id),
        files={"file": ("empty.md", b"", "text/markdown")},
    )

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "EXTRACTION_FAILED"
