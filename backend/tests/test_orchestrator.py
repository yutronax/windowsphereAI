import shutil
from pathlib import Path

import pytest
from sqlalchemy.orm import Session

from backend.db import create_db_engine, create_session_factory
from backend.db_models import Base, Transaction
from backend.models import DateSource, OperationType, PdfFileMetadata, PlanSkeleton, PlanStep, SortOrder
import datetime as dt

from backend.orchestrator import (
    PlanApplicationError,
    TransactionRevertError,
    apply_plan,
    purge_expired_delete_backups,
    recover_incomplete_transactions,
    revert_transaction,
)
from backend.security import PathWhitelistError


@pytest.fixture
def session() -> Session:
    engine = create_db_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    factory = create_session_factory(engine)
    with factory() as db_session:
        yield db_session


def _plan(steps: list[PlanStep]) -> PlanSkeleton:
    return PlanSkeleton(steps=steps, dateSource=DateSource.CREATED_AT, sortOrder=SortOrder.ASCENDING)


def _step(
    order: int,
    target_folder: str,
    file_names: list[str],
    operation_type: OperationType = OperationType.MOVE,
    new_file_names: list[str] | None = None,
) -> PlanStep:
    return PlanStep(
        order=order,
        operationType=operation_type,
        targetFolder=target_folder,
        affectedFileCount=len(file_names),
        fileNames=file_names,
        newFileNames=new_file_names,
    )


def _write_pdf(root, filename: str) -> None:
    (root / filename).write_bytes(b"%PDF-1.4 fake")


def _write_real_pdf(root, filename: str, page_count: int) -> None:
    # Saga #304: MERGE testleri gercek pypdf ile olusturulmus gercek PDF'ler
    # gerektiriyor (sayfa sayisi dogrulamasi icin) - _write_pdf'in sahte
    # bayt icerigi pypdf.PdfReader ile acilamaz.
    from pypdf import PdfWriter

    writer = PdfWriter()
    for _ in range(page_count):
        writer.add_blank_page(width=200, height=200)
    with open(root / filename, "wb") as f:
        writer.write(f)
    writer.close()


def test_apply_plan_moves_files_into_target_folder_and_records_completed_operations(session, tmp_path):
    _write_pdf(tmp_path, "a.pdf")
    _write_pdf(tmp_path, "b.pdf")
    pdf_files = [
        PdfFileMetadata(filename="a.pdf", createdAt="2026-08-01"),
        PdfFileMetadata(filename="b.pdf", createdAt="2026-08-02"),
    ]
    plan = _plan([_step(0, "2026-08", ["a.pdf", "b.pdf"])])

    transaction = apply_plan(session, plan, pdf_files, tmp_path)

    assert not (tmp_path / "a.pdf").exists()
    assert not (tmp_path / "b.pdf").exists()
    assert (tmp_path / "2026-08" / "a.pdf").exists()
    assert (tmp_path / "2026-08" / "b.pdf").exists()
    assert transaction.status == "committed"
    assert len(transaction.operations) == 2
    assert all(op.status == "completed" for op in transaction.operations)


def test_apply_plan_splits_pdf_files_across_multiple_steps_by_file_names(session, tmp_path):
    _write_pdf(tmp_path, "a.pdf")
    _write_pdf(tmp_path, "b.pdf")
    pdf_files = [
        PdfFileMetadata(filename="a.pdf", createdAt="2026-08-01"),
        PdfFileMetadata(filename="b.pdf", createdAt="2026-09-01"),
    ]
    plan = _plan([_step(0, "2026-08", ["a.pdf"]), _step(1, "2026-09", ["b.pdf"])])

    apply_plan(session, plan, pdf_files, tmp_path)

    assert (tmp_path / "2026-08" / "a.pdf").exists()
    assert (tmp_path / "2026-09" / "b.pdf").exists()


def test_apply_plan_ignores_step_order_when_matching_files_by_name(session, tmp_path):
    # Saga #286: dağıtım artık pozisyonel DEĞİL, isimle eşleşiyor — steps'in
    # sırası veya pdf_files'ın sırası dosya-step eşleşmesini etkilemez.
    _write_pdf(tmp_path, "a.pdf")
    _write_pdf(tmp_path, "b.pdf")
    pdf_files = [
        PdfFileMetadata(filename="b.pdf", createdAt="2026-09-01"),
        PdfFileMetadata(filename="a.pdf", createdAt="2026-08-01"),
    ]
    plan = _plan([_step(1, "2026-09", ["b.pdf"]), _step(0, "2026-08", ["a.pdf"])])

    apply_plan(session, plan, pdf_files, tmp_path)

    assert (tmp_path / "2026-08" / "a.pdf").exists()
    assert (tmp_path / "2026-09" / "b.pdf").exists()


def test_apply_plan_rejects_whole_plan_without_moving_anything_when_a_pdf_file_is_unassigned(session, tmp_path):
    _write_pdf(tmp_path, "a.pdf")
    _write_pdf(tmp_path, "b.pdf")
    pdf_files = [
        PdfFileMetadata(filename="a.pdf", createdAt="2026-08-01"),
        PdfFileMetadata(filename="b.pdf", createdAt="2026-08-02"),
    ]
    plan = _plan([_step(0, "2026-08", ["a.pdf"])])  # b.pdf hiçbir step'e atanmadı

    with pytest.raises(PlanApplicationError):
        apply_plan(session, plan, pdf_files, tmp_path)

    assert (tmp_path / "a.pdf").exists()
    assert (tmp_path / "b.pdf").exists()
    assert not (tmp_path / "2026-08").exists()


def test_apply_plan_rejects_whole_plan_when_a_step_references_an_unknown_file(session, tmp_path):
    _write_pdf(tmp_path, "a.pdf")
    pdf_files = [PdfFileMetadata(filename="a.pdf", createdAt="2026-08-01")]
    plan = _plan([_step(0, "2026-08", ["a.pdf", "ghost.pdf"])])

    with pytest.raises(PlanApplicationError):
        apply_plan(session, plan, pdf_files, tmp_path)

    assert (tmp_path / "a.pdf").exists()
    assert not (tmp_path / "2026-08").exists()


def test_apply_plan_rejects_whole_plan_when_a_source_file_escapes_the_whitelist(session, tmp_path):
    pdf_files = [PdfFileMetadata(filename="..", createdAt="2026-08-01")]
    plan = _plan([_step(0, "2026-08", [".."])])

    with pytest.raises(Exception):
        apply_plan(session, plan, pdf_files, tmp_path)

    assert not (tmp_path / "2026-08").exists()


def test_apply_plan_does_not_touch_any_file_for_a_list_only_plan(session, tmp_path):
    # Saga #291: LIST tamamen salt okunur/inert - hicbir dosya sistemi
    # cagrisi yapilmaz, hicbir FileOperation kaydi olusturulmaz. Bu test
    # onceden "desteklenmeyen operationType" ornegi olarak LIST kullanan
    # bir testin yerini aldi - artik OperationType enum'undaki TUM 5
    # deger destekleniyor, "desteklenmeyen tip" senaryosu artik yok.
    _write_pdf(tmp_path, "a.pdf")
    pdf_files = [PdfFileMetadata(filename="a.pdf", createdAt="2026-08-01")]
    plan = _plan([_step(0, "2026-08", ["a.pdf"], operation_type=OperationType.LIST)])

    transaction = apply_plan(session, plan, pdf_files, tmp_path)

    assert (tmp_path / "a.pdf").exists()
    assert not (tmp_path / "2026-08").exists()
    assert transaction.status == "committed"
    assert transaction.operations == []


def test_apply_plan_only_processes_the_move_step_in_a_mixed_list_and_move_plan(session, tmp_path):
    _write_pdf(tmp_path, "a.pdf")
    _write_pdf(tmp_path, "b.pdf")
    pdf_files = [
        PdfFileMetadata(filename="a.pdf", createdAt="2026-08-01"),
        PdfFileMetadata(filename="b.pdf", createdAt="2026-08-02"),
    ]
    plan = _plan(
        [
            _step(0, "2026-08", ["a.pdf"], operation_type=OperationType.LIST),
            _step(1, "2026-08", ["b.pdf"], operation_type=OperationType.MOVE),
        ]
    )

    transaction = apply_plan(session, plan, pdf_files, tmp_path)

    assert (tmp_path / "a.pdf").exists()  # LIST dokunmadi
    assert not (tmp_path / "b.pdf").exists()  # MOVE tasidi
    assert (tmp_path / "2026-08" / "b.pdf").exists()
    assert len(transaction.operations) == 1  # sadece MOVE icin kayit var


def test_apply_plan_rejects_an_operation_type_missing_from_supported_set(session, tmp_path, monkeypatch):
    # Red-team bulgusu (Saga #291): OperationType enum'undaki TUM 5
    # deger artik destekleniyor, bu yuzden _SUPPORTED_OPERATION_TYPES
    # kontrolu su an olu kod - gercek bir enum degeriyle tetiklenemiyor.
    # Gelecekte enum'a yeni bir deger eklenip _SUPPORTED_OPERATION_TYPES
    # guncellenmesi UNUTULURSA bu guard'in hala calistigini dogrulamak
    # icin _SUPPORTED_OPERATION_TYPES'i monkeypatch ile daraltiyoruz.
    import backend.orchestrator as orchestrator_module

    monkeypatch.setattr(orchestrator_module, "_SUPPORTED_OPERATION_TYPES", {OperationType.MOVE})
    _write_pdf(tmp_path, "a.pdf")
    pdf_files = [PdfFileMetadata(filename="a.pdf", createdAt="2026-08-01")]
    plan = _plan([_step(0, "2026-08", ["a.pdf"], operation_type=OperationType.COPY)])

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
    plan = _plan([_step(0, "2026-08", ["a.pdf", "b.pdf"])])

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
    plan = _plan([_step(0, "2026-08", ["a.pdf", "b.pdf", "c.pdf"])])

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
    plan = _plan([_step(0, "2026-08", ["a.pdf", "b.pdf"])])

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
    plan = _plan([_step(0, "2026-08", ["a.pdf", "b.pdf"])])

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


def test_apply_plan_copies_files_leaving_the_source_intact(session, tmp_path):
    _write_pdf(tmp_path, "a.pdf")
    pdf_files = [PdfFileMetadata(filename="a.pdf", createdAt="2026-08-01")]
    plan = _plan([_step(0, "2026-08", ["a.pdf"], operation_type=OperationType.COPY)])

    transaction = apply_plan(session, plan, pdf_files, tmp_path)

    assert (tmp_path / "a.pdf").exists()  # kaynak hala yerinde
    assert (tmp_path / "2026-08" / "a.pdf").exists()  # kopya olusturuldu
    assert transaction.status == "committed"
    assert transaction.operations[0].status == "completed"


def test_apply_plan_rolls_back_a_copy_by_deleting_the_destination_without_touching_source(session, tmp_path, monkeypatch):
    _write_pdf(tmp_path, "a.pdf")
    _write_pdf(tmp_path, "b.pdf")
    pdf_files = [
        PdfFileMetadata(filename="a.pdf", createdAt="2026-08-01"),
        PdfFileMetadata(filename="b.pdf", createdAt="2026-08-02"),
    ]
    plan = _plan([_step(0, "2026-08", ["a.pdf", "b.pdf"], operation_type=OperationType.COPY)])

    real_copy = shutil.copy2
    call_count = {"n": 0}

    def flaky_copy(src, dst):
        call_count["n"] += 1
        if call_count["n"] == 2:
            raise OSError("simulated disk failure")
        return real_copy(src, dst)

    monkeypatch.setattr("backend.orchestrator.shutil.copy2", flaky_copy)

    with pytest.raises(PlanApplicationError):
        apply_plan(session, plan, pdf_files, tmp_path)

    # a.pdf kopyalanmisti, rollback hedefteki kopyayi sildi.
    assert (tmp_path / "a.pdf").exists()  # kaynak hic dokunulmadi
    assert not (tmp_path / "2026-08" / "a.pdf").exists()  # kopya silindi
    assert (tmp_path / "b.pdf").exists()  # b.pdf hic kopyalanmadi


def test_apply_plan_raises_original_error_not_a_masked_one_when_rollback_dispatch_fails(session, tmp_path, monkeypatch):
    # Red-team bulgusu (Saga #288): rollback sozlugu aramasi (OperationType(...))
    # eskiden sadece OSError'a karsi korunuyordu - bilinmeyen bir operation_type
    # ValueError/KeyError firlatip orijinal hatayi (exc) maskeleyebilirdi ve
    # transaction sonsuza dek "pending" kalirdi. Bu artik yakalaniyor.
    _write_pdf(tmp_path, "a.pdf")
    _write_pdf(tmp_path, "b.pdf")
    pdf_files = [
        PdfFileMetadata(filename="a.pdf", createdAt="2026-08-01"),
        PdfFileMetadata(filename="b.pdf", createdAt="2026-08-02"),
    ]
    plan = _plan([_step(0, "2026-08", ["a.pdf", "b.pdf"])])

    real_move = shutil.move
    call_count = {"n": 0}

    def flaky_move(src, dst):
        call_count["n"] += 1
        if call_count["n"] == 2:
            raise OSError("simulated disk failure")
        return real_move(src, dst)

    monkeypatch.setattr("backend.orchestrator.shutil.move", flaky_move)
    monkeypatch.setattr("backend.orchestrator._ROLLBACK_OPERATIONS", {})  # bilinmeyen operation_type simule eder

    with pytest.raises(PlanApplicationError, match="simulated disk failure"):
        apply_plan(session, plan, pdf_files, tmp_path)

    transaction = session.query(Transaction).one()
    assert transaction.status == "rolled_back"  # "pending" asili KALMADI
    assert transaction.operations[0].status == "rollback_failed"


def test_apply_plan_deletes_files_after_backing_them_up(session, tmp_path):
    _write_pdf(tmp_path, "a.pdf")
    pdf_files = [PdfFileMetadata(filename="a.pdf", createdAt="2026-08-01")]
    plan = _plan([_step(0, "2026-08", ["a.pdf"], operation_type=OperationType.DELETE)])

    transaction = apply_plan(session, plan, pdf_files, tmp_path)

    assert not (tmp_path / "a.pdf").exists()  # kaynak silindi
    backup_path = tmp_path / ".windows-ai-files-backup" / str(transaction.id) / "a.pdf"
    assert backup_path.exists()  # gercek fiziksel yedek olusturuldu
    assert transaction.status == "committed"
    assert transaction.operations[0].status == "completed"


def test_apply_plan_rolls_back_a_delete_by_restoring_the_file_from_backup(session, tmp_path, monkeypatch):
    _write_pdf(tmp_path, "a.pdf")
    _write_pdf(tmp_path, "b.pdf")
    pdf_files = [
        PdfFileMetadata(filename="a.pdf", createdAt="2026-08-01"),
        PdfFileMetadata(filename="b.pdf", createdAt="2026-08-02"),
    ]
    plan = _plan([_step(0, "2026-08", ["a.pdf", "b.pdf"], operation_type=OperationType.DELETE)])

    real_unlink = Path.unlink
    call_count = {"n": 0}

    def flaky_unlink(self, *args, **kwargs):
        call_count["n"] += 1
        if call_count["n"] == 2:
            raise OSError("simulated disk failure")
        return real_unlink(self, *args, **kwargs)

    monkeypatch.setattr("pathlib.Path.unlink", flaky_unlink)

    with pytest.raises(PlanApplicationError):
        apply_plan(session, plan, pdf_files, tmp_path)

    # a.pdf silinip yedeklendi, sonra rollback ile orijinal konumuna geri geldi.
    assert (tmp_path / "a.pdf").exists()
    # b.pdf silme islemi hic basarili olmadi, zaten yerinde kalmali.
    assert (tmp_path / "b.pdf").exists()


def test_delete_backup_path_stays_within_max_path_depth(tmp_path):
    from backend.orchestrator import _DELETE_BACKUP_DIRNAME, _delete_backup_path
    from backend.security import MAX_PATH_DEPTH, is_path_too_deep

    backup_path = _delete_backup_path(tmp_path, transaction_id=1, filename="a.pdf")

    assert backup_path.parent.parent.name == _DELETE_BACKUP_DIRNAME
    backup_path.parent.mkdir(parents=True)
    backup_path.touch()
    assert is_path_too_deep(backup_path, tmp_path, max_depth=MAX_PATH_DEPTH) is False


def test_apply_plan_renames_a_file_in_place(session, tmp_path):
    _write_pdf(tmp_path, "eski.pdf")
    pdf_files = [PdfFileMetadata(filename="eski.pdf", createdAt="2026-08-01")]
    plan = _plan(
        [_step(0, "2026-08", ["eski.pdf"], operation_type=OperationType.RENAME, new_file_names=["yeni.pdf"])]
    )

    transaction = apply_plan(session, plan, pdf_files, tmp_path)

    assert not (tmp_path / "eski.pdf").exists()
    assert (tmp_path / "yeni.pdf").exists()
    assert transaction.status == "committed"


def test_apply_plan_rolls_back_a_rename_by_restoring_the_old_name(session, tmp_path, monkeypatch):
    _write_pdf(tmp_path, "a.pdf")
    _write_pdf(tmp_path, "b.pdf")
    pdf_files = [
        PdfFileMetadata(filename="a.pdf", createdAt="2026-08-01"),
        PdfFileMetadata(filename="b.pdf", createdAt="2026-08-02"),
    ]
    plan = _plan(
        [
            _step(
                0,
                "2026-08",
                ["a.pdf", "b.pdf"],
                operation_type=OperationType.RENAME,
                new_file_names=["a2.pdf", "b2.pdf"],
            )
        ]
    )

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

    assert (tmp_path / "a.pdf").exists()  # eski ismine geri geldi
    assert not (tmp_path / "a2.pdf").exists()
    assert (tmp_path / "b.pdf").exists()  # hic yeniden adlandirilmadi


def test_apply_plan_rejects_cross_step_chained_renames_without_losing_data(session, tmp_path):
    # 2. red-team turu bulgusu (deneysel dogrulandi, HIGH): apply_plan
    # seviyesinde ucdan uca dogrulama - a.pdf->b.pdf (step 0) VE
    # b.pdf->c.pdf (step 1) ayni planda olursa, b.pdf'in orijinal
    # icerigi (bu testte ayirt edici bir icerikle yazilmis) sessizce
    # kaybolmamali - plan hicbir dosyaya dokunmadan reddedilmeli.
    (tmp_path / "a.pdf").write_bytes(b"A-icerik")
    (tmp_path / "b.pdf").write_bytes(b"B-ORIJINAL-ONEMLI-VERI")
    pdf_files = [
        PdfFileMetadata(filename="a.pdf", createdAt="2026-08-01"),
        PdfFileMetadata(filename="b.pdf", createdAt="2026-08-02"),
    ]
    plan = _plan(
        [
            _step(0, "2026-08", ["a.pdf"], operation_type=OperationType.RENAME, new_file_names=["b.pdf"]),
            _step(1, "2026-08", ["b.pdf"], operation_type=OperationType.RENAME, new_file_names=["c.pdf"]),
        ]
    )

    with pytest.raises(Exception):
        apply_plan(session, plan, pdf_files, tmp_path)

    # Hicbir dosyaya dokunulmamis olmali - b.pdf'in orijinal icerigi korunuyor.
    assert (tmp_path / "a.pdf").read_bytes() == b"A-icerik"
    assert (tmp_path / "b.pdf").read_bytes() == b"B-ORIJINAL-ONEMLI-VERI"
    assert not (tmp_path / "c.pdf").exists()


# Saga #304: MERGE operasyonu - N kaynak PDF -> 1 yeni birlesik PDF,
# kaynaklara dokunulmaz, rollback COPY semantigiyle (sadece hedefi sil).


def _merge_step(order: int, file_names: list[str], merged_file_name: str) -> PlanStep:
    return PlanStep(
        order=order,
        operationType=OperationType.MERGE,
        targetFolder="2026-08",
        affectedFileCount=len(file_names),
        fileNames=file_names,
        mergedFileName=merged_file_name,
    )


def test_apply_plan_merges_real_pdfs_into_one_file_with_the_correct_total_page_count(session, tmp_path):
    from pypdf import PdfReader

    _write_real_pdf(tmp_path, "a.pdf", 2)
    _write_real_pdf(tmp_path, "b.pdf", 3)
    pdf_files = [
        PdfFileMetadata(filename="a.pdf", createdAt="2026-08-01"),
        PdfFileMetadata(filename="b.pdf", createdAt="2026-08-02"),
    ]
    plan = _plan([_merge_step(0, ["a.pdf", "b.pdf"], "birlesik.pdf")])

    transaction = apply_plan(session, plan, pdf_files, tmp_path)

    merged_path = tmp_path / "birlesik.pdf"
    assert merged_path.exists()
    reader = PdfReader(str(merged_path))
    assert len(reader.pages) == 5
    assert transaction.status == "committed"
    assert len(transaction.operations) == 1
    assert transaction.operations[0].status == "completed"


def test_apply_plan_leaves_merge_sources_untouched(session, tmp_path):
    _write_real_pdf(tmp_path, "a.pdf", 1)
    _write_real_pdf(tmp_path, "b.pdf", 1)
    pdf_files = [
        PdfFileMetadata(filename="a.pdf", createdAt="2026-08-01"),
        PdfFileMetadata(filename="b.pdf", createdAt="2026-08-02"),
    ]
    plan = _plan([_merge_step(0, ["a.pdf", "b.pdf"], "birlesik.pdf")])

    apply_plan(session, plan, pdf_files, tmp_path)

    assert (tmp_path / "a.pdf").exists()
    assert (tmp_path / "b.pdf").exists()


def test_apply_plan_rolls_back_a_merge_by_deleting_the_merged_file_without_touching_sources(session, tmp_path):
    _write_real_pdf(tmp_path, "a.pdf", 1)
    _write_real_pdf(tmp_path, "b.pdf", 1)
    pdf_files = [
        PdfFileMetadata(filename="a.pdf", createdAt="2026-08-01"),
        PdfFileMetadata(filename="b.pdf", createdAt="2026-08-02"),
        PdfFileMetadata(filename="c.pdf", createdAt="2026-08-03"),
    ]
    plan = _plan(
        [
            _merge_step(0, ["a.pdf", "b.pdf"], "birlesik.pdf"),
            _step(1, "2026-08", ["c.pdf"]),  # c.pdf pdf_files'ta ama diskte yok - bu step basarisiz olur
        ]
    )

    with pytest.raises(PlanApplicationError):
        apply_plan(session, plan, pdf_files, tmp_path)

    assert not (tmp_path / "birlesik.pdf").exists()
    assert (tmp_path / "a.pdf").exists()
    assert (tmp_path / "b.pdf").exists()


def test_apply_plan_merge_leaves_no_temp_files_behind_on_success(session, tmp_path):
    # Red-team bulgusu (Saga #304): _forward_merge artik gecici dosyaya
    # yazip ATOMIK rename ile hedefe tasiyor - basarili bir merge sonrasi
    # klasorde SADECE birlesik.pdf, a.pdf, b.pdf kalmali, hicbir ".tmp"
    # artik dosya birakilmamali.
    _write_real_pdf(tmp_path, "a.pdf", 1)
    _write_real_pdf(tmp_path, "b.pdf", 1)
    pdf_files = [
        PdfFileMetadata(filename="a.pdf", createdAt="2026-08-01"),
        PdfFileMetadata(filename="b.pdf", createdAt="2026-08-02"),
    ]
    plan = _plan([_merge_step(0, ["a.pdf", "b.pdf"], "birlesik.pdf")])

    apply_plan(session, plan, pdf_files, tmp_path)

    remaining = {p.name for p in tmp_path.iterdir()}
    assert remaining == {"a.pdf", "b.pdf", "birlesik.pdf"}


def test_forward_merge_leaves_no_partial_file_at_destination_when_write_fails(tmp_path, monkeypatch):
    # _forward_merge'i dogrudan cagirip PdfWriter.write'in yazma sirasinda
    # basarisiz oldugunu simule ediyoruz (disk dolu / izin hatasi benzeri).
    # Gecici-dosya + atomik-rename deseni sayesinde gercek destination_path'te
    # HICBIR yarim/bozuk dosya kalmamali.
    from pypdf import PdfWriter

    from backend.orchestrator import _forward_merge

    _write_real_pdf(tmp_path, "a.pdf", 1)
    _write_real_pdf(tmp_path, "b.pdf", 1)
    destination = tmp_path / "birlesik.pdf"

    def _boom(self, path):
        raise OSError("simulated disk full")

    monkeypatch.setattr(PdfWriter, "write", _boom)

    with pytest.raises(OSError):
        _forward_merge([tmp_path / "a.pdf", tmp_path / "b.pdf"], destination)

    assert not destination.exists()
    # Hicbir ".tmp" artik dosyasi da kalmamis olmali.
    leftovers = [p for p in tmp_path.iterdir() if p.name not in {"a.pdf", "b.pdf"}]
    assert leftovers == []


# Saga #305: SPLIT operasyonu - 1 kaynak PDF -> N yeni tek-sayfalik PDF,
# kaynaga dokunulmaz, rollback COPY semantigiyle (her cikti icin sadece
# hedefi sil).


def _split_step(order: int, file_name: str) -> PlanStep:
    return PlanStep(
        order=order,
        operationType=OperationType.SPLIT,
        targetFolder="2026-08",
        affectedFileCount=1,
        fileNames=[file_name],
    )


def test_apply_plan_splits_a_real_pdf_into_one_file_per_page(session, tmp_path):
    from pypdf import PdfReader

    _write_real_pdf(tmp_path, "rapor.pdf", 3)
    pdf_files = [PdfFileMetadata(filename="rapor.pdf", createdAt="2026-08-01")]
    plan = _plan([_split_step(0, "rapor.pdf")])

    transaction = apply_plan(session, plan, pdf_files, tmp_path)

    for page_number in (1, 2, 3):
        output_path = tmp_path / f"rapor_{page_number}.pdf"
        assert output_path.exists()
        reader = PdfReader(str(output_path))
        assert len(reader.pages) == 1
    assert transaction.status == "committed"
    assert len(transaction.operations) == 3
    assert all(op.status == "completed" for op in transaction.operations)


def test_apply_plan_leaves_split_source_untouched(session, tmp_path):
    _write_real_pdf(tmp_path, "rapor.pdf", 2)
    pdf_files = [PdfFileMetadata(filename="rapor.pdf", createdAt="2026-08-01")]
    plan = _plan([_split_step(0, "rapor.pdf")])

    apply_plan(session, plan, pdf_files, tmp_path)

    assert (tmp_path / "rapor.pdf").exists()


def test_apply_plan_rejects_split_when_output_file_name_already_exists(session, tmp_path):
    _write_real_pdf(tmp_path, "rapor.pdf", 3)
    # rapor_2.pdf plan'in BILMEDIGI, onceden var olan ilgisiz bir dosya -
    # cikti adiyla CAKISIYOR.
    (tmp_path / "rapor_2.pdf").write_bytes(b"%PDF-1.4 onceden-var")
    pdf_files = [PdfFileMetadata(filename="rapor.pdf", createdAt="2026-08-01")]
    plan = _plan([_split_step(0, "rapor.pdf")])

    with pytest.raises(PlanApplicationError):
        apply_plan(session, plan, pdf_files, tmp_path)

    # rapor_1.pdf (cakismadan ONCE yazilmis olabilecek) rollback ile
    # silinmis olmali - hicbir SPLIT ciktisi geride kalmamali.
    assert not (tmp_path / "rapor_1.pdf").exists()
    # Cakisan onceden-var-olan dosya DOKUNULMADAN kalmali (uzerine yazilmadi).
    assert (tmp_path / "rapor_2.pdf").read_bytes() == b"%PDF-1.4 onceden-var"
    assert not (tmp_path / "rapor_3.pdf").exists()
    assert (tmp_path / "rapor.pdf").exists()


def test_apply_plan_rejects_split_of_a_zero_page_pdf(session, tmp_path):
    _write_real_pdf(tmp_path, "bos.pdf", 0)
    pdf_files = [PdfFileMetadata(filename="bos.pdf", createdAt="2026-08-01")]
    plan = _plan([_split_step(0, "bos.pdf")])

    with pytest.raises(PlanApplicationError):
        apply_plan(session, plan, pdf_files, tmp_path)


def test_apply_plan_rolls_back_split_outputs_when_a_later_step_fails(session, tmp_path):
    _write_real_pdf(tmp_path, "rapor.pdf", 2)
    pdf_files = [
        PdfFileMetadata(filename="rapor.pdf", createdAt="2026-08-01"),
        PdfFileMetadata(filename="c.pdf", createdAt="2026-08-03"),
    ]
    plan = _plan(
        [
            _split_step(0, "rapor.pdf"),
            _step(1, "2026-08", ["c.pdf"]),  # c.pdf pdf_files'ta ama diskte yok - basarisiz olur
        ]
    )

    with pytest.raises(PlanApplicationError):
        apply_plan(session, plan, pdf_files, tmp_path)

    assert not (tmp_path / "rapor_1.pdf").exists()
    assert not (tmp_path / "rapor_2.pdf").exists()
    assert (tmp_path / "rapor.pdf").exists()


# OCR operasyonu (red step, Saga: apply_plan henuz OperationType.OCR'i
# desteklemiyor, backend.orchestrator.ocr_pdf_file diye bir isim de
# import edilmis degil). Bu testler simdilik KIRMIZI kalmali.


def test_apply_plan_runs_ocr_on_a_pdf_inside_allowed_root_without_moving_it(session, tmp_path, monkeypatch):
    _write_pdf(tmp_path, "a.pdf")
    pdf_files = [PdfFileMetadata(filename="a.pdf", createdAt="2026-08-01")]
    plan = _plan([_step(0, "2026-08", ["a.pdf"], operation_type=OperationType.OCR)])

    calls: list[Path] = []

    def fake_ocr_pdf_file(pdf_path: Path) -> list[str]:
        calls.append(pdf_path)
        return ["metin"]

    monkeypatch.setattr("backend.orchestrator.ocr_pdf_file", fake_ocr_pdf_file)

    transaction = apply_plan(session, plan, pdf_files, tmp_path)

    assert calls == [tmp_path / "a.pdf"]
    assert (tmp_path / "a.pdf").exists()
    assert transaction.status == "committed"
    assert len(transaction.operations) == 0


def test_apply_plan_rejects_ocr_of_a_path_outside_allowed_root(session, tmp_path, monkeypatch):
    # PdfFileMetadata.filename kendi validator'unda ayrac icermez, bu yuzden
    # dogrudan bir path-traversal stringi ifade edilemez - ama tek segmentlik
    # ".." (Saga #272'deki mevcut testlerin kullandigi teknikle AYNI) allowed_root
    # disina cikar. apply_plan'in OCR adiminin da diger operationType'lar
    # (MERGE/SPLIT/DELETE) gibi is_path_allowed/validate_plan_paths uzerinden
    # kaynagi dogrulamasi gerektigini, mock OCR fonksiyonunun HIC
    # cagrilmadigini dogrulayarak test ediyoruz.
    pdf_files = [PdfFileMetadata(filename="..", createdAt="2026-08-01")]
    plan = _plan([_step(0, "2026-08", [".."], operation_type=OperationType.OCR)])

    calls: list[Path] = []

    def fake_ocr_pdf_file(pdf_path: Path) -> list[str]:
        calls.append(pdf_path)
        return ["metin"]

    monkeypatch.setattr("backend.orchestrator.ocr_pdf_file", fake_ocr_pdf_file)

    # Red-team notu (Saga #307): burada bilerek genel Exception yerine
    # PathWhitelistError bekleniyor - guvenlik testinin, gercek path
    # dogrulamasindan farkli bir hatayla (ör. bir yazim hatasindan gelen
    # AttributeError/KeyError) yanlislikla "yesil" gecmesini engellemek icin.
    with pytest.raises(PathWhitelistError):
        apply_plan(session, plan, pdf_files, tmp_path)

    assert calls == []


def test_recover_incomplete_transactions_marks_physically_moved_files_as_completed(session, tmp_path):
    # Saga #286: shutil.move basarili oldu ama surec operation.status =
    # "completed" + commit'ten ONCE coktu senaryosunu simule eder - kayit
    # "pending" kalir, dosya fiziksel olarak hedefte durur.
    target_dir = tmp_path / "2026-08"
    target_dir.mkdir()
    (target_dir / "a.pdf").write_bytes(b"%PDF-1.4 fake")

    from backend.file_operations import create_transaction, record_file_operation

    transaction = create_transaction(session)
    record_file_operation(
        session,
        transaction,
        operation_type="Taşı",
        source_path=str(tmp_path / "a.pdf"),
        destination_path=str(target_dir / "a.pdf"),
        backup_path=str(tmp_path / "a.pdf"),
    )
    transaction.status = "pending"
    session.commit()

    recovered = recover_incomplete_transactions(session)

    assert len(recovered) == 1
    assert recovered[0].status == "committed"
    assert recovered[0].operations[0].status == "completed"


def test_recover_incomplete_transactions_marks_never_moved_files_as_rolled_back(session, tmp_path):
    from backend.file_operations import create_transaction, record_file_operation

    transaction = create_transaction(session)
    record_file_operation(
        session,
        transaction,
        operation_type="Taşı",
        source_path=str(tmp_path / "a.pdf"),
        destination_path=str(tmp_path / "2026-08" / "a.pdf"),  # hiç oluşmadı
        backup_path=str(tmp_path / "a.pdf"),
    )
    transaction.status = "pending"
    session.commit()

    recovered = recover_incomplete_transactions(session)

    assert len(recovered) == 1
    assert recovered[0].status == "rolled_back"
    assert recovered[0].operations[0].status == "rolled_back"


def test_recover_incomplete_transactions_reverifies_stale_completed_operations_in_a_pending_transaction(session, tmp_path):
    # Saga #286 red-team bulgusu: apply_plan'in rollback except bloğu bir
    # operasyonu bellek-içi "completed"->"rolled_back"e cevirdikten SONRA
    # ama nihai session.commit()'ten ONCE surec cokerse, DB'de o operasyon
    # hala "completed" gorunur - ama dosya fiziksel olarak zaten geri
    # tasinmis olabilir. Sadece status=="pending" olanlari kontrol etmek
    # bu operasyonu sonsuza dek yanlis etiketli birakirdi.
    from backend.file_operations import create_transaction, record_file_operation

    transaction = create_transaction(session)
    stale_completed_op = record_file_operation(
        session,
        transaction,
        operation_type="Taşı",
        source_path=str(tmp_path / "a.pdf"),
        destination_path=str(tmp_path / "2026-08" / "a.pdf"),  # fiziksel olarak geri tasindi, artik yok
        backup_path=str(tmp_path / "a.pdf"),
    )
    stale_completed_op.status = "completed"  # DB'de hala "completed", ama dosya orada degil
    still_pending_op = record_file_operation(
        session,
        transaction,
        operation_type="Taşı",
        source_path=str(tmp_path / "b.pdf"),
        destination_path=str(tmp_path / "2026-08" / "b.pdf"),  # hic tasinmadi
        backup_path=str(tmp_path / "b.pdf"),
    )
    transaction.status = "pending"
    session.commit()

    recovered = recover_incomplete_transactions(session)

    assert len(recovered) == 1
    refreshed_stale_op = next(op for op in recovered[0].operations if op.id == stale_completed_op.id)
    refreshed_pending_op = next(op for op in recovered[0].operations if op.id == still_pending_op.id)
    assert refreshed_stale_op.status == "rolled_back"
    assert refreshed_pending_op.status == "rolled_back"
    assert recovered[0].status == "rolled_back"


def test_recover_incomplete_transactions_ignores_already_terminal_transactions(session, tmp_path):
    from backend.file_operations import create_transaction, record_file_operation

    transaction = create_transaction(session)
    record_file_operation(
        session,
        transaction,
        operation_type="Taşı",
        source_path=str(tmp_path / "a.pdf"),
        destination_path=str(tmp_path / "2026-08" / "a.pdf"),
        backup_path=str(tmp_path / "a.pdf"),
    )
    transaction.status = "committed"
    session.commit()

    recovered = recover_incomplete_transactions(session)

    assert recovered == []


def test_revert_transaction_moves_a_completed_move_back_to_its_original_location(session, tmp_path):
    _write_pdf(tmp_path, "a.pdf")
    pdf_files = [PdfFileMetadata(filename="a.pdf", createdAt="2026-08-01")]
    plan = _plan([_step(0, "2026-08", ["a.pdf"])])
    transaction = apply_plan(session, plan, pdf_files, tmp_path)

    reverted = revert_transaction(session, transaction, tmp_path)

    assert (tmp_path / "a.pdf").exists()
    assert not (tmp_path / "2026-08" / "a.pdf").exists()
    assert reverted.status == "reverted"
    assert all(op.status == "rolled_back" for op in reverted.operations)


def test_revert_transaction_deletes_the_copy_and_leaves_the_original_intact(session, tmp_path):
    _write_pdf(tmp_path, "a.pdf")
    pdf_files = [PdfFileMetadata(filename="a.pdf", createdAt="2026-08-01")]
    plan = _plan([_step(0, "2026-08", ["a.pdf"], operation_type=OperationType.COPY)])
    transaction = apply_plan(session, plan, pdf_files, tmp_path)

    revert_transaction(session, transaction, tmp_path)

    assert (tmp_path / "a.pdf").exists()
    assert not (tmp_path / "2026-08" / "a.pdf").exists()


def test_revert_transaction_restores_a_deleted_file_from_its_backup(session, tmp_path):
    _write_pdf(tmp_path, "a.pdf")
    pdf_files = [PdfFileMetadata(filename="a.pdf", createdAt="2026-08-01")]
    plan = _plan([_step(0, "2026-08", ["a.pdf"], operation_type=OperationType.DELETE)])
    transaction = apply_plan(session, plan, pdf_files, tmp_path)
    assert not (tmp_path / "a.pdf").exists()

    revert_transaction(session, transaction, tmp_path)

    assert (tmp_path / "a.pdf").exists()


def test_revert_transaction_restores_the_old_name_of_a_renamed_file(session, tmp_path):
    _write_pdf(tmp_path, "a.pdf")
    pdf_files = [PdfFileMetadata(filename="a.pdf", createdAt="2026-08-01")]
    plan = _plan([_step(0, "2026-08", ["a.pdf"], operation_type=OperationType.RENAME, new_file_names=["b.pdf"])])
    transaction = apply_plan(session, plan, pdf_files, tmp_path)

    revert_transaction(session, transaction, tmp_path)

    assert (tmp_path / "a.pdf").exists()
    assert not (tmp_path / "b.pdf").exists()


def test_revert_transaction_reverts_multiple_operations_in_reverse_order(session, tmp_path, monkeypatch):
    _write_pdf(tmp_path, "a.pdf")
    _write_pdf(tmp_path, "b.pdf")
    pdf_files = [
        PdfFileMetadata(filename="a.pdf", createdAt="2026-08-01"),
        PdfFileMetadata(filename="b.pdf", createdAt="2026-08-02"),
    ]
    plan = _plan([_step(0, "2026-08", ["a.pdf", "b.pdf"])])
    transaction = apply_plan(session, plan, pdf_files, tmp_path)

    revert_order: list[str] = []
    import backend.orchestrator as orchestrator_module

    original = orchestrator_module._rollback_move

    def _tracking_rollback_move(destination_path, backup_path):
        revert_order.append(Path(destination_path).name)
        original(destination_path, backup_path)

    monkeypatch.setattr(orchestrator_module, "_rollback_move", _tracking_rollback_move)
    monkeypatch.setitem(orchestrator_module._ROLLBACK_OPERATIONS, OperationType.MOVE, _tracking_rollback_move)

    revert_transaction(session, transaction, tmp_path)

    assert revert_order == ["b.pdf", "a.pdf"]


def test_revert_transaction_rejects_a_transaction_that_is_not_committed(session, tmp_path):
    _write_pdf(tmp_path, "a.pdf")
    pdf_files = [PdfFileMetadata(filename="a.pdf", createdAt="2026-08-01")]
    plan = _plan([_step(0, "2026-08", ["a.pdf"])])
    transaction = apply_plan(session, plan, pdf_files, tmp_path)
    transaction.status = "reverted"
    session.commit()

    with pytest.raises(TransactionRevertError):
        revert_transaction(session, transaction, tmp_path)

    # Reddedilince hiçbir dosyaya dokunulmaz — dosya hâlâ apply_plan'ın
    # bıraktığı hedef klasörde, kök klasöre GERİ TAŞINMAMIŞ olmalı.
    assert not (tmp_path / "a.pdf").exists()
    assert (tmp_path / "2026-08" / "a.pdf").exists()


def test_revert_transaction_marks_revert_failed_and_raises_when_a_step_cannot_be_reverted(session, tmp_path):
    _write_pdf(tmp_path, "a.pdf")
    _write_pdf(tmp_path, "b.pdf")
    pdf_files = [
        PdfFileMetadata(filename="a.pdf", createdAt="2026-08-01"),
        PdfFileMetadata(filename="b.pdf", createdAt="2026-08-02"),
    ]
    plan = _plan([_step(0, "2026-08", ["a.pdf", "b.pdf"])])
    transaction = apply_plan(session, plan, pdf_files, tmp_path)
    # b.pdf'in hedefteki kopyasını rollback'ten ÖNCE kaldırıp yerine bir
    # KLASÖR koyuyoruz — shutil.move hedef zaten var olan bir klasörse
    # OSError fırlatır, bu da rollback'in KENDİSİNİN başarısız olduğu
    # senaryoyu gerçekçi şekilde tetikler.
    b_destination = tmp_path / "2026-08" / "b.pdf"
    b_destination.unlink()
    b_destination.mkdir()
    # b.pdf'in eski konumunda da bir dosya bırakıyoruz ki shutil.move hedefi
    # zaten dolu bir konuma taşımaya çalışsın (Windows'ta bu OSError verir).
    _write_pdf(tmp_path, "b.pdf")

    with pytest.raises(TransactionRevertError):
        revert_transaction(session, transaction, tmp_path)

    assert transaction.status == "revert_failed"
    # a.pdf başarıyla geri alındı (b.pdf'ten SONRA işlendiği için ters
    # sırada a.pdf İLK geri alınır) — kısmi ilerleme kaybolmadı.
    assert (tmp_path / "a.pdf").exists()


def test_revert_transaction_ignores_operations_outside_the_allowed_root(session, tmp_path):
    _write_pdf(tmp_path, "a.pdf")
    pdf_files = [PdfFileMetadata(filename="a.pdf", createdAt="2026-08-01")]
    plan = _plan([_step(0, "2026-08", ["a.pdf"])])
    transaction = apply_plan(session, plan, pdf_files, tmp_path)
    # DB'deki kaydı, allowed_root DIŞINDA bir yeri işaret edecek şekilde
    # elle bozuyoruz (Saga #293 S4: savunma derinliği senaryosu).
    outside_root = tmp_path.parent / "baska-bir-klasor"
    transaction.operations[0].destination_path = str(outside_root / "a.pdf")
    session.commit()

    with pytest.raises(TransactionRevertError):
        revert_transaction(session, transaction, tmp_path)

    assert transaction.status == "revert_failed"
    assert not outside_root.exists()


def _apply_a_delete_plan(session, tmp_path, filename: str = "a.pdf"):
    _write_pdf(tmp_path, filename)
    pdf_files = [PdfFileMetadata(filename=filename, createdAt="2026-08-01")]
    plan = _plan([_step(0, "2026-08", [filename], operation_type=OperationType.DELETE)])
    return apply_plan(session, plan, pdf_files, tmp_path)


def test_purge_expired_delete_backups_deletes_the_backup_folder_and_marks_the_transaction_purged(session, tmp_path):
    transaction = _apply_a_delete_plan(session, tmp_path)
    backup_dir = tmp_path / ".windows-ai-files-backup" / str(transaction.id)
    assert backup_dir.exists()
    transaction.created_at = dt.datetime.utcnow() - dt.timedelta(days=31)
    session.commit()

    purged_ids = purge_expired_delete_backups(session, tmp_path, older_than_days=30)

    assert purged_ids == [transaction.id]
    assert not backup_dir.exists()
    assert transaction.status == "backup_purged"


def test_purge_expired_delete_backups_ignores_transactions_newer_than_the_cutoff(session, tmp_path):
    transaction = _apply_a_delete_plan(session, tmp_path)
    backup_dir = tmp_path / ".windows-ai-files-backup" / str(transaction.id)

    purged_ids = purge_expired_delete_backups(session, tmp_path, older_than_days=30)

    assert purged_ids == []
    assert backup_dir.exists()
    assert transaction.status == "committed"


def test_purge_expired_delete_backups_skips_mixed_operation_transactions(session, tmp_path):
    _write_pdf(tmp_path, "a.pdf")
    _write_pdf(tmp_path, "b.pdf")
    pdf_files = [
        PdfFileMetadata(filename="a.pdf", createdAt="2026-08-01"),
        PdfFileMetadata(filename="b.pdf", createdAt="2026-08-02"),
    ]
    plan = _plan(
        [
            _step(0, "2026-08", ["a.pdf"], operation_type=OperationType.DELETE),
            _step(1, "2026-08", ["b.pdf"], operation_type=OperationType.MOVE),
        ]
    )
    transaction = apply_plan(session, plan, pdf_files, tmp_path)
    backup_dir = tmp_path / ".windows-ai-files-backup" / str(transaction.id)
    assert backup_dir.exists()
    transaction.created_at = dt.datetime.utcnow() - dt.timedelta(days=31)
    session.commit()

    purged_ids = purge_expired_delete_backups(session, tmp_path, older_than_days=30)

    assert purged_ids == []
    assert backup_dir.exists()
    assert transaction.status == "committed"


def test_purge_expired_delete_backups_does_not_touch_a_transaction_belonging_to_a_different_root(
    session, tmp_path
):
    # Red-team bulgusu (HIGH): `Transaction` hangi `allowed_root`a ait
    # olduğunu bilmiyor — DB sorgusu TÜM köklerdeki committed transaction'ları
    # döndürür. Başka bir köke ait bir transaction için bu fonksiyona YANLIŞ
    # bir `allowed_root` verilirse (çok-kök senaryosu), o transaction'a
    # DOKUNULMAMALI (durumu `"committed"` kalmalı, backup'ı olduğu gibi
    # durmalı) — aksi halde hiçbir şey fiziksel olarak silinmeden geri
    # alınamaz hale gelirdi.
    other_root = tmp_path / "baska-bir-kok"
    other_root.mkdir()
    transaction = _apply_a_delete_plan(session, other_root)
    transaction.created_at = dt.datetime.utcnow() - dt.timedelta(days=31)
    session.commit()

    wrong_root = tmp_path / "yanlis-kok"
    wrong_root.mkdir()
    purged_ids = purge_expired_delete_backups(session, wrong_root, older_than_days=30)

    assert purged_ids == []
    assert transaction.status == "committed"
    assert (other_root / ".windows-ai-files-backup" / str(transaction.id)).exists()


def test_purge_expired_delete_backups_result_is_rejected_by_revert_transaction_without_any_code_change(
    session, tmp_path
):
    # Saga #300'ün asıl güvenlik gerekçesi: purge edilmiş bir transaction
    # `revert_transaction`e verilirse, `_rollback_completed_operations`in
    # "hedef fiziksel olarak yoksa zaten geri alınmış" kısayolu SESSİZCE
    # "başarılı" görünürdü — `"backup_purged"` durumu bunu `revert_transaction`in
    # ZATEN VAR OLAN committed-only guard'ıyla (Saga #293) engelliyor.
    transaction = _apply_a_delete_plan(session, tmp_path)
    transaction.created_at = dt.datetime.utcnow() - dt.timedelta(days=31)
    session.commit()
    purge_expired_delete_backups(session, tmp_path, older_than_days=30)

    with pytest.raises(TransactionRevertError):
        revert_transaction(session, transaction, tmp_path)

    # Reddedilince hiçbir "başarılı geri alma" görünümü yok, dosya
    # gerçekten kaybolmuş durumda kalıyor (bu testin amacı budur).
    assert not (tmp_path / "a.pdf").exists()
