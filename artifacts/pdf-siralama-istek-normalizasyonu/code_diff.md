diff --git a/backend/models.py b/backend/models.py
index 5b1a9c9..8322673 100644
--- a/backend/models.py
+++ b/backend/models.py
@@ -1,16 +1,21 @@
 from pydantic import BaseModel, field_validator
 
+from backend.request_normalization import normalize_request_text, normalize_selected_folder
+
 
 class SessionRequest(BaseModel):
     selectedFolder: str
     requestText: str
 
-    @field_validator("selectedFolder", "requestText")
+    @field_validator("selectedFolder")
+    @classmethod
+    def normalize_folder(cls, value: str) -> str:
+        return normalize_selected_folder(value)
+
+    @field_validator("requestText")
     @classmethod
-    def not_blank(cls, value: str) -> str:
-        if value.strip() == "":
-            raise ValueError("must not be empty or whitespace-only")
-        return value
+    def normalize_text(cls, value: str) -> str:
+        return normalize_request_text(value)
 
 
 class SessionContext(BaseModel):
--- new file: backend/request_normalization.py ---
def _trim_and_reject_blank(value: str) -> str:
    trimmed = value.strip()
    if trimmed == "":
        raise ValueError("must not be empty or whitespace-only")
    return trimmed


def normalize_request_text(text: str) -> str:
    return _trim_and_reject_blank(text)


def normalize_selected_folder(folder: str) -> str:
    return _trim_and_reject_blank(folder)
