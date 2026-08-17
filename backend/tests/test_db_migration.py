import sqlite3

import pytest
from sqlalchemy import Column, Integer, MetaData, String, Table, inspect

from backend.db import _add_missing_columns, create_db_engine


def test_create_db_engine_creates_all_tables_from_scratch(tmp_path):
    db_file = tmp_path / "app.db"

    engine = create_db_engine(f"sqlite:///{db_file}")

    table_names = set(inspect(engine).get_table_names())
    assert {"transactions", "file_operations"} <= table_names


def test_create_db_engine_adds_a_missing_column_to_an_existing_table_without_losing_data(tmp_path):
    db_file = tmp_path / "app.db"

    # Eski şemayı elle oluştur: file_operations tablosu var ama backup_path
    # kolonu YOK (modelin daha yeni bir sürümünde eklenmiş gibi simüle et).
    connection = sqlite3.connect(db_file)
    connection.execute(
        """
        CREATE TABLE transactions (
            id INTEGER PRIMARY KEY,
            created_at DATETIME,
            status VARCHAR
        )
        """
    )
    connection.execute(
        """
        CREATE TABLE file_operations (
            id INTEGER PRIMARY KEY,
            transaction_id INTEGER,
            operation_type VARCHAR,
            source_path VARCHAR,
            destination_path VARCHAR,
            created_at DATETIME,
            status VARCHAR
        )
        """
    )
    connection.execute("INSERT INTO transactions (id, status) VALUES (1, 'committed')")
    connection.execute(
        "INSERT INTO file_operations (id, transaction_id, operation_type, source_path, destination_path, status) "
        "VALUES (1, 1, 'Taşı', 'a.pdf', '2026-08/a.pdf', 'completed')"
    )
    connection.commit()
    connection.close()

    engine = create_db_engine(f"sqlite:///{db_file}")

    columns = {col["name"] for col in inspect(engine).get_columns("file_operations")}
    assert "backup_path" in columns

    with engine.connect() as verify_connection:
        row = verify_connection.exec_driver_sql(
            "SELECT source_path, destination_path, status, backup_path FROM file_operations WHERE id = 1"
        ).one()
    assert row.source_path == "a.pdf"
    assert row.destination_path == "2026-08/a.pdf"
    assert row.status == "completed"
    assert row.backup_path is None


def test_add_missing_columns_raises_instead_of_silently_dropping_a_not_null_constraint(tmp_path, monkeypatch):
    # Red-team bulgusu: bu shim, varsayılan değeri olmayan NOT NULL bir
    # kolon eklenmeye çalışılırsa sessizce nullable'a düşürmek yerine
    # GÜRÜLTÜLÜ biçimde başarısız olmalı (taze kurulum vs yükseltilmiş
    # kurulum arasında sessiz şema sürüklenmesini önlemek için).
    db_file = tmp_path / "app.db"
    connection = sqlite3.connect(db_file)
    connection.execute("CREATE TABLE file_operations (id INTEGER PRIMARY KEY, status VARCHAR)")
    connection.execute("INSERT INTO file_operations (id, status) VALUES (1, 'completed')")
    connection.commit()
    connection.close()

    fake_metadata = MetaData()
    Table(
        "file_operations",
        fake_metadata,
        Column("id", Integer, primary_key=True),
        Column("status", String),
        Column("required_new_field", String, nullable=False),
    )

    class _FakeBase:
        metadata = fake_metadata

    monkeypatch.setattr("backend.db.Base", _FakeBase)

    from sqlalchemy import create_engine

    engine = create_engine(f"sqlite:///{db_file}")

    with pytest.raises(RuntimeError, match="Şema göçü desteklenmiyor"):
        _add_missing_columns(engine)

    # Başarısız deneme sonrasında kolon eklenmemiş olmalı.
    assert "required_new_field" not in {col["name"] for col in inspect(engine).get_columns("file_operations")}


def test_create_db_engine_is_idempotent_on_an_already_up_to_date_schema(tmp_path):
    db_file = tmp_path / "app.db"

    create_db_engine(f"sqlite:///{db_file}")
    # İkinci çağrı hata fırlatmamalı ve şemayı bozmamalı.
    engine = create_db_engine(f"sqlite:///{db_file}")

    columns = {col["name"] for col in inspect(engine).get_columns("file_operations")}
    assert "backup_path" in columns
