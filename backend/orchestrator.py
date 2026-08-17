import shutil
from pathlib import Path

from sqlalchemy.orm import Session

from backend.db_models import FileOperation, Transaction
from backend.file_operations import create_transaction, record_file_operation
from backend.models import OperationType, PdfFileMetadata, PlanSkeleton, PlanStep
from backend.security import validate_plan_paths


class PlanApplicationError(Exception):
    """Raised when a plan cannot be applied. Any moves already performed for
    this call have been rolled back (moved back to their original location)
    before this is raised."""


def _distribute_files_to_steps(
    pdf_files: list[PdfFileMetadata], steps: list[PlanStep]
) -> list[tuple[PlanStep, list[PdfFileMetadata]]]:
    """`PlanStep` bugün HANGİ dosyanın kendisine ait olduğunu taşımıyor
    (sadece `affectedFileCount`) — bu yüzden `pdf_files`, plan adımlarına
    `order`a göre SIRAYLA, `affectedFileCount` kadar bölünerek dağıtılır.
    Bu KIRILGAN bir varsayımdır (LLM'in `pdf_files` sırasını koruduğunu
    varsayar); asıl düzeltme `PlanStep`e açık bir dosya listesi eklemek
    olurdu, o ayrı bir task. Toplam sayı eşleşmezse tüm plan reddedilir."""
    ordered_steps = sorted(steps, key=lambda step: step.order)
    total_expected = sum(step.affectedFileCount for step in ordered_steps)
    if total_expected != len(pdf_files):
        raise PlanApplicationError(
            f"pdf_files sayısı ({len(pdf_files)}) planın affectedFileCount "
            f"toplamıyla ({total_expected}) eşleşmiyor"
        )

    distributed: list[tuple[PlanStep, list[PdfFileMetadata]]] = []
    cursor = 0
    for step in ordered_steps:
        chunk = pdf_files[cursor : cursor + step.affectedFileCount]
        distributed.append((step, chunk))
        cursor += step.affectedFileCount
    return distributed


def apply_plan(
    session: Session,
    plan: PlanSkeleton,
    pdf_files: list[PdfFileMetadata],
    allowed_root: Path,
) -> Transaction:
    """Onaylanmış bir planı TEK transaction içinde gerçekten uygular: hedef
    tarih klasörlerini oluşturur, PDF'leri plan sırasıyla taşır, her adımı
    `FileOperation` olarak kaydeder. Bir adım başarısız olursa o ana kadar
    taşınmış dosyalar ters sırayla eski konumlarına geri taşınır ve
    `PlanApplicationError` fırlatılır — kısmi başarı asla döndürülmez.

    Sadece `OperationType.MOVE` destekler (bu MVP'nin "PDF'leri tarihe göre
    sırala" kapsamı taşımadır); başka bir operationType görürse hiçbir
    dosyaya dokunmadan reddeder."""
    validate_plan_paths(plan, pdf_files, allowed_root)

    for step in plan.steps:
        if step.operationType != OperationType.MOVE:
            raise PlanApplicationError(
                f"Orchestrator şu an sadece '{OperationType.MOVE.value}' "
                f"operasyonunu destekliyor, gelen: '{step.operationType.value}'"
            )

    step_files = _distribute_files_to_steps(pdf_files, plan.steps)

    transaction = create_transaction(session)
    session.commit()  # Transaction kaydı, sonuç ne olursa olsun kalıcı olsun.

    applied: list[tuple[FileOperation, Path, Path]] = []  # (operation, destination, original_source)
    try:
        for step, files in step_files:
            target_dir = allowed_root / step.targetFolder
            target_dir.mkdir(parents=True, exist_ok=True)
            for pdf_file in files:
                source_path = allowed_root / pdf_file.filename
                destination_path = target_dir / pdf_file.filename

                operation = record_file_operation(
                    session,
                    transaction,
                    operation_type=step.operationType.value,
                    source_path=str(source_path),
                    destination_path=str(destination_path),
                    backup_path=str(source_path),
                )
                shutil.move(str(source_path), str(destination_path))
                operation.status = "completed"
                session.commit()
                applied.append((operation, destination_path, source_path))
    except Exception as exc:
        for operation, destination_path, original_source_path in reversed(applied):
            if not destination_path.exists():
                operation.status = "rolled_back"
                continue
            # Ters taşımanın KENDİSİ de başarısız olabilir (ör. original_source
            # bu sırada başka bir işlem tarafından dolduruldu, disk doldu).
            # Bunu yakalamazsak orijinal exception maskelenir VE aşağıdaki
            # transaction.status="rolled_back"/commit hiç çalışmaz — transaction
            # sonsuza dek "pending" kalır. En iyi çaba: hatayı yut, geri kalan
            # dosyaları geri taşımaya devam et, bu operasyonu doğru şekilde
            # "rollback_failed" olarak işaretle (yanlışlıkla "rolled_back"
            # DEME — dosya fiziksel olarak hâlâ hedefte, #276'nın geri alma
            # mantığı buna güvenecek), orijinal exception'ı (`exc`) fırlat.
            try:
                shutil.move(str(destination_path), str(original_source_path))
                operation.status = "rolled_back"
            except OSError:
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
