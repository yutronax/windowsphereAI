# Code Diff — word-to-pdf-donusumu

Codex kotası dolu olduğu için (15 Eylül 2026'ya kadar) bu değişiklik
kullanıcı onayıyla Claude Haiku alt ajanı (`efektor` subagent) tarafından
yazıldı — bu sefer açıkça "commit atma" talimatı verildi ve alt ajan buna
uydu (bağımsız `git log`/`git status` ile doğrulandı, yetkisiz commit yok).

## Yeni dosya
- `backend/word_to_pdf.py` — `WordToPdfConversionError` + `convert_word_to_pdf(source_path, destination_path, timeout=60)`. `shutil.which("soffice")` + sabit Windows yolu fallback'i, geçici dizine `--headless --norestore --convert-to pdf` çağrısı, tazelik doğrulaması (dosya var mı + boyut > 0 + mtime karşılaştırması), `Path.replace()` ile atomik taşıma, `finally` bloğunda geçici dizin temizliği.

## Değiştirilen dosyalar
- `backend/models.py`: `OperationType.WORD_TO_PDF`, `PlanStep.pdfFileName`, `word_to_pdf_fields_only_for_word_to_pdf` model_validator (PDF_COMPRESS deseninin birebir kopyası — AC-1).
- `backend/orchestrator.py`: import eklendi, `_SUPPORTED_OPERATION_TYPES`'a eklendi, rollback mapping'ine `WORD_TO_PDF: _rollback_copy` eklendi, `apply_plan` içine PDF_COMPRESS bloğunun hemen ardına WORD_TO_PDF bloğu eklendi (AC-1/AC-2/AC-3).
- `backend/security.py`: `_DESTINATION_FIELD_BY_OPERATION` dict'ine `WORD_TO_PDF: "pdfFileName"` eklendi — whitelist+çakışma kontrolü otomatik kapsandı (AC-5/AC-6).
- `backend/tests/test_security.py`: 2 yeni test (whitelist reddi + çakışma reddi).
- `backend/tests/test_orchestrator.py`: `_write_real_docx` (python-docx ile) + 4 yeni test (happy path gerçek soffice, kaynak dokunulmadı, kaynak yok, geçerli PDF üretimi).

## Doğrulama
```
./.venv/Scripts/python.exe -m pytest backend/tests/test_security.py backend/tests/test_orchestrator.py -k word_to_pdf -v
6 passed in 8.99s

./.venv/Scripts/python.exe -m pytest backend/
546 passed, 5 skipped in 76.36s
```
Bağımsız olarak (subagent raporundan ayrı) tarafımca yeniden çalıştırıldı,
aynı sonuç, 0 FAIL. (Subagent raporu "7 passed" dedi, gerçek sayı 6 — küçük
bir sapma, önemli değil, tüm testler zaten tam suite'te de PASS.)

## Tasarım notu (kod incelemesinde bulundu, red-team'e iletiliyor)
`convert_word_to_pdf`'in mtime-karşılaştırma mantığı (satır 92-96), her
çağrıda TAZE bir `tempfile.mkdtemp()` dizini kullandığı için pratikte
her zaman geçer (yeni oluşturulan geçici dosyanın mtime'ı sistem saati
geri gitmedikçe her zaman eskisinden yeni olur) — atdd.md'nin bahsettiği
"eski/bayat PDF sessizce üzerine yazılır" riski, LibreOffice'in doğrudan
`destination_path`e değil HER ZAMAN taze bir geçici dizine yazması
sayesinde zaten yapısal olarak önlenmiş durumda (Saga #329'un image
crop'taki "her zaman yeni dosyaya yaz" deseniyle aynı mantık). Asıl
etkili kontroller "dosya var mı" (satır 79) ve "boyut > 0" (satır 85) —
mtime karşılaştırması şu haliyle ölü/etkisiz kod. Blocking değil ama
CAVEMAN açısından not edilmeye değer.
