diff --git a/backend/tests/test_main_integration.py b/backend/tests/test_main_integration.py
index c851a49..889da3e 100644
--- a/backend/tests/test_main_integration.py
+++ b/backend/tests/test_main_integration.py
@@ -134,7 +134,11 @@ def test_cors_header_present_for_session_post_from_allowed_origin():
 
 
 VALID_PLAN_JSON = json.dumps(
-    {"steps": [{"order": 0, "operationType": "Taşı", "targetFolder": "2026-08", "affectedFileCount": 1}]}
+    {
+        "dateSource": "created_at",
+        "sortOrder": "ascending",
+        "steps": [{"order": 0, "operationType": "Taşı", "targetFolder": "2026-08", "affectedFileCount": 1}],
+    }
 )
 
 
diff --git a/backend/tests/test_plan_generation.py b/backend/tests/test_plan_generation.py
index ab56859..761eda6 100644
--- a/backend/tests/test_plan_generation.py
+++ b/backend/tests/test_plan_generation.py
@@ -2,7 +2,7 @@ import json
 
 import pytest
 
-from backend.models import PdfFileMetadata, PlanSkeleton
+from backend.models import DateSource, PdfFileMetadata, PlanSkeleton, SortOrder
 from backend.plan_generation import (
     DEFAULT_MODEL_ID,
     PlanGenerationError,
@@ -28,10 +28,12 @@ class FakeLLMClient:
 
 VALID_PLAN_JSON = json.dumps(
     {
+        "dateSource": "created_at",
+        "sortOrder": "descending",
         "steps": [
             {"order": 0, "operationType": "Taşı", "targetFolder": "2026-08", "affectedFileCount": 2},
             {"order": 1, "operationType": "Taşı", "targetFolder": "2026-07", "affectedFileCount": 1},
-        ]
+        ],
     }
 )
 
@@ -53,7 +55,7 @@ def test_returns_an_empty_plan_without_calling_the_llm_when_no_pdf_files():
 
     result = generate_plan_skeleton([], client)
 
-    assert result == PlanSkeleton(steps=[])
+    assert result == PlanSkeleton(steps=[], dateSource=DateSource.CREATED_AT, sortOrder=SortOrder.ASCENDING)
     assert client.last_call is None
 
 
@@ -136,3 +138,81 @@ def test_build_metadata_prompt_includes_only_filename_and_date_not_content():
 
     assert "fatura.pdf" in prompt
     assert "2026-08-01" in prompt
+
+
+def test_raises_plan_generation_error_when_date_source_is_missing():
+    missing = json.dumps(
+        {
+            "sortOrder": "ascending",
+            "steps": [{"order": 0, "operationType": "Taşı", "targetFolder": "2026-08", "affectedFileCount": 1}],
+        }
+    )
+    client = FakeLLMClient(response=missing)
+
+    with pytest.raises(PlanGenerationError):
+        generate_plan_skeleton(ONE_PDF, client)
+
+
+def test_raises_plan_generation_error_for_an_unknown_date_source():
+    invalid = json.dumps(
+        {
+            "dateSource": "modified_at",
+            "sortOrder": "ascending",
+            "steps": [{"order": 0, "operationType": "Taşı", "targetFolder": "2026-08", "affectedFileCount": 1}],
+        }
+    )
+    client = FakeLLMClient(response=invalid)
+
+    with pytest.raises(PlanGenerationError):
+        generate_plan_skeleton(ONE_PDF, client)
+
+
+def test_raises_plan_generation_error_when_sort_order_is_missing():
+    missing = json.dumps(
+        {
+            "dateSource": "created_at",
+            "steps": [{"order": 0, "operationType": "Taşı", "targetFolder": "2026-08", "affectedFileCount": 1}],
+        }
+    )
+    client = FakeLLMClient(response=missing)
+
+    with pytest.raises(PlanGenerationError):
+        generate_plan_skeleton(ONE_PDF, client)
+
+
+def test_raises_plan_generation_error_for_an_unknown_sort_order():
+    invalid = json.dumps(
+        {
+            "dateSource": "created_at",
+            "sortOrder": "random",
+            "steps": [{"order": 0, "operationType": "Taşı", "targetFolder": "2026-08", "affectedFileCount": 1}],
+        }
+    )
+    client = FakeLLMClient(response=invalid)
+
+    with pytest.raises(PlanGenerationError):
+        generate_plan_skeleton(ONE_PDF, client)
+
+
+@pytest.mark.parametrize("bad_target_folder", ["2026", "Ağustos", "2026-8", "", "2026/08", "2026-13", "2026-00"])
+def test_raises_plan_generation_error_for_a_target_folder_not_matching_yyyy_mm(bad_target_folder):
+    invalid = json.dumps(
+        {
+            "dateSource": "created_at",
+            "sortOrder": "ascending",
+            "steps": [{"order": 0, "operationType": "Taşı", "targetFolder": bad_target_folder, "affectedFileCount": 1}],
+        }
+    )
+    client = FakeLLMClient(response=invalid)
+
+    with pytest.raises(PlanGenerationError):
+        generate_plan_skeleton(ONE_PDF, client)
+
+
+def test_empty_pdf_list_still_produces_a_plan_skeleton_with_date_source_and_sort_order():
+    client = FakeLLMClient(response="should not be used")
+
+    result = generate_plan_skeleton([], client)
+
+    assert result.dateSource == DateSource.CREATED_AT
+    assert result.sortOrder == SortOrder.ASCENDING
