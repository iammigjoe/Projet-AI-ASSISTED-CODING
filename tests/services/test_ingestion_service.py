"""
===============================================================================
Tests : IngestionService
===============================================================================
Objectif :
    Vérifier la chaîne upload → parse → chapitres estimés sur les cours Markdown.

Lot :
    B (ingestion)
===============================================================================
"""

from pathlib import Path

from backend.domain.enums import MasteryGoal
from backend.domain.estimation import StudySettings
from backend.integrations.parsers.base import ParserRegistry
from backend.integrations.parsers.markdown_parser import MarkdownParser
from backend.integrations.parsers.pdf_parser import PdfParser
from backend.integrations.storage.local_file_storage import LocalFileStorage
from backend.integrations.storage.upload_validator import UploadValidator
from backend.services.ingestion_service import IngestionService

FIXTURES = Path(__file__).resolve().parents[1] / "fixtures" / "documents"


def _service(tmp_path: Path) -> IngestionService:
    return IngestionService(
        validator=UploadValidator(20_971_520),
        storage=LocalFileStorage(tmp_path),
        parsers=ParserRegistry([MarkdownParser(), PdfParser()]),
    )


def test_ingestion_service_accepts_and_processes_machine_learning(
    tmp_path: Path,
) -> None:
    service = _service(tmp_path)
    data = (FIXTURES / "machine-learning.md").read_bytes()
    settings = StudySettings(200, MasteryGoal.STANDARD)

    accepted = service.accept_upload(data, filename_original="Machine Learning.md")
    result = service.process_stored(
        accepted.storage_key,
        settings=settings,
        difficulty=3,
        file_type=accepted.file_type,
    )

    assert accepted.filename_original == "Machine Learning.md"
    assert accepted.storage_key != "Machine Learning.md"
    assert len(result.chapters) == 5
    assert all(item.estimated_min >= 1 for item in result.chapters)
