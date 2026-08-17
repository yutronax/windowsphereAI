from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.db_models import FileOperation, Transaction

# Bu modül SADECE denetim kaydı tutar — path GÜVENLİK doğrulaması YAPMAZ.
# Çağıran (Saga #274 Orchestrator), source_path/destination_path'i
# backend/security.py'deki is_path_allowed/is_system_protected/
# is_path_too_deep ile ÖNCEDEN doğrulamış olmalıdır; bu fonksiyonlar ham
# string'leri hiçbir kontrol yapmadan kaydeder (red-team bulgusu, Saga
# #275).
#
# `create_transaction`/`record_file_operation` sadece `session.flush()`
# çağırır, `commit()` ÇAĞIRMAZ — satırlar aynı session içinde görünür ama
# diske YAZILMAZ. Çağıran, tüm transaction'ı (bir veya birden fazla
# FileOperation) kapsayan `session.commit()`/`session.rollback()`'i
# KENDİSİ yönetmelidir (Saga #274/#276: bir dosya taşıma adımı başarısız
# olursa transaction'ın tamamı rollback edilebilsin diye).


def create_transaction(session: Session) -> Transaction:
    transaction = Transaction()
    session.add(transaction)
    session.flush()
    return transaction


def record_file_operation(
    session: Session,
    transaction: Transaction,
    *,
    operation_type: str,
    source_path: str,
    destination_path: str,
    backup_path: str | None = None,
) -> FileOperation:
    operation = FileOperation(
        transaction_id=transaction.id,
        operation_type=operation_type,
        source_path=source_path,
        destination_path=destination_path,
        backup_path=backup_path,
    )
    session.add(operation)
    session.flush()
    return operation


def list_file_operations(session: Session, transaction: Transaction) -> list[FileOperation]:
    statement = (
        select(FileOperation)
        .where(FileOperation.transaction_id == transaction.id)
        .order_by(FileOperation.id)
    )
    return list(session.scalars(statement).all())
