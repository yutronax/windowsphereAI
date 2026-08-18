import pytest
from pydantic import ValidationError

from backend.models import OperationType, PlanStep


def _step(**overrides):
    defaults = {
        "order": 0,
        "operationType": OperationType.MOVE,
        "targetFolder": "2026-08",
        "affectedFileCount": 1,
        "fileNames": ["a.pdf"],
    }
    defaults.update(overrides)
    return PlanStep(**defaults)


def test_new_file_names_omitted_for_non_rename_operation_types():
    step = _step()

    assert step.newFileNames is None


def test_new_file_names_rejected_when_operation_type_is_not_rename():
    with pytest.raises(ValidationError):
        _step(newFileNames=["b.pdf"])


def test_new_file_names_required_when_operation_type_is_rename():
    with pytest.raises(ValidationError):
        _step(operationType=OperationType.RENAME)


def test_new_file_names_must_match_file_names_length():
    with pytest.raises(ValidationError):
        _step(
            operationType=OperationType.RENAME,
            fileNames=["a.pdf", "b.pdf"],
            affectedFileCount=2,
            newFileNames=["a2.pdf"],
        )


def test_new_file_names_rejects_duplicates():
    with pytest.raises(ValidationError):
        _step(
            operationType=OperationType.RENAME,
            fileNames=["a.pdf", "b.pdf"],
            affectedFileCount=2,
            newFileNames=["same.pdf", "same.pdf"],
        )


def test_new_file_names_rejects_path_separators():
    with pytest.raises(ValidationError):
        _step(operationType=OperationType.RENAME, newFileNames=["../evil.pdf"])


def test_new_file_names_rejects_blank_entries():
    with pytest.raises(ValidationError):
        _step(operationType=OperationType.RENAME, newFileNames=["   "])


def test_new_file_names_accepted_for_valid_rename_step():
    step = _step(operationType=OperationType.RENAME, newFileNames=["yeni.pdf"])

    assert step.newFileNames == ["yeni.pdf"]


def test_file_names_rejects_duplicates_within_the_same_step():
    # Red-team bulgusu (Saga #290): fileNames'te tekrar varsa
    # dict(zip(fileNames, newFileNames)) bir eslemeyi sessizce kaybederdi.
    with pytest.raises(ValidationError):
        _step(
            operationType=OperationType.RENAME,
            fileNames=["a.pdf", "a.pdf"],
            affectedFileCount=2,
            newFileNames=["x.pdf", "y.pdf"],
        )


def test_new_file_names_allows_a_case_only_self_rename():
    # 3. red-team turu bulgusu: a.pdf -> A.pdf (ayni dosyanin sadece harf
    # buyuklugu degisikligi) MESRU - kendi kendine cakisma sayilmamali.
    step = _step(operationType=OperationType.RENAME, fileNames=["a.pdf"], newFileNames=["A.pdf"])

    assert step.newFileNames == ["A.pdf"]


def test_new_file_names_rejects_case_variant_overlap_with_a_different_source():
    # a.pdf -> B.PDF cakisiyor cunku b.pdf de bu step'te AYRI bir kaynak.
    with pytest.raises(ValidationError):
        _step(
            operationType=OperationType.RENAME,
            fileNames=["a.pdf", "b.pdf"],
            affectedFileCount=2,
            newFileNames=["B.PDF", "c.pdf"],
        )


def test_new_file_names_rejects_overlap_with_source_file_names():
    # Red-team bulgusu (Saga #290): zincirleme rename (a.pdf->b.pdf VE
    # b.pdf->c.pdf ayni step'te) b.pdf'in orijinal icerigini kaybedebilirdi.
    with pytest.raises(ValidationError):
        _step(
            operationType=OperationType.RENAME,
            fileNames=["a.pdf", "b.pdf"],
            affectedFileCount=2,
            newFileNames=["b.pdf", "c.pdf"],
        )


# Saga #304: MERGE operasyonu - mergedFileName alanının SADECE MERGE icin
# zorunlu olmasi, path separator yasagi, fileNames >= 2 kisiti.


def test_merged_file_name_required_when_operation_type_is_merge():
    with pytest.raises(ValidationError):
        _step(
            operationType=OperationType.MERGE,
            fileNames=["a.pdf", "b.pdf"],
            affectedFileCount=2,
        )


def test_merged_file_name_rejected_when_operation_type_is_not_merge():
    with pytest.raises(ValidationError):
        _step(mergedFileName="birlesik.pdf")


def test_merged_file_name_accepted_for_valid_merge_step():
    step = _step(
        operationType=OperationType.MERGE,
        fileNames=["a.pdf", "b.pdf"],
        affectedFileCount=2,
        mergedFileName="birlesik.pdf",
    )

    assert step.mergedFileName == "birlesik.pdf"


def test_merged_file_name_rejects_path_separators():
    with pytest.raises(ValidationError):
        _step(
            operationType=OperationType.MERGE,
            fileNames=["a.pdf", "b.pdf"],
            affectedFileCount=2,
            mergedFileName="../evil.pdf",
        )


def test_merge_rejects_fewer_than_two_file_names():
    with pytest.raises(ValidationError):
        _step(
            operationType=OperationType.MERGE,
            fileNames=["a.pdf"],
            affectedFileCount=1,
            mergedFileName="birlesik.pdf",
        )


def test_merged_file_name_rejects_overlap_with_source_file_names():
    # Red-team bulgusu (Saga #304): mergedFileName, AYNI step'teki
    # fileNames girdilerinden biriyle ayniysa, _forward_merge kaynak
    # dosyayi hem okur hem AYNI path'e yazar - kaynak icerigi bozulabilir.
    with pytest.raises(ValidationError):
        _step(
            operationType=OperationType.MERGE,
            fileNames=["a.pdf", "b.pdf"],
            affectedFileCount=2,
            mergedFileName="a.pdf",
        )


def test_merged_file_name_rejects_case_variant_overlap_with_source_file_names():
    # Case-insensitive Windows dosya sistemi - A.PDF de a.pdf ile ayni
    # gercek dosyayi temsil eder.
    with pytest.raises(ValidationError):
        _step(
            operationType=OperationType.MERGE,
            fileNames=["a.pdf", "b.pdf"],
            affectedFileCount=2,
            mergedFileName="A.PDF",
        )


# Saga #305: SPLIT operasyonu - fileNames uzunlugu TAM OLARAK 1 olmali
# (MERGE'in "en az 2" kisitinin simetrigi, dar kapsam).


def test_split_rejects_more_than_one_file_name():
    with pytest.raises(ValidationError):
        _step(
            operationType=OperationType.SPLIT,
            fileNames=["a.pdf", "b.pdf"],
            affectedFileCount=2,
        )


def test_split_rejects_empty_file_names():
    with pytest.raises(ValidationError):
        _step(
            operationType=OperationType.SPLIT,
            fileNames=[],
            affectedFileCount=0,
        )


def test_split_accepts_exactly_one_file_name():
    step = _step(
        operationType=OperationType.SPLIT,
        fileNames=["a.pdf"],
        affectedFileCount=1,
    )

    assert step.fileNames == ["a.pdf"]


# OCR operasyonu (red step): OperationType.OCR henuz models.py'de tanimli
# degil, bu test o eklenene kadar KIRMIZI kalmali (OperationType.OCR erisimi
# AttributeError firlatir, bu da testin toplanma/calisma asamasinda
# basarisiz olmasina yol acar - beklenen red durumu).
def test_plan_step_rejects_ocr_with_more_than_one_file_name():
    with pytest.raises(ValidationError):
        _step(
            operationType=OperationType.OCR,
            fileNames=["a.pdf", "b.pdf"],
            affectedFileCount=2,
        )
