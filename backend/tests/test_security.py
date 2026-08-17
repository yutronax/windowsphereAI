from pathlib import Path

import pytest

from backend.models import DateSource, PdfFileMetadata, PlanSkeleton, PlanStep, OperationType, SortOrder
from backend.security import (
    MAX_PATH_DEPTH,
    PathWhitelistError,
    is_path_allowed,
    is_path_too_deep,
    is_system_protected,
    validate_plan_paths,
    validate_rename_destinations,
)


def test_is_path_allowed_true_for_path_inside_root(tmp_path):
    root = tmp_path
    inside = root / "2026-08" / "a.pdf"

    assert is_path_allowed(inside, root) is True


def test_is_path_allowed_true_for_root_itself(tmp_path):
    assert is_path_allowed(tmp_path, tmp_path) is True


def test_is_path_allowed_false_for_traversal_outside_root(tmp_path):
    outside = tmp_path / ".." / "sibling" / "evil.pdf"

    assert is_path_allowed(outside, tmp_path) is False


def test_is_path_allowed_false_for_sibling_directory_with_shared_prefix(tmp_path):
    root = tmp_path / "allowed"
    root.mkdir()
    sibling = tmp_path / "allowed-but-not-really" / "evil.pdf"

    assert is_path_allowed(sibling, root) is False


def _plan(target_folder: str = "2026-08") -> PlanSkeleton:
    return PlanSkeleton(
        steps=[PlanStep(order=0, operationType=OperationType.MOVE, targetFolder=target_folder, affectedFileCount=1, fileNames=["a.pdf"])],
        dateSource=DateSource.CREATED_AT,
        sortOrder=SortOrder.ASCENDING,
    )


def test_validate_plan_paths_passes_for_valid_plan(tmp_path):
    pdf_files = [PdfFileMetadata(filename="a.pdf", createdAt="2026-08-01")]

    validate_plan_paths(_plan(), pdf_files, tmp_path)


def test_validate_plan_paths_rejects_entire_plan_when_one_source_file_escapes_root(tmp_path):
    # Saga #272: filename artık Pydantic seviyesinde path separator
    # içeremiyor (models.py:filename_has_no_path_separators), ama tek
    # segmentlik ".." hâlâ ayraçsız geçerli bir string — whitelist'in bunu
    # runtime'da yakaladığını doğruluyoruz.
    pdf_files = [
        PdfFileMetadata(filename="a.pdf", createdAt="2026-08-01"),
        PdfFileMetadata(filename="..", createdAt="2026-08-01"),
    ]

    with pytest.raises(PathWhitelistError):
        validate_plan_paths(_plan(), pdf_files, tmp_path)


def test_path_whitelist_error_carries_structured_fields(tmp_path):
    pdf_files = [PdfFileMetadata(filename="..", createdAt="2026-08-01")]

    with pytest.raises(PathWhitelistError) as exc_info:
        validate_plan_paths(_plan(), pdf_files, tmp_path)

    error = exc_info.value
    assert error.description == "Kaynak dosya"
    assert error.reason == "izin verilen kök dışında"
    assert error.allowed_root == str(tmp_path)
    assert str(tmp_path.parent) in error.offending_path
    assert str(error) == f"{error.description} {error.reason}: {error.offending_path}"


def test_validate_plan_paths_passes_for_empty_steps_and_no_pdf_files(tmp_path):
    empty_plan = PlanSkeleton(steps=[], dateSource=DateSource.CREATED_AT, sortOrder=SortOrder.ASCENDING)

    validate_plan_paths(empty_plan, [], tmp_path)


def test_validate_plan_paths_rejects_when_target_folder_escapes_root(tmp_path):
    # PlanStep.targetFolder normalde TARGET_FOLDER_PATTERN (YYYY-MM) ile
    # kısıtlı olduğu için bu dal API üzerinden tetiklenemez; regex ileride
    # gevşetilirse whitelist'in hâlâ koruma sağladığını doğrulamak için
    # model_construct ile alan doğrulamasını atlıyoruz.
    step = PlanStep.model_construct(order=0, operationType=OperationType.MOVE, targetFolder=r"..\..\evil", affectedFileCount=1)
    plan = PlanSkeleton.model_construct(steps=[step], dateSource=DateSource.CREATED_AT, sortOrder=SortOrder.ASCENDING)

    with pytest.raises(PathWhitelistError):
        validate_plan_paths(plan, [], tmp_path)


def test_is_path_too_deep_false_at_exactly_max_depth(tmp_path):
    path = tmp_path
    for i in range(MAX_PATH_DEPTH):
        path = path / f"level{i}"

    assert is_path_too_deep(path, tmp_path) is False


def test_is_path_too_deep_true_one_level_beyond_max_depth(tmp_path):
    path = tmp_path
    for i in range(MAX_PATH_DEPTH + 1):
        path = path / f"level{i}"

    assert is_path_too_deep(path, tmp_path) is True


def test_is_system_protected_true_for_windows_directory(monkeypatch):
    monkeypatch.setenv("WINDIR", r"C:\Windows")

    assert is_system_protected(Path(r"C:\Windows\System32\evil.pdf")) is True


def test_is_system_protected_true_for_programdata_directory(monkeypatch):
    monkeypatch.setenv("ProgramData", r"C:\ProgramData")

    assert is_system_protected(Path(r"C:\ProgramData\evil.pdf")) is True


def test_is_system_protected_false_for_appdata_directory():
    # %APPDATA%/%LOCALAPPDATA% kasıtlı olarak korunan kök listesinde değil
    # (kullanıcı verisi de barındırabilir, ör. pytest'in kendi tmp_path'i);
    # whitelist kökü (`is_path_allowed`) zaten dışına çıkışı engelliyor.
    assert is_system_protected(Path(r"C:\Users\yusuf\AppData\Local\Temp\a.pdf")) is False


def test_is_system_protected_false_for_ordinary_user_directory():
    assert is_system_protected(Path(r"C:\Users\yusuf\Documents\a.pdf")) is False


def test_validate_plan_paths_rejects_entire_plan_when_source_file_path_is_too_deep(tmp_path):
    # filename artık şema seviyesinde path separator içeremediği için (Saga
    # #272 red-team bulgusu, models.py:filename_has_no_path_separators) bu
    # dal API üzerinden tetiklenemez; whitelist'in hâlâ derinlik koruması
    # sağladığını doğrulamak için model_construct ile şema doğrulamasını
    # atlıyoruz (bkz. test_validate_plan_paths_rejects_when_target_folder_escapes_root
    # ile aynı pattern).
    deep_filename = "\\".join(f"level{i}" for i in range(MAX_PATH_DEPTH + 1)) + "\\evil.pdf"
    pdf_files = [
        PdfFileMetadata(filename="a.pdf", createdAt="2026-08-01"),
        PdfFileMetadata.model_construct(filename=deep_filename, createdAt="2026-08-01"),
    ]

    with pytest.raises(PathWhitelistError):
        validate_plan_paths(_plan(), pdf_files, tmp_path)


def _rename_plan(new_file_name: str) -> PlanSkeleton:
    step = PlanStep(
        order=0,
        operationType=OperationType.RENAME,
        targetFolder="2026-08",
        affectedFileCount=1,
        fileNames=["kaynak.pdf"],
        newFileNames=[new_file_name],
    )
    return PlanSkeleton(steps=[step], dateSource=DateSource.CREATED_AT, sortOrder=SortOrder.ASCENDING)


def test_validate_rename_destinations_rejects_collision_with_an_existing_unrelated_file(tmp_path):
    # Red-team bulgusu (Saga #290, HIGH severity, deneysel dogrulandi):
    # shutil.move hedefte zaten var olan bir dosyayi sessizce uzerine yazar.
    (tmp_path / "kaynak.pdf").write_bytes(b"%PDF-1.4 fake")
    (tmp_path / "onemli_dosya.pdf").write_bytes(b"%PDF-1.4 onemli veri")
    pdf_files = [PdfFileMetadata(filename="kaynak.pdf", createdAt="2026-08-01")]

    with pytest.raises(PathWhitelistError):
        validate_plan_paths(_rename_plan("onemli_dosya.pdf"), pdf_files, tmp_path)


def test_validate_rename_destinations_allows_a_target_name_that_is_itself_a_known_pdf_file(tmp_path):
    # Hedef isim planin bildigi (pdf_files'taki) bir dosyaysa - ornegin o
    # dosya da planin baska bir yerinde ele aliniyorsa - engellenmemeli.
    (tmp_path / "kaynak.pdf").write_bytes(b"%PDF-1.4 fake")
    (tmp_path / "b.pdf").write_bytes(b"%PDF-1.4 fake")
    pdf_files = [
        PdfFileMetadata(filename="kaynak.pdf", createdAt="2026-08-01"),
        PdfFileMetadata(filename="b.pdf", createdAt="2026-08-02"),
    ]

    validate_rename_destinations(_rename_plan("b.pdf"), pdf_files, tmp_path)


def test_validate_rename_destinations_passes_when_target_name_does_not_exist_yet(tmp_path):
    pdf_files = [PdfFileMetadata(filename="kaynak.pdf", createdAt="2026-08-01")]

    validate_rename_destinations(_rename_plan("hic-olmayan.pdf"), pdf_files, tmp_path)


def test_validate_rename_destinations_rejects_cross_step_chained_renames(tmp_path):
    # 2. red-team turu bulgusu (deneysel dogrulandi, HIGH): step 0
    # a.pdf->b.pdf, step 1 b.pdf->c.pdf - b.pdf hem bir RENAME'in hedefi
    # hem baska bir RENAME'in kaynagi. Sira ne olursa olsun, b.pdf'in
    # orijinal icerigi sessizce kaybolur (apply_plan uctan uca test
    # edilerek kanitlandi). Plan genelinde bu artik tamamen yasak.
    step0 = PlanStep(
        order=0,
        operationType=OperationType.RENAME,
        targetFolder="2026-08",
        affectedFileCount=1,
        fileNames=["a.pdf"],
        newFileNames=["b.pdf"],
    )
    step1 = PlanStep(
        order=1,
        operationType=OperationType.RENAME,
        targetFolder="2026-08",
        affectedFileCount=1,
        fileNames=["b.pdf"],
        newFileNames=["c.pdf"],
    )
    plan = PlanSkeleton(steps=[step0, step1], dateSource=DateSource.CREATED_AT, sortOrder=SortOrder.ASCENDING)
    pdf_files = [
        PdfFileMetadata(filename="a.pdf", createdAt="2026-08-01"),
        PdfFileMetadata(filename="b.pdf", createdAt="2026-08-02"),
    ]

    with pytest.raises(PathWhitelistError):
        validate_plan_paths(plan, pdf_files, tmp_path)


def test_validate_rename_destinations_rejects_case_variant_cross_step_chained_renames(tmp_path):
    # 3. red-team turu bulgusu (deneysel dogrulandi, HIGH): zincir tespiti
    # ilk halinde case-sensitive'ti - a.pdf->B.PDF (step 0) ve b.pdf->c.pdf
    # (step 1) Windows'ta AYNI zincir olmasina ragmen (B.PDF == b.pdf)
    # yakalanmiyordu.
    step0 = PlanStep(
        order=0,
        operationType=OperationType.RENAME,
        targetFolder="2026-08",
        affectedFileCount=1,
        fileNames=["a.pdf"],
        newFileNames=["B.PDF"],
    )
    step1 = PlanStep(
        order=1,
        operationType=OperationType.RENAME,
        targetFolder="2026-08",
        affectedFileCount=1,
        fileNames=["b.pdf"],
        newFileNames=["c.pdf"],
    )
    plan = PlanSkeleton(steps=[step0, step1], dateSource=DateSource.CREATED_AT, sortOrder=SortOrder.ASCENDING)
    pdf_files = [
        PdfFileMetadata(filename="a.pdf", createdAt="2026-08-01"),
        PdfFileMetadata(filename="b.pdf", createdAt="2026-08-02"),
    ]

    with pytest.raises(PathWhitelistError):
        validate_plan_paths(plan, pdf_files, tmp_path)


def test_validate_rename_destinations_allows_a_case_only_self_rename(tmp_path):
    # 3. red-team turu bulgusu: kaynak.pdf -> KAYNAK.pdf (ayni dosyanin
    # sadece harf buyuklugu degisikligi) MESRU bir tek-dosya islemidir,
    # "zincir" DEGILDIR - reddedilmemeli.
    (tmp_path / "kaynak.pdf").write_bytes(b"%PDF-1.4 fake")
    pdf_files = [PdfFileMetadata(filename="kaynak.pdf", createdAt="2026-08-01")]

    validate_plan_paths(_rename_plan("KAYNAK.pdf"), pdf_files, tmp_path)
