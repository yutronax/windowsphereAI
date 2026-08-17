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
