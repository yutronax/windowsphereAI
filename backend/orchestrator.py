import shutil
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.db_models import FileOperation, Transaction
from backend.file_operations import create_transaction, record_file_operation
from backend.models import OperationType, PdfFileMetadata, PlanSkeleton, PlanStep
from backend.security import validate_plan_paths


class PlanApplicationError(Exception):
    """Raised when a plan cannot be applied. Any moves already performed for
    this call have been rolled back (moved back to their original location)
    before this is raised."""


# Saga #288/#289: MOVE'a ek olarak COPY ve DELETE desteklenmeye başladı.
# Her operationType'ın İLERİ (forward) ve GERİ (rollback) uygulaması farklı
# fiziksel semantiğe sahip — bu yüzden dispatch dict'leri kullanılıyor
# (gelecekteki RENAME task'ı için dördüncü bir dal eklemeyi kolaylaştırır).
#
# Sözleşme (tüm operationType'lar için AYNI — Saga #289'da netleştirildi):
# `destination_path` = forward işlem SONRASI dosyanın FİZİKSEL OLARAK
# bulunduğu yer; `backup_path` = rollback'in GERİ YÜKLEYECEĞİ konum. MOVE
# için destination=yeni konum/backup=eski konum; COPY için destination=kopya/
# backup=kaynak (rollback'te kullanılmaz, sadece şema tutarlılığı için);
# DELETE için destination=gizli yedek konumu/backup=orijinal kaynak konumu.
# Bu ortak sözleşme sayesinde rollback döngüsü HİÇBİR operationType'a özel
# dallanma gerektirmeden çalışır.
_SUPPORTED_OPERATION_TYPES = {OperationType.MOVE, OperationType.COPY, OperationType.DELETE}

# DELETE'in fiziksel yedeklerinin saklandığı, `allowed_root` altında gizli
# klasör. transaction.id ile ayrıştırılır (farklı transaction'lardaki aynı
# isimli dosyalar çakışmasın diye). Derinlik: klasör+txn_id+dosya = 3,
# MAX_PATH_DEPTH'i (security.py, Saga #272) AŞMAZ.
_DELETE_BACKUP_DIRNAME = ".windows-ai-files-backup"


def _delete_backup_path(allowed_root: Path, transaction_id: int, filename: str) -> Path:
    return allowed_root / _DELETE_BACKUP_DIRNAME / str(transaction_id) / filename


def _forward_move(source_path: Path, destination_path: Path) -> None:
    shutil.move(str(source_path), str(destination_path))


def _forward_copy(source_path: Path, destination_path: Path) -> None:
    shutil.copy2(str(source_path), str(destination_path))


def _forward_delete(source_path: Path, destination_path: Path) -> None:
    # `destination_path` burada gizli yedek konumu (bkz. `_delete_backup_path`).
    # Önce fiziksel yedek alınır, SONRA kaynak silinir — sıra önemli: yedek
    # başarısız olursa kaynak hâlâ yerinde kalır, hiçbir veri kaybı olmaz.
    destination_path.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(str(source_path), str(destination_path))
    source_path.unlink()


_FORWARD_OPERATIONS = {
    OperationType.MOVE: _forward_move,
    OperationType.COPY: _forward_copy,
    OperationType.DELETE: _forward_delete,
}


def _rollback_move(destination_path: Path, backup_path: Path) -> None:
    shutil.move(str(destination_path), str(backup_path))


def _rollback_copy(destination_path: Path, backup_path: Path) -> None:
    # COPY'de kaynak hiç değişmedi — rollback SADECE hedefteki kopyayı siler,
    # backup_path'e (=kaynak) hiç dokunmaz.
    destination_path.unlink()


_ROLLBACK_OPERATIONS = {
    OperationType.MOVE: _rollback_move,
    OperationType.COPY: _rollback_copy,
    # DELETE rollback'i MOVE ile AYNI: "gizli yedek konumundaki dosyayı
    # orijinal konuma geri taşı" — _rollback_move zaten tam olarak bunu
    # yapıyor, ayrı bir fonksiyona gerek yok.
    OperationType.DELETE: _rollback_move,
}


def _distribute_files_to_steps(
    pdf_files: list[PdfFileMetadata], steps: list[PlanStep]
) -> list[tuple[PlanStep, list[PdfFileMetadata]]]:
    """`PlanStep.fileNames` (Saga #286) üzerinden her step'in HANGİ
    dosyalara sahip olduğunu KESİN olarak çözer — artık pozisyonel/sıralı
    bir varsayım YOK. Her `fileNames` girdisinin `pdf_files` içinde
    gerçekten var olduğunu VE `pdf_files`'taki her dosyanın TAM OLARAK
    bir step'e atandığını (ne eksik ne fazla, ne çift atama) doğrular;
    aksi halde tüm plan reddedilir."""
    ordered_steps = sorted(steps, key=lambda step: step.order)
    files_by_name = {file.filename: file for file in pdf_files}

    assigned_names: set[str] = set()
    distributed: list[tuple[PlanStep, list[PdfFileMetadata]]] = []
    for step in ordered_steps:
        step_files: list[PdfFileMetadata] = []
        for name in step.fileNames:
            if name not in files_by_name:
                raise PlanApplicationError(
                    f"Plan step {step.order}, pdf_files listesinde olmayan bir "
                    f"dosyaya atıfta bulunuyor: '{name}'"
                )
            if name in assigned_names:
                raise PlanApplicationError(
                    f"Dosya birden fazla step'e atanmış: '{name}'"
                )
            assigned_names.add(name)
            step_files.append(files_by_name[name])
        distributed.append((step, step_files))

    unassigned = set(files_by_name) - assigned_names
    if unassigned:
        raise PlanApplicationError(
            f"Hiçbir step'e atanmamış dosyalar var: {sorted(unassigned)}"
        )

    return distributed


def apply_plan(
    session: Session,
    plan: PlanSkeleton,
    pdf_files: list[PdfFileMetadata],
    allowed_root: Path,
) -> Transaction:
    """Onaylanmış bir planı TEK transaction içinde gerçekten uygular: hedef
    tarih klasörlerini oluşturur, PDF'leri plan sırasıyla taşır, her adımı
    `FileOperation` olarak kaydeder (Saga #275). Bir adım başarısız olursa
    (Saga #276) o ana kadar tamamlanmış adımlar, kaydedilen
    `FileOperation.destination_path`/`backup_path` alanları kullanılarak
    TERS SIRAYLA eski konumlarına geri taşınır; `PlanApplicationError`
    net bir hata mesajıyla fırlatılır — kısmi başarı asla döndürülmez, her
    `FileOperation`ın nihai durumu (`rolled_back`/`rollback_failed`) DB'ye
    yazılır.

    `OperationType.MOVE`, `OperationType.COPY` ve `OperationType.DELETE`
    destekler (Saga #288/#289); başka bir operationType görürse hiçbir
    dosyaya dokunmadan reddeder."""
    validate_plan_paths(plan, pdf_files, allowed_root)

    for step in plan.steps:
        if step.operationType not in _SUPPORTED_OPERATION_TYPES:
            supported = ", ".join(f"'{op.value}'" for op in _SUPPORTED_OPERATION_TYPES)
            raise PlanApplicationError(
                f"Orchestrator şu an sadece {supported} operasyonlarını "
                f"destekliyor, gelen: '{step.operationType.value}'"
            )

    step_files = _distribute_files_to_steps(pdf_files, plan.steps)

    transaction = create_transaction(session)
    session.commit()  # Transaction kaydı, sonuç ne olursa olsun kalıcı olsun.

    applied: list[FileOperation] = []
    try:
        for step, files in step_files:
            # Saga #289: DELETE'in gerçek bir hedef klasörü yok — targetFolder
            # (YYYY-MM) şema gereği hâlâ zorunlu ama DELETE için hiç
            # kullanılmıyor (bkz. ATDD "bilinen sınırlama"). Sadece
            # MOVE/COPY için gerçek hedef klasör oluşturulur.
            if step.operationType != OperationType.DELETE:
                target_dir = allowed_root / step.targetFolder
                target_dir.mkdir(parents=True, exist_ok=True)
            for pdf_file in files:
                source_path = allowed_root / pdf_file.filename
                if step.operationType == OperationType.DELETE:
                    destination_path = _delete_backup_path(allowed_root, transaction.id, pdf_file.filename)
                    backup_path = source_path
                else:
                    destination_path = target_dir / pdf_file.filename
                    backup_path = source_path

                operation = record_file_operation(
                    session,
                    transaction,
                    operation_type=step.operationType.value,
                    source_path=str(source_path),
                    destination_path=str(destination_path),
                    backup_path=str(backup_path),
                )
                _FORWARD_OPERATIONS[step.operationType](source_path, destination_path)
                operation.status = "completed"
                session.commit()
                applied.append(operation)
    except Exception as exc:
        # Saga #276: geri alma, bellek-içi bir yardımcı yapı değil, DOĞRUDAN
        # kaydedilmiş `FileOperation.destination_path`/`backup_path`
        # alanlarından okunarak yapılır — tamamlanmış adımlar TERS SIRAYLA
        # (`reversed(applied)`) geri çevrilir.
        for operation in reversed(applied):
            destination_path = Path(operation.destination_path)
            original_source_path = Path(operation.backup_path)
            if not destination_path.exists():
                operation.status = "rolled_back"
                continue
            # Ters işlemin KENDİSİ de başarısız olabilir (ör. original_source
            # bu sırada başka bir işlem tarafından dolduruldu, disk doldu).
            # Bunu yakalamazsak orijinal exception maskelenir VE aşağıdaki
            # transaction.status="rolled_back"/commit hiç çalışmaz — transaction
            # sonsuza dek "pending" kalır. En iyi çaba: hatayı yut, geri kalan
            # dosyaları geri almaya devam et, bu operasyonu doğru şekilde
            # "rollback_failed" olarak işaretle (yanlışlıkla "rolled_back"
            # DEME — dosya fiziksel olarak hâlâ hedefte, #276'nın geri alma
            # mantığı buna güvenecek), orijinal exception'ı (`exc`) fırlat.
            try:
                # Saga #288: rollback artık operation_type'a göre dallanıyor —
                # MOVE için hedefi kaynağa geri taşı, COPY için sadece
                # hedefteki kopyayı sil (kaynağa hiç dokunma). Dispatch
                # sözlüğü araması (`OperationType(...)`/`[...]`) da AYNI
                # try içinde — bilinmeyen/bozuk bir `operation_type` (ör.
                # ileride eklenecek bir op türü rollback tablosuna
                # unutulursa) `ValueError`/`KeyError` fırlatabilir; bunu
                # yakalamazsak orijinal exception (`exc`) maskelenir ve
                # transaction sonsuza dek "pending" kalır — aynı OSError
                # riskiyle simetrik olarak ele alınmalı (red-team bulgusu,
                # Saga #288).
                _ROLLBACK_OPERATIONS[OperationType(operation.operation_type)](
                    destination_path, original_source_path
                )
                operation.status = "rolled_back"
            except (OSError, ValueError, KeyError):
                operation.status = "rollback_failed"
        for operation in transaction.operations:
            # Kaydı oluşturulmuş ama shutil.move'un kendisi başarısız olduğu
            # için hiç "completed" olamamış son adım — hiçbir dosya
            # hareketi yapılmadığı için doğrudan rolled_back sayılabilir.
            if operation.status == "pending":
                operation.status = "rolled_back"
        transaction.status = "rolled_back"
        session.commit()
        raise PlanApplicationError(
            f"Plan uygulanamadı, tamamlanmış adımlar geri alındı: {exc}"
        ) from exc

    transaction.status = "committed"
    session.commit()
    return transaction


def recover_incomplete_transactions(session: Session) -> list[Transaction]:
    """Saga #286: `apply_plan` çalışırken süreç çökerse (`shutil.move`
    başarılı olduktan hemen sonra ama `session.commit()`'ten ÖNCE),
    `FileOperation.status` sonsuza dek "pending" asılı kalabilir — dosya
    fiziksel olarak taşınmış olabilir ama DB bunu bilmiyor olabilir. Bu
    fonksiyon `status="pending"` olan tüm `Transaction`'ları tarar ve her
    `FileOperation`'ı GERÇEK dosya sistemi durumuna göre uzlaştırır:
    `destination_path` fiziksel olarak varsa dosya gerçekten taşınmış
    demektir → `"completed"`; yoksa taşıma hiç gerçekleşmemiş/geri
    alınmış demektir → `"rolled_back"` (kaynak zaten olması gereken
    yerde). Tüm operasyonları `"completed"` olan bir transaction
    `"committed"` işaretlenir, aksi halde `"rolled_back"`.

    ÖNEMLİ (red-team bulgusu): transaction'ın kendisi hâlâ `"pending"`
    olduğu sürece, İÇİNDEKİ HER `FileOperation` yeniden doğrulanır —
    sadece kendi durumu `"pending"` olanlar DEĞİL. Gerekçe: `apply_plan`in
    rollback except bloğu bir operasyonu bellek-içi `"completed"`→
    `"rolled_back"`e çevirdikten SONRA ama nihai `session.commit()`'ten
    ÖNCE süreç çökerse, DB'de o operasyon hâlâ `"completed"` görünür —
    ama dosya fiziksel olarak zaten geri taşınmış olabilir. Sadece
    `status=="pending"` olanları kontrol etmek bu operasyonu sonsuza dek
    yanlış etiketli bırakırdı.

    Henüz bir FastAPI startup event'ine BAĞLANMADI (Saga #287'nin devamı
    — gerçek bir apply endpoint'i olmadan bağlanacak bir başlangıç akışı
    yok); bu saf, çağrılabilir bir fonksiyon."""
    pending_transactions = session.scalars(
        select(Transaction).where(Transaction.status == "pending")
    ).all()

    recovered: list[Transaction] = []
    for transaction in pending_transactions:
        all_completed = True
        for operation in transaction.operations:
            if Path(operation.destination_path).exists():
                operation.status = "completed"
            else:
                operation.status = "rolled_back"
                all_completed = False
        if any(operation.status == "rolled_back" for operation in transaction.operations):
            all_completed = False
        transaction.status = "committed" if all_completed else "rolled_back"
        recovered.append(transaction)

    session.commit()
    return recovered
