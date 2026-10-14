import time
from pathlib import Path

import pytest

from actions.file_controller import DocumentService, DocumentWorker, UnsafePathError


def test_document_service_can_create_and_validate_atomic_text(tmp_path):
    service = DocumentService()
    out, label = service.create_text_artifact(tmp_path, "alpha report", "txt", "alpha body")
    assert out.exists()
    assert out.read_text(encoding="utf-8") == "alpha body"
    assert out.parent == tmp_path
    assert label == "created"


def test_document_service_rejects_invalid_path_and_conflicting_overwrite(tmp_path):
    service = DocumentService()
    with pytest.raises((ValueError, UnsafePathError)):
        service.create_text_artifact(Path("C:/Windows"), "alpha", "txt", "body")

    out, _ = service.create_text_artifact(tmp_path, "alpha", "txt", "body")
    second, _ = service.create_text_artifact(tmp_path, "alpha", "txt", "body-two")
    assert second.name == "alpha_2.txt"


def test_document_service_uses_new_path_for_collision(tmp_path):
    service = DocumentService()
    service.create_text_artifact(tmp_path, "alpha", "txt", "a")
    second, _ = service.create_text_artifact(tmp_path, "alpha", "txt", "b")
    assert second.name == "alpha_2.txt"


def test_document_service_atomic_write_failure_and_output_validation(monkeypatch, tmp_path):
    service = DocumentService()

    def boom(path, extension):
        raise OSError("disk error")

    monkeypatch.setattr(service, "_validate_artifact", boom)
    with pytest.raises(OSError):
        service.create_text_artifact(tmp_path, "bad", "txt", "text")


def test_document_worker_cancellation_marks_task_cancelled(tmp_path):
    service = DocumentService()
    worker = DocumentWorker(service, timeout_seconds=2)
    task = worker.submit("example", lambda task: (task.cancel_event.wait(0.1), task.cancel_event.set(), ""))
    time.sleep(0.05)
    worker.cancel(task.task_id)
    assert task.status == "cancelled"


def test_document_service_fallback_label_selection_for_supported_pairs():
    service = DocumentService()
    assert service._fallback_label(Path("input.docx"), "pdf") == "office/libreoffice-high-fidelity"
    assert service._fallback_label(Path("input.pptx"), "txt") == "pptx-xml-text-fallback"
    assert service._fallback_label(Path("input.pdf"), "txt") == "pdf-text-extraction"
