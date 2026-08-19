# Plan — pdf-append-safe
_Reference: atdd.md_

## Files to Modify
| File | Why | Risk |
|------|-----|------|
| backend/models.py | `OperationType.APPEND = "Ekle"` eklenir; `PlanStep`'e `appendText: str | None = Field(default=None, max_length=5000)` alanı + `field_validator` (boş/whitespace reddi, sadece APPEND'te zorunlu — mevcut `mergedFileName` desenindeki `model_validator` ile aynı desen) | low |
| backend/orchestrator.py | `_forward_append(source_path, append_text)` fonksiyonu eklenir — MERGE/REDACT ile AYNI "geçici dosya + atomik replace" deseni, ama önce kaynağın GERÇEKTEN okunabilir olduğu doğrulanır (`PdfReader(str(source_path))` — açılamazsa `PlanApplicationError`, "dosya yok" ile AYNI hataya düşmez). `apply_plan`'daki operationType switch'ine `APPEND` dalı eklenir. | high |
| backend/plan_generation.py | Sistem promptuna `"Ekle"` operationType + `appendText` alan açıklaması eklenir (mevcut `mergedFileName` açıklama desenindeki gibi: "SADECE operationType Ekle ise... başka HERHANGİ bir operationType'ta bu alanı TAMAMEN ATLA") | low |
| requirements.txt | `reportlab==5.0.0` eklenir (en güncel, bilinen açığı olmayan sürüm — plan aşamasında `pip index versions` ile doğrulandı) | low |

## New Files
Yok — text→PDF sayfa render mantığı `orchestrator.py` içinde küçük bir yardımcı fonksiyon (`_render_text_page_bytes(text: str) -> bytes`) olarak eklenecek, MERGE/REDACT'ın kendi yardımcılarının yanına (ayrı bir dosya gerektirecek kadar büyük değil).

## Dependencies
- `pypdf.PdfReader`/`PdfWriter` — zaten kullanılıyor (MERGE/SPLIT/REDACT).
- `reportlab.pdfgen.canvas` — yeni, sadece düz metni bir sayfaya çizmek için (`canvas.Canvas(io.BytesIO(), pagesize=A4)`, `drawString` ile satır satır metin, uzun metin satır kaydırma gerektirebilir — basit bir word-wrap yardımcı fonksiyonu gerekebilir, code-copilot'a not).
- **Kaynak-var-ama-bozuk vs kaynak-yok ayrımı (ATDD'nin kalbi):** `source_path.exists()` kontrolü ÖNCE yapılır (yoksa "dosya bulunamadı" hatası), VARSA `PdfReader(str(source_path))` denenir (`try/except` — pypdf'in fırlattığı `PdfReadError`/`Exception` yakalanıp "kaynak PDF okunamıyor, bozuk olabilir" hatası fırlatılır). Bu iki kontrol AYRI `except` bloklarında, AYRI mesajlarla olmalı — eski projenin kusuru tam olarak bu ikisinin AYNI koda düşmesiydi.
- Testler mevcut `backend/tests/test_orchestrator.py`'ye eklenir (MERGE/REDACT test desenleri referans alınır).

## Migration Required?
Hayır — DB şeması değişmiyor, sadece Pydantic şeması ve saf dosya işlemi.

## Risks
- (atdd.md'den taşındı) `appendText` uzunluk sınırı 5000 karakter olarak belirlendi (ReDoS değil ama aşırı büyük tek-sayfa render maliyetini sınırlıyor) — makul bir varsayım, kullanıcı onaylamadı ama Threat-Model Notu'nun doğal sonucu.
- ReportLab'ın `drawString` API'si otomatik satır kaydırma (word-wrap) YAPMAZ — code-copilot'a NOT: 5000 karaktere kadar metin tek satıra sığmayacağı için basit bir word-wrap (satır başına ~80-90 karakter, `textwrap.wrap` stdlib ile) uygulanmalı, aksi halde metin sayfa dışına taşar/görünmez olur.
- Destination path = source path (yerinde güncelleme) — MERGE/REDACT'tan farklı olarak burada `source_path` ve `destination_path` AYNI — mevcut "geçici dosya + atomik replace" deseni bunu zaten güvenli kılıyor (kaynak, yazma tamamlanana kadar hiç dokunulmuyor).

## Open Questions
Yok — atdd.md'nin Unknowns'ı (ReportLab sürümü, appendText sınırı) bu plan turunda çözüldü.
