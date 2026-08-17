import shutil

import pytest
from sqlalchemy.orm import Session

from backend.db import create_db_engine, create_session_factory
from backend.db_models import Base, Transaction
from backend.models import DateSource, OperationType, PdfFileMetadata, PlanSkeleton, PlanStep, SortOrder
from backend.orchestrator import PlanApplicationError, apply_plan


@pytest.fixture
def session() -> Session:
    engine = create_db_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    factory = create_session_factory(engine)
    with factory() as db_session:
        yield db_session


def _plan(steps: list[PlanStep]) -> PlanSkeleton:
    return PlanSkeleton(steps=steps, dateSource=DateSource.CREATED_AT, sortOrder=SortOrder.ASCENDING)


def _write_pdf(root, filename: str) -> None:
    (root / filename).write_bytes(b"%PDF-1.4 fake")


def test_apply_plan_moves_files_into_target_folder_and_records_completed_operations(session, tmp_path):
    _write_pdf(tmp_path, "a.pdf")
    _write_pdf(tmp_path, "b.pdf")
    pdf_files = [
        PdfFileMetadata(filename="a.pdf", createdAt="2026-08-01"),
        PdfFileMetadata(filename="b.pdf", createdAt="2026-08-02"),
    ]
    plan = _plan([PlanStep(order=0, operationType=OperationType.MOVE, targetFolder="2026-08", affectedFileCount=2)])

    transaction = apply_plan(session, plan, pdf_files, tmp_path)

    assert not (tmp_path / "a.pdf").exists()
    assert not (tmp_path / "b.pdf").exists()
    assert (tmp_path / "2026-08" / "a.pdf").exists()
    assert (tmp_path / "2026-08" / "b.pdf").exists()
    assert transaction.status == "committed"
    assert len(transaction.operations) == 2
    assert all(op.status == "completed" for op in transaction.operations)


def test_apply_plan_splits_pdf_files_across_multiple_steps_in_order(session, tmp_path):
    _write_pdf(tmp_path, "a.pdf")
    _write_pdf(tmp_path, "b.pdf")
    pdf_files = [
        PdfFileMetadata(filename="a.pdf", createdAt="2026-08-01"),
        PdfFileMetadata(filename="b.pdf", createdAt="2026-09-01"),
    ]
    plan = _plan(
        [
            PlanStep(order=0, operationType=OperationType.MOVE, targetFolder="2026-08", affectedFileCount=1),
            PlanStep(order=1, operationType=OperationType.MOVE, targetFolder="2026-09", affectedFileCount=1),
        ]
    )

    apply_plan(session, plan, pdf_files, tmp_path)

    assert (tmp_path / "2026-08" / "a.pdf").exists()
    assert (tmp_path / "2026-09" / "b.pdf").exists()


def test_apply_plan_rejects_whole_plan_without_moving_anything_when_file_count_mismatches(session, tmp_path):
    _write_pdf(tmp_path, "a.pdf")
    pdf_files = [PdfFileMetadata(filename="a.pdf", createdAt="2026-08-01")]
    plan = _plan([PlanStep(order=0, operationType=OperationType.MOVE, targetFolder="2026-08", affectedFileCount=2)])

    with pytest.raises(PlanApplicationError):
        apply_plan(session, plan, pdf_files, tmp_path)

    assert (tmp_path / "a.pdf").exists()
    assert not (tmp_path / "2026-08").exists()


def test_apply_plan_rejects_whole_plan_when_a_source_file_escapes_the_whitelist(session, tmp_path):
    pdf_files = [PdfFileMetadata(filename="..", createdAt="2026-08-01")]
    plan = _plan([PlanStep(order=0, operationType=OperationType.MOVE, targetFolder="2026-08", affectedFileCount=1)])

    with pytest.raises(Exception):
        apply_plan(session, plan, pdf_files, tmp_path)

    assert not (tmp_path / "2026-08").exists()


def test_apply_plan_rejects_non_move_operation_types_without_touching_files(session, tmp_path):
    _write_pdf(tmp_path, "a.pdf")
    pdf_files = [PdfFileMetadata(filename="a.pdf", createdAt="2026-08-01")]
    plan = _plan([PlanStep(order=0, operationType=OperationType.DELETE, targetFolder="2026-08", affectedFileCount=1)])

    with pytest.raises(PlanApplicationError):
        apply_plan(session, plan, pdf_files, tmp_path)

    assert (tmp_path / "a.pdf").exists()
    assert not (tmp_path / "2026-08").exists()


def test_apply_plan_rolls_back_completed_moves_when_a_later_move_fails(session, tmp_path, monkeypatch):
    _write_pdf(tmp_path, "a.pdf")
    _write_pdf(tmp_path, "b.pdf")
    pdf_files = [
        PdfFileMetadata(filename="a.pdf", createdAt="2026-08-01"),
        PdfFileMetadata(filename="b.pdf", createdAt="2026-08-02"),
    ]
    plan = _plan([PlanStep(order=0, operationType=OperationType.MOVE, targetFolder="2026-08", affectedFileCount=2)])

    real_move = shutil.move
    call_count = {"n": 0}

    def flaky_move(src, dst):
        call_count["n"] += 1
        if call_count["n"] == 2:
            raise OSError("simulated disk failure")
        return real_move(src, dst)

    monkeypatch.setattr("backend.orchestrator.shutil.move", flaky_move)

    with pytest.raises(PlanApplicationError):
        apply_plan(session, plan, pdf_files, tmp_path)

    # a.pdf taşındı, sonra rollback ile eski konumuna geri döndü.
    assert (tmp_path / "a.pdf").exists()
    assert not (tmp_path / "2026-08" / "a.pdf").exists()
    # b.pdf'in taşınması hiç başarılı olmadı, zaten yerinde kalmalı.
    assert (tmp_path / "b.pdf").exists()


def test_apply_plan_rolls_back_completed_moves_in_reverse_order(session, tmp_path, monkeypatch):
    _write_pdf(tmp_path, "a.pdf")
    _write_pdf(tmp_path, "b.pdf")
    _write_pdf(tmp_path, "c.pdf")
    pdf_files = [
        PdfFileMetadata(filename="a.pdf", createdAt="2026-08-01"),
        PdfFileMetadata(filename="b.pdf", createdAt="2026-08-02"),
        PdfFileMetadata(filename="c.pdf", createdAt="2026-08-03"),
    ]
    plan = _plan([PlanStep(order=0, operationType=OperationType.MOVE, targetFolder="2026-08", affectedFileCount=3)])

    real_move = shutil.move
    move_order: list[str] = []

    def tracking_move(src, dst):
        move_order.append(f"{src}->{dst}")
        if len(move_order) == 3:  # c.pdf'in ileri taşınması başarısız olsun
            raise OSError("simulated disk failure")
        return real_move(src, dst)

    monkeypatch.setattr("backend.orchestrator.shutil.move", tracking_move)

    with pytest.raises(PlanApplicationError):
        apply_plan(session, plan, pdf_files, tmp_path)

    # Rollback hareketleri, ileri taşımaların TERS sırasıyla gerçekleşmeli:
    # önce (son tamamlanan) b.pdf, sonra a.pdf geri taşınmalı.
    reverse_moves = move_order[3:]
    assert len(reverse_moves) == 2
    assert reverse_moves[0].split("->")[0].endswith("b.pdf")
    assert reverse_moves[1].split("->")[0].endswith("a.pdf")
    assert (tmp_path / "a.pdf").exists()
    assert (tmp_path / "b.pdf").exists()
    assert (tmp_path / "c.pdf").exists()
    assert not (tmp_path / "2026-08").exists() or list((tmp_path / "2026-08").iterdir()) == []


def test_apply_plan_reads_rollback_source_from_recorded_backup_path(session, tmp_path, monkeypatch):
    _write_pdf(tmp_path, "a.pdf")
    _write_pdf(tmp_path, "b.pdf")
    pdf_files = [
        PdfFileMetadata(filename="a.pdf", createdAt="2026-08-01"),
        PdfFileMetadata(filename="b.pdf", createdAt="2026-08-02"),
    ]
    plan = _plan([PlanStep(order=0, operationType=OperationType.MOVE, targetFolder="2026-08", affectedFileCount=2)])

    real_move = shutil.move
    call_count = {"n": 0}

    def flaky_move(src, dst):
        call_count["n"] += 1
        if call_count["n"] == 2:
            raise OSError("simulated disk failure")
        return real_move(src, dst)

    monkeypatch.setattr("backend.orchestrator.shutil.move", flaky_move)

    with pytest.raises(PlanApplicationError):
        apply_plan(session, plan, pdf_files, tmp_path)

    completed_op = session.query(Transaction).one().operations[0]
    assert completed_op.backup_path == str(tmp_path / "a.pdf")
    assert completed_op.status == "rolled_back"
    assert (tmp_path / "a.pdf").exists()


def test_apply_plan_marks_transaction_and_operations_rolled_back_on_failure(session, tmp_path, monkeypatch):
    _write_pdf(tmp_path, "a.pdf")
    _write_pdf(tmp_path, "b.pdf")
    pdf_files = [
        PdfFileMetadata(filename="a.pdf", createdAt="2026-08-01"),
        PdfFileMetadata(filename="b.pdf", createdAt="2026-08-02"),
    ]
    plan = _plan([PlanStep(order=0, operationType=OperationType.MOVE, targetFolder="2026-08", affectedFileCount=2)])

    real_move = shutil.move
    call_count = {"n": 0}

    def flaky_move(src, dst):
        call_count["n"] += 1
        if call_count["n"] == 2:
            raise OSError("simulated disk failure")
        return real_move(src, dst)

    monkeypatch.setattr("backend.orchestrator.shutil.move", flaky_move)

    with pytest.raises(PlanApplicationError):
        apply_plan(session, plan, pdf_files, tmp_path)

    transaction = session.query(Transaction).one()
    assert transaction.status == "rolled_back"
    assert all(op.status == "rolled_back" for op in transaction.operations)
