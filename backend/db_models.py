from __future__ import annotations

import datetime as dt

from sqlalchemy import DateTime, ForeignKey, String
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


class Transaction(Base):
    """Bir plan onayının uygulanmasını temsil eden atomik birim.
    Saga #274/#276: tüm FileOperation'ları başarılıysa "committed",
    herhangi biri başarısız olup geri alındıysa "rolled_back" olur."""

    __tablename__ = "transactions"

    id: Mapped[int] = mapped_column(primary_key=True)
    created_at: Mapped[dt.datetime] = mapped_column(DateTime, default=dt.datetime.utcnow)
    status: Mapped[str] = mapped_column(String, default="pending")
    # Saga #301: bu transaction'ın uygulandığı allowed_root — server tarafında
    # kaydedilir (istemciden asla alınmaz), revert_transaction bunu kullanır.
    # Nullable: migration öncesi eski kayıtlarda yok.
    allowed_root: Mapped[str | None] = mapped_column(String, nullable=True)

    operations: Mapped[list["FileOperation"]] = relationship(
        back_populates="transaction", cascade="all, delete-orphan"
    )


class FileOperation(Base):
    """Tek bir dosya hareketinin denetim kaydı. `backup_path`, geri alma
    (Saga #276) sırasında kullanılacak fiziksel yedek konumudur — gerçek
    taşıma/kopyalama Saga #274'te yazılacak Orchestrator'a ait, bu tablo
    sadece kaydı tutar."""

    __tablename__ = "file_operations"

    id: Mapped[int] = mapped_column(primary_key=True)
    transaction_id: Mapped[int] = mapped_column(ForeignKey("transactions.id"))
    operation_type: Mapped[str] = mapped_column(String)
    source_path: Mapped[str] = mapped_column(String)
    destination_path: Mapped[str] = mapped_column(String)
    backup_path: Mapped[str | None] = mapped_column(String, nullable=True)
    created_at: Mapped[dt.datetime] = mapped_column(DateTime, default=dt.datetime.utcnow)
    status: Mapped[str] = mapped_column(String, default="pending")

    transaction: Mapped["Transaction"] = relationship(back_populates="operations")
