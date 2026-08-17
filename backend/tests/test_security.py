from pathlib import Path

import pytest

from backend.models import DateSource, PdfFileMetadata, PlanSkeleton, PlanStep, OperationType, SortOrder
from backend.security import PathWhitelistError, is_path_allowed, validate_plan_paths


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
        steps=[PlanStep(order=0, operationType=OperationType.MOVE, targetFolder=target_folder, affectedFileCount=1)],
        dateSource=DateSource.CREATED_AT,
        sortOrder=SortOrder.ASCENDING,
    )


def test_validate_plan_paths_passes_for_valid_plan(tmp_path):
    pdf_files = [PdfFileMetadata(filename="a.pdf", createdAt="2026-08-01")]

    validate_plan_paths(_plan(), pdf_files, tmp_path)


def test_validate_plan_paths_rejects_entire_plan_when_one_source_file_escapes_root(tmp_path):
    pdf_files = [
        PdfFileMetadata(filename="a.pdf", createdAt="2026-08-01"),
        PdfFileMetadata(filename=r"..\..\evil.pdf", createdAt="2026-08-01"),
    ]

    with pytest.raises(PathWhitelistError):
        validate_plan_paths(_plan(), pdf_files, tmp_path)


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
