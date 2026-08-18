import json

import pytest

from backend.models import DateSource, PdfFileMetadata, PlanSkeleton, SortOrder
from backend.plan_generation import (
    DEFAULT_MODEL_ID,
    PlanGenerationError,
    build_metadata_prompt,
    generate_plan_skeleton,
    resolve_model_id,
)


class FakeLLMClient:
    def __init__(self, response: str | None = None, exception: Exception | None = None):
        self.response = response
        self.exception = exception
        self.last_call: dict | None = None

    def complete(self, *, model: str, system_prompt: str, user_prompt: str) -> str:
        self.last_call = {"model": model, "system_prompt": system_prompt, "user_prompt": user_prompt}
        if self.exception is not None:
            raise self.exception
        assert self.response is not None
        return self.response


VALID_PLAN_JSON = json.dumps(
    {
        "dateSource": "created_at",
        "sortOrder": "descending",
        "steps": [
            {"order": 0, "operationType": "Taşı", "targetFolder": "2026-08", "affectedFileCount": 2, "fileNames": ["a.pdf", "b.pdf"]},
            {"order": 1, "operationType": "Taşı", "targetFolder": "2026-07", "affectedFileCount": 1, "fileNames": ["c.pdf"]},
        ],
    }
)

ONE_PDF = [PdfFileMetadata(filename="fatura.pdf", createdAt="2026-08-01")]


def test_returns_a_valid_plan_skeleton_from_a_valid_llm_response():
    client = FakeLLMClient(response=VALID_PLAN_JSON)

    result = generate_plan_skeleton(ONE_PDF, client)

    assert isinstance(result, PlanSkeleton)
    assert len(result.steps) == 2
    assert result.steps[0].targetFolder == "2026-08"


def test_returns_an_empty_plan_without_calling_the_llm_when_no_pdf_files():
    client = FakeLLMClient(response="should not be used")

    result = generate_plan_skeleton([], client)

    assert result == PlanSkeleton(steps=[], dateSource=DateSource.CREATED_AT, sortOrder=SortOrder.ASCENDING)
    assert client.last_call is None


def test_raises_plan_generation_error_when_the_llm_client_raises():
    client = FakeLLMClient(exception=RuntimeError("network down"))

    with pytest.raises(PlanGenerationError):
        generate_plan_skeleton(ONE_PDF, client)


def test_raises_plan_generation_error_for_invalid_json():
    client = FakeLLMClient(response="not json at all")

    with pytest.raises(PlanGenerationError):
        generate_plan_skeleton(ONE_PDF, client)


def test_raises_plan_generation_error_for_a_response_outside_the_schema():
    invalid = json.dumps({"steps": [{"order": -1, "operationType": "Taşı", "targetFolder": "X", "affectedFileCount": 1}]})
    client = FakeLLMClient(response=invalid)

    with pytest.raises(PlanGenerationError):
        generate_plan_skeleton(ONE_PDF, client)


def test_raises_plan_generation_error_for_an_unknown_operation_type():
    invalid = json.dumps({"steps": [{"order": 0, "operationType": "FormatDisk", "targetFolder": "X", "affectedFileCount": 1}]})
    client = FakeLLMClient(response=invalid)

    with pytest.raises(PlanGenerationError):
        generate_plan_skeleton(ONE_PDF, client)


def test_raises_plan_generation_error_for_duplicate_order_values():
    invalid = json.dumps(
        {
            "steps": [
                {"order": 0, "operationType": "Taşı", "targetFolder": "X", "affectedFileCount": 1},
                {"order": 0, "operationType": "Sil", "targetFolder": "Y", "affectedFileCount": 1},
            ]
        }
    )
    client = FakeLLMClient(response=invalid)

    with pytest.raises(PlanGenerationError):
        generate_plan_skeleton(ONE_PDF, client)


def test_uses_the_explicitly_passed_model_over_the_env_default():
    client = FakeLLMClient(response=VALID_PLAN_JSON)

    generate_plan_skeleton(ONE_PDF, client, model="custom-model")

    assert client.last_call["model"] == "custom-model"


def test_resolve_model_id_falls_back_to_default_when_env_unset(monkeypatch):
    monkeypatch.delenv("PLAN_LLM_MODEL_ID", raising=False)

    assert resolve_model_id() == DEFAULT_MODEL_ID


def test_resolve_model_id_uses_env_override(monkeypatch):
    monkeypatch.setenv("PLAN_LLM_MODEL_ID", "pinned-model-x")

    assert resolve_model_id() == "pinned-model-x"


def test_generate_plan_skeleton_uses_the_env_model_when_none_passed(monkeypatch):
    monkeypatch.setenv("PLAN_LLM_MODEL_ID", "pinned-model-x")
    client = FakeLLMClient(response=VALID_PLAN_JSON)

    generate_plan_skeleton(ONE_PDF, client)

    assert client.last_call["model"] == "pinned-model-x"


def test_build_metadata_prompt_includes_only_filename_and_date_not_content():
    prompt = build_metadata_prompt([PdfFileMetadata(filename="fatura.pdf", createdAt="2026-08-01")], "PDF'leri sırala")

    assert "fatura.pdf" in prompt
    assert "2026-08-01" in prompt


def test_build_metadata_prompt_includes_the_user_request_text():
    # Saga #292: request_text olmadan LLM COPY/DELETE/RENAME/LIST arasindan
    # dogru operationType'i secemiyordu - artik prompt'a dahil ediliyor.
    prompt = build_metadata_prompt([PdfFileMetadata(filename="a.pdf", createdAt="2026-08-01")], "Bu dosyalari yedekle")

    assert "Bu dosyalari yedekle" in prompt


def test_generate_plan_skeleton_passes_the_request_text_to_the_llm_prompt():
    client = FakeLLMClient(response=VALID_PLAN_JSON)

    generate_plan_skeleton(ONE_PDF, client, request_text="Eski dosyalari sil")

    assert "Eski dosyalari sil" in client.last_call["user_prompt"]


def test_raises_plan_generation_error_when_date_source_is_missing():
    missing = json.dumps(
        {
            "sortOrder": "ascending",
            "steps": [{"order": 0, "operationType": "Taşı", "targetFolder": "2026-08", "affectedFileCount": 1}],
        }
    )
    client = FakeLLMClient(response=missing)

    with pytest.raises(PlanGenerationError):
        generate_plan_skeleton(ONE_PDF, client)


def test_raises_plan_generation_error_for_an_unknown_date_source():
    invalid = json.dumps(
        {
            "dateSource": "modified_at",
            "sortOrder": "ascending",
            "steps": [{"order": 0, "operationType": "Taşı", "targetFolder": "2026-08", "affectedFileCount": 1}],
        }
    )
    client = FakeLLMClient(response=invalid)

    with pytest.raises(PlanGenerationError):
        generate_plan_skeleton(ONE_PDF, client)


def test_raises_plan_generation_error_when_sort_order_is_missing():
    missing = json.dumps(
        {
            "dateSource": "created_at",
            "steps": [{"order": 0, "operationType": "Taşı", "targetFolder": "2026-08", "affectedFileCount": 1}],
        }
    )
    client = FakeLLMClient(response=missing)

    with pytest.raises(PlanGenerationError):
        generate_plan_skeleton(ONE_PDF, client)


def test_raises_plan_generation_error_for_an_unknown_sort_order():
    invalid = json.dumps(
        {
            "dateSource": "created_at",
            "sortOrder": "random",
            "steps": [{"order": 0, "operationType": "Taşı", "targetFolder": "2026-08", "affectedFileCount": 1}],
        }
    )
    client = FakeLLMClient(response=invalid)

    with pytest.raises(PlanGenerationError):
        generate_plan_skeleton(ONE_PDF, client)


@pytest.mark.parametrize("bad_target_folder", ["2026", "Ağustos", "2026-8", "", "2026/08", "2026-13", "2026-00"])
def test_raises_plan_generation_error_for_a_target_folder_not_matching_yyyy_mm(bad_target_folder):
    invalid = json.dumps(
        {
            "dateSource": "created_at",
            "sortOrder": "ascending",
            "steps": [{"order": 0, "operationType": "Taşı", "targetFolder": bad_target_folder, "affectedFileCount": 1}],
        }
    )
    client = FakeLLMClient(response=invalid)

    with pytest.raises(PlanGenerationError):
        generate_plan_skeleton(ONE_PDF, client)


def test_empty_pdf_list_still_produces_a_plan_skeleton_with_date_source_and_sort_order():
    client = FakeLLMClient(response="should not be used")

    result = generate_plan_skeleton([], client)

    assert result.dateSource == DateSource.CREATED_AT
    assert result.sortOrder == SortOrder.ASCENDING


# Saga #304: PLAN_SYSTEM_PROMPT'a MERGE eslemesi + mergedFileName sema
# aciklamasi eklendigini dogrular.


def test_system_prompt_maps_birlestir_request_to_merge_operation_type():
    from backend.plan_generation import PLAN_SYSTEM_PROMPT

    assert "birleştir" in PLAN_SYSTEM_PROMPT
    assert "tek dosya yap" in PLAN_SYSTEM_PROMPT
    assert "Birleştir" in PLAN_SYSTEM_PROMPT


def test_system_prompt_documents_merged_file_name_schema():
    from backend.plan_generation import PLAN_SYSTEM_PROMPT

    assert "mergedFileName" in PLAN_SYSTEM_PROMPT


# Saga #305: PLAN_SYSTEM_PROMPT'a SPLIT eslemesi + fileNames'in SPLIT icin
# tam 1 dosya icermesi gerektigi notu eklendigini dogrular.


def test_system_prompt_maps_bol_request_to_split_operation_type():
    from backend.plan_generation import PLAN_SYSTEM_PROMPT

    assert "böl" in PLAN_SYSTEM_PROMPT
    assert "Böl" in PLAN_SYSTEM_PROMPT


def test_system_prompt_documents_split_requires_exactly_one_file_name():
    from backend.plan_generation import PLAN_SYSTEM_PROMPT

    assert "Böl" in PLAN_SYSTEM_PROMPT
    assert "tam olarak 1" in PLAN_SYSTEM_PROMPT or "TAM OLARAK 1" in PLAN_SYSTEM_PROMPT
