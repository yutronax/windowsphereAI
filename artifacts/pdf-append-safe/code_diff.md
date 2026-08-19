# Code Diff — pdf-append-safe (GREEN step)
_Reference: atdd.md, plan.md, test_diff.md_

## Değişen dosyalar

### requirements.txt
- `reportlab==5.0.0` eklendi (en güncel, bilinen açığı olmayan sürüm).

### backend/models.py
- `OperationType.APPEND = "Ekle"` eklendi.
- `PlanStep.appendText: str | None = Field(default=None, max_length=5000)` eklendi.
- `field_validator("appendText")` — boş/whitespace-only reddi (mevcut `contentContains` deseniyle tutarlı).
- `model_validator` — `operationType == APPEND` ise `appendText` zorunlu + `fileNames` tam olarak 1 dosya içermeli, diğer operationType'larda `appendText` yasak.

### backend/orchestrator.py
- `_render_text_page_bytes(text)` — ReportLab A4 canvas, `textwrap.wrap(width=90)` ile satır kaydırma, tek sayfalık PDF bytes üretir.
- `_forward_append(source_path, append_text, backup_path=None)` — kaynak-yok (AC-3) ile kaynak-bozuk (AC-2) AYRI `PlanApplicationError` mesajlarıyla ayrılır; MERGE/REDACT ile AYNI geçici-dosya+atomik-replace deseni; `backup_path` verilirse atomik değiştirmeden hemen önce kaynağın kopyası alınır (rollback için).
- `_rollback_append(destination_path, backup_path)` — yeni bir rollback varyantı: APPEND kaynağı YERİNDE günceller (hedef=kaynak), rollback "hedefi silmek" değil backup'ı geri kopyalamak.
- `_APPEND_BACKUP_DIRNAME` + `_append_backup_path()` — DELETE'in yedek deseniyle aynı ama ayrı bir gizli klasör.
- `apply_plan()`'a APPEND dalı eklendi (`_SUPPORTED_OPERATION_TYPES`, `_ROLLBACK_OPERATIONS`'a kayıt).

### backend/plan_generation.py
- Sistem promptuna "Ekle" operationType + `appendText` alan açıklaması eklendi (mevcut `mergedFileName` kalıbıyla tutarlı).

## Pytest sonucu
```
.venv/Scripts/python.exe -m pytest backend/tests/ -v
376 passed, 5 skipped, 0 failed
```

## Bilinen sınırlama (red-team'de bulundu, ayrı görev olarak flag'lendi)
`_APPEND_BACKUP_DIRNAME` klasörü hiç temizlenmiyor (DELETE'in aksine purge mekanizması yok) — `task_d8391ecb` ile takipte.
