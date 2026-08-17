diff --git a/backend/models.py b/backend/models.py
index a5ab275..0012d3a 100644
--- a/backend/models.py
+++ b/backend/models.py
@@ -1,9 +1,14 @@
+import re
 from enum import Enum
 
 from pydantic import BaseModel, field_validator
 
 from backend.request_normalization import normalize_request_text, normalize_selected_folder
 
+# YYYY-MM, ay 01-12 aralığında olmalı (red-team bulgusu, Saga #270: "2026-13"
+# gibi geçersiz aylar eskiden bu regex'ten geçiyordu).
+TARGET_FOLDER_PATTERN = re.compile(r"^\d{4}-(0[1-9]|1[0-2])$")
+
 
 class SessionRequest(BaseModel):
     selectedFolder: str
@@ -49,14 +54,33 @@ class PlanStep(BaseModel):
 
     @field_validator("targetFolder")
     @classmethod
-    def target_folder_not_blank(cls, value: str) -> str:
-        if value.strip() == "":
-            raise ValueError("must not be empty or whitespace-only")
+    def target_folder_matches_year_month(cls, value: str) -> str:
+        if not TARGET_FOLDER_PATTERN.match(value.strip()):
+            raise ValueError("must be a YYYY-MM folder name (e.g. '2026-08')")
         return value
 
 
+class DateSource(str, Enum):
+    """Not: `PlanSkeleton.steps` boşsa (taşınacak PDF yoksa),
+    `dateSource`/`sortOrder` yine de şema tutarlılığı için gerçek bir enum
+    değeri taşır ama HİÇBİR GERÇEK KARARI TEMSİL ETMEZ — `generate_plan_skeleton`
+    bu durumda LLM'e hiç istek atmadan varsayılan değerler atar (bkz.
+    plan_generation.py). Downstream kod (Security/Orchestrator, Saga #271+)
+    bu alanları `steps` boşken anlamlı veri gibi yorumlamamalı (red-team
+    bulgusu, Saga #270)."""
+
+    CREATED_AT = "created_at"
+
+
+class SortOrder(str, Enum):
+    ASCENDING = "ascending"
+    DESCENDING = "descending"
+
+
 class PlanSkeleton(BaseModel):
     steps: list[PlanStep]
+    dateSource: DateSource
+    sortOrder: SortOrder
 
     @field_validator("steps")
     @classmethod
diff --git a/backend/plan_generation.py b/backend/plan_generation.py
index 1e7606c..a5916f2 100644
--- a/backend/plan_generation.py
+++ b/backend/plan_generation.py
@@ -4,7 +4,7 @@ from typing import Protocol
 
 from pydantic import ValidationError
 
-from backend.models import PdfFileMetadata, PlanSkeleton
+from backend.models import DateSource, PdfFileMetadata, PlanSkeleton, SortOrder
 
 DEFAULT_MODEL_ID = "gpt-4o-mini"
 MODEL_ID_ENV_VAR = "PLAN_LLM_MODEL_ID"
@@ -13,10 +13,13 @@ PLAN_SYSTEM_PROMPT = (
     "Sen bir dosya organizasyon asistanısın. Sana verilen PDF dosya adı ve "
     "oluşturulma tarihi metadata'sından, dosyaları tarihe göre YYYY-MM "
     "klasörlerine taşıyacak bir plan üret. Sadece şu JSON şemasında yanıt "
-    'ver: {"steps": [{"order": <negatif olmayan tamsayı>, "operationType": '
+    'ver: {"dateSource": "created_at", "sortOrder": "ascending"|"descending", '
+    '"steps": [{"order": <negatif olmayan tamsayı>, "operationType": '
     '"Taşı"|"Kopyala"|"Sil"|"Yeniden Adlandır"|"Listele", "targetFolder": '
-    '<string>, "affectedFileCount": <negatif olmayan tamsayı>}]}. '
-    "Başka hiçbir metin ekleme, sadece bu JSON'u döndür."
+    '<"YYYY-MM" formatında string>, "affectedFileCount": <negatif olmayan '
+    "tamsayı>}]}. dateSource ve sortOrder alanları AÇIKÇA belirtilmeli, "
+    "her targetFolder kesinlikle YYYY-MM formatında olmalı. Başka hiçbir "
+    "metin ekleme, sadece bu JSON'u döndür."
 )
 
 
@@ -43,7 +46,9 @@ def generate_plan_skeleton(
     model: str | None = None,
 ) -> PlanSkeleton:
     if not pdf_files:
-        return PlanSkeleton(steps=[])
+        # Taşınacak dosya yoksa LLM'e hiç istek atılmaz; dateSource/sortOrder
+        # yine de şema tutarlılığı için sağlanır (fiilen kullanılmaz).
+        return PlanSkeleton(steps=[], dateSource=DateSource.CREATED_AT, sortOrder=SortOrder.ASCENDING)
 
     resolved_model = model or resolve_model_id()
     prompt = build_metadata_prompt(pdf_files)
