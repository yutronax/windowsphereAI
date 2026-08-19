# Code Diff — word-tablo-basligi

Yazım motoru: bağımsız `efektor` subagent'lar (Codex kotası dolu; biri
test [red], biri implementasyon [green]).

## Files Modified
- `backend/models.py` — `OperationType.WORD_APPEND_TABLE`;
  `PlanStep.tableHeaders`/`tableRows`;
  `word_append_table_fields_only_for_word_append_table` model_validator
  (EXCEL_APPEND'in deseninin kopyası, `tableHeaders` opsiyonel).
- `backend/orchestrator.py` — `word_table` import; `_SUPPORTED_OPERATION_TYPES`,
  `_ROLLBACK_OPERATIONS` (`WORD_APPEND_TABLE→_rollback_append`, EXCEL_APPEND'in
  AYNI fonksiyonu, değişiklik gerekmedi), hedef-klasör hariç-tutma listesi;
  yeni step bloğu (EXCEL_APPEND bloğunun birebir kopyası).
- `requirements.txt` — `python-docx==1.2.0` eklendi (yeni bağımlılık, proje
  genelinde ilk kullanım).
- `backend/tests/test_word_table.py`, `backend/tests/test_orchestrator.py`
  — test-yazım subagent'ı tarafından red step'te eklendi.

## New Files
- `backend/word_table.py` — `append_table(source_path, headers, rows,
  backup_path) -> None`. **python-docx API'si gerçek kurulumla doğrulandı**
  (plan.md'nin önerisi `add_table(rows=N, cols=M)` +
  `table.rows[i].cells[j].text` doğru çıktı, düzeltme gerekmedi).
  `excel_rows.append_excel_rows`'un backup→tempfile→atomik-replace
  deseninin birebir kopyası.
- `backend/tests/test_word_table.py` — 6 unit test (red step'te yazıldı).

## Ortam düzeltmesi (bu görevde tespit edildi ve giderildi)
Test-yazım subagent'ı `python-docx`'i yanlışlıkla proje `.venv`'i yerine
global bir Python 3.11 kurulumuna kurmuştu. Bu, `git status`/pytest
doğrulamasında sessiz bir tutarsızlık yaratabilirdi (testler `.venv`
dışında geçip `.venv` ile kırmızı kalabilirdi). Fark edilip düzeltildi:
`python-docx` ayrıca `.venv`'e kuruldu, kırmızı/yeşil durumların ikisi de
`.venv` ile bağımsız olarak yeniden doğrulandı.

## Acceptance Criteria Coverage
AC-1 (başlıklı happy path), AC-2 (başlıksız happy path), AC-3 (sütun
uyuşmazlığı), AC-4 (kaynak yok/bozuk) — hepsi hem unit hem entegrasyon
seviyesinde yeşil.

## Test Evidence
- Hedeflenen testler: `11 passed`
- Tüm backend suite: `463 passed, 5 skipped, 0 failed` — regresyon yok.

## Remaining Limitations
- Word→PDF dönüştürme (LibreOffice) TAMAMEN kapsam dışı (atdd.md'de
  işaretli) — ortamda `soffice` kurulu değil.
- `plan_generation.py`/LLM prompt tarafı kapsam dışı.
- Tablo biçimlendirmesi (stil/renk/font) yok, sadece ham metin.

## CAVEMAN Review
- Files added: 2 (`word_table.py`, `test_word_table.py`) — plan.md'de öngörülmüştü.
- New abstractions: yok — EXCEL_APPEND'in kanıtlanmış mimari desenini birebir izliyor.
- New dependency: `python-docx` — plan.md'de gerekçelendirilmiş, tek kullanım noktası.

## Definition of Done
- Her AC implementeli, kısmi implementasyon yok, kapsam dışı işlevsellik yok.
- TODO/FIXME/placeholder yok.
- Proje konvansiyonları (EXCEL_APPEND deseni) takip edildi.
- `pytest backend/tests` — 463 passed, 5 skipped, 0 failed.
