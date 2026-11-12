"""
===============================================================================
Tests : UploadValidator et LocalFileStorage
===============================================================================
Objectif :
    Vérifier magic bytes, taille max, UUID, et refus du path traversal.

Lot :
    B (ingestion)
===============================================================================
"""

from pathlib import Path

import pytest

from backend.domain.enums import DocumentType
from backend.domain.errors import FileTooLargeError, UnsupportedFileTypeError
from backend.integrations.storage.local_file_storage import LocalFileStorage
from backend.integrations.storage.upload_validator import UploadValidator

FIXTURES = Path(__file__).resolve().parents[1] / "fixtures" / "documents"


def test_validator_accepts_markdown_utf8() -> None:
    data = (FIXTURES / "statistics.md").read_bytes()
    document_type = UploadValidator(20_971_520).validate(data[:4096], len(data))

    assert document_type is DocumentType.MARKDOWN


def test_validator_accepts_pdf_magic() -> None:
    data = b"%PDF-1.4 minimal"
    assert UploadValidator(1024).validate(data, len(data)) is DocumentType.PDF


def test_validator_rejects_binary_with_null_bytes() -> None:
    with pytest.raises(UnsupportedFileTypeError):
        UploadValidator(1024).validate(b"\x00\x01\x02binary", 6)


def test_fake_pdf_fixture_is_not_pdf_magic() -> None:
    data = (FIXTURES / "fake.pdf").read_bytes()

    assert not data.startswith(b"%PDF")
    assert UploadValidator(1024).validate(data, len(data)) is DocumentType.MARKDOWN


def test_validator_rejects_too_large() -> None:
    with pytest.raises(FileTooLargeError):
        UploadValidator(10).validate(b"%PDF-1.4", 100)


def test_local_storage_uses_uuid_not_original_name(tmp_path: Path) -> None:
    storage = LocalFileStorage(tmp_path)
    data = b"# Hello\n"

    key = storage.save(data, DocumentType.MARKDOWN)

    assert key.endswith(".md")
    assert "Hello" not in key
    assert (tmp_path / key).read_bytes() == data
    assert storage.open(key).is_file()


def test_local_storage_rejects_path_traversal(tmp_path: Path) -> None:
    storage = LocalFileStorage(tmp_path)

    with pytest.raises(ValueError):
        storage.open("../outside.md")
