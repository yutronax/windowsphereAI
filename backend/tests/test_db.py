import pytest
from sqlalchemy.orm import Session

from backend.db import create_db_engine, create_session_factory, db_path
from backend.db_models import Base
from backend.file_operations import create_transaction, list_file_operations, record_file_operation


@pytest.fixture
def session() -> Session:
    engine = create_db_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    factory = create_session_factory(engine)
    with factory() as db_session:
        yield db_session


def test_db_path_raises_without_appdata(monkeypatch):
    monkeypatch.delenv("APPDATA", raising=False)

    with pytest.raises(RuntimeError):
        db_path()


def test_db_path_is_under_appdata_windows_ai_files(monkeypatch, tmp_path):
    monkeypatch.setenv("APPDATA", str(tmp_path))

    assert db_path() == tmp_path / "windows-ai-files" / "app.db"


def test_create_transaction_defaults_to_pending_status(session):
    transaction = create_transaction(session)

    assert transaction.id is not None
    assert transaction.status == "pending"


def test_record_file_operation_links_to_transaction(session):
    transaction = create_transaction(session)

    operation = record_file_operation(
        session,
        transaction,
        operation_type="Taşı",
        source_path=r"C:\Users\Yusuf\Documents\a.pdf",
        destination_path=r"C:\Users\Yusuf\Documents\2026-08\a.pdf",
        backup_path=r"C:\Users\Yusuf\AppData\windows-ai-files\backups\a.pdf",
    )

    assert operation.id is not None
    assert operation.transaction_id == transaction.id
    assert operation.status == "pending"
    assert operation.backup_path == r"C:\Users\Yusuf\AppData\windows-ai-files\backups\a.pdf"


def test_record_file_operation_backup_path_defaults_to_none(session):
    transaction = create_transaction(session)

    operation = record_file_operation(
        session,
        transaction,
        operation_type="Taşı",
        source_path="a.pdf",
        destination_path="2026-08/a.pdf",
    )

    assert operation.backup_path is None


def test_list_file_operations_returns_all_operations_for_a_transaction_in_order(session):
    transaction = create_transaction(session)
    other_transaction = create_transaction(session)

    first = record_file_operation(
        session, transaction, operation_type="Taşı", source_path="a.pdf", destination_path="2026-08/a.pdf"
    )
    second = record_file_operation(
        session, transaction, operation_type="Taşı", source_path="b.pdf", destination_path="2026-08/b.pdf"
    )
    record_file_operation(
        session, other_transaction, operation_type="Taşı", source_path="c.pdf", destination_path="2026-09/c.pdf"
    )

    operations = list_file_operations(session, transaction)

    assert [op.id for op in operations] == [first.id, second.id]


def test_transaction_operations_relationship_reflects_recorded_operations(session):
    transaction = create_transaction(session)
    record_file_operation(
        session, transaction, operation_type="Taşı", source_path="a.pdf", destination_path="2026-08/a.pdf"
    )

    session.refresh(transaction)

    assert len(transaction.operations) == 1
    assert transaction.operations[0].transaction is transaction
