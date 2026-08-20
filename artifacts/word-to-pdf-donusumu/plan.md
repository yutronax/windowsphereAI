# Plan — word-to-pdf-donusumu
_Reference: atdd.md_

## Files to Modify
| File | Why | Risk |
|------|-----|------|
| backend/models.py | AC-1/AC-6: `OperationType.WORD_TO_PDF` enum girdisi eklenir (satır ~84 civarına, `WORD_APPEND_TABLE`'ın yanına); `pdfFileName: str \| None = None` alanı eklenir; `PDF_COMPRESS` deseninin BİREBİR kopyası olan yeni bir `word_to_pdf_fields_only_for_word_to_pdf` model_validator'ı eklenir (satır ~648-671, `pdf_compress_fields_only_for_pdf_compress`'in hemen ardına) — `pdfFileName` SADECE `WORD_TO_PDF` için zorunlu, `fileNames` tam olarak 1 eleman, `pdfFileName` kaynaklarla çakışamaz. | low |
| backend/security.py | AC-5/AC-6: `_DESTINATION_FIELD_BY_OPERATION` dict'ine (satır 175-186) `OperationType.WORD_TO_PDF: "pdfFileName"` girdisi eklenir — whitelist (satır 138-155) VE çakışma kontrolü (`validate_destination_collisions`, satır 189-299) OTOMATİK olarak bu yeni operasyonu kapsar, ek kod gerekmez (Saga #338'in tam tasarladığı genelleştirme buradan faydalanıyor). | low |
| backend/orchestrator.py | AC-1/AC-2/AC-3/AC-4: yeni bir `if step.operationType == OperationType.WORD_TO_PDF:` bloğu (satır ~880 civarına, `PDF_COMPRESS` bloğunun deseniyle — `source_path`/`destination_path` hesapla, yeni modülü çağır, `PlanApplicationError` ile sarmalanmış exception, `record_file_operation` + `completed` + `applied.append`). Rollback fonksiyonu: `_rollback_copy` (satır 388-392'deki `PDF_COMPRESS: _rollback_copy` mapping'ine `WORD_TO_PDF: _rollback_copy` eklenir — kaynak asla değişmiyor, hedef silinerek geri alınır, COPY semantiği). | medium |
| backend/tests/test_orchestrator.py | AC-1..AC-4/AC-6 için happy-path + timeout + tazelik-başarısız + whitelist/çakışma testleri (mevcut PDF_COMPRESS testlerinin — satır 2718-2767 civarı — desenini takip eder). GERÇEK bir `.docx` fixture'ı ve GERÇEK `soffice` çağrısı gerekiyor (integration testler, atdd.md test_strategy %30). | medium |
| backend/tests/test_security.py | AC-5/AC-6 için WORD_TO_PDF'in whitelist+çakışma testleri (Saga #338'in 7-operasyonluk desenini takip eder — 2 test: whitelist reddi + çakışma reddi). | low |

## New Files
| File | Purpose |
|------|---------|
| backend/word_to_pdf.py | AC-1/AC-2/AC-3: `convert_word_to_pdf(source_path: Path, destination_path: Path, timeout: int = 60) -> None` — `shutil.which("soffice")` ile ikili konumunu bulur (PATH'te aranır, sabit Windows yoluna hardcode edilmez — atdd.md Assumptions), bulunamazsa açık bir hata fırlatır; GEÇİCİ bir dizine `subprocess.run(["soffice", "--headless", "--norestore", "--convert-to", "pdf", "--outdir", tmp_dir, str(source_path)], timeout=60, capture_output=True)` çalıştırır (LibreOffice çıktı dosya adını HER ZAMAN `source.stem+".pdf"` üretir — komut satırından değiştirilemez, bu yüzden geçici dizine yazılıp `Path.rename`/`.replace()` ile kullanıcının istediği `destination_path`e taşınır); dönüşüm ÖNCESİ hedef `destination_path` mtime/varlığı kaydedilir, dönüşüm SONRASI (geçici dosyanın) mtime/boyutu ile karşılaştırılıp "tazelik" (gerçekten yeni içerik üretildi mi) doğrulanır — tazelik başarısızsa özel bir exception (`WordToPdfConversionError` veya benzeri) fırlatılır, `subprocess.TimeoutExpired` de aynı/ayrı bir exception'a çevrilir. |

## Dependencies
- `backend/pdf_compress.py`'nin tempfile+atomik-replace (`temp_path.replace(destination_path)`) deseni referans alınacak — ama BU İLK KEZ bir DIŞ İKİLİ (subprocess) çağrısı olacak, `backend/` içinde şu an `subprocess` kullanan HİÇBİR modül yok (grep ile doğrulandı) — bu, projenin ilk external-process-çağıran operasyonu, hata yüzeyi (process spawn başarısızlığı, timeout, kayıp/bozuk PATH) diğer modüllerden farklı, dikkatli ele alınmalı.
- `backend/orchestrator.py` satır 388-392'deki rollback-fonksiyon mapping'i (`ROLLBACK_HANDLERS` veya benzeri isimli dict, tam adı orchestrator.py'de doğrulanacak) — `WORD_TO_PDF: _rollback_copy` eklenmesi gerekiyor, aksi halde rollback sırasında `KeyError`/tanımsız davranış riski var (mevcut PDF_COMPRESS ile AYNI COPY semantiği: kaynak dokunulmadı, hedef silinerek geri alınır).
- `backend/models.py`'nin `OperationType` enum'ının kullanıldığı TÜM yerler (`backend/orchestrator.py` satır 1157 civarındaki bir liste/set — muhtemelen "hangi operasyonlar X davranışını paylaşıyor" gibi bir gruplama) kontrol edilmeli, WORD_TO_PDF'in oraya da eklenmesi gerekip gerekmediği (ör. "tek-kaynak" operasyonlar listesi) plan/code-copilot aşamasında doğrulanmalı.
- `python-docx` zaten `word_table.py` için kurulu (Word dosyalarını AÇMAK için) ama bu görev Word dosyasını AÇMIYOR, sadece `soffice`'e path olarak veriyor — `python-docx`'e yeni bir bağımlılık gerekmiyor.

## Migration Required?
Hayır — sadece Python kod + yeni bir enum değeri, şema/veri değişikliği yok.

## Risks
- (atdd.md'den taşındı) LibreOffice'in çıktı dosya adını HER ZAMAN `source.stem+".pdf"` üretmesi — implementasyon geçici-dizin+rename deseniyle bunu çözüyor (yukarıda New Files'ta detaylandırıldı).
- (atdd.md'den taşındı) İlk `soffice --version` denemesinin ~30 saniye takılması (muhtemelen ilk-çalıştırma profil oluşturma) — `--headless --norestore` bayrakları + 60sn timeout bunu ele alıyor, ama CI/başka bir makinede İLK çalıştırmanın daha da yavaş olabileceği unutulmamalı (test ortamında `soffice`'in en az bir kez "ısıtılmış" olması gerekebilir — bu, test-copilot'un dikkat etmesi gereken bir nokta, flaky test riski).
- **Yeni (plan aşamasında bulundu):** Bu, projenin İLK subprocess/dış-ikili çağrısı — mevcut hiçbir modül bu deseni kullanmıyor, code-copilot'un taklit edebileceği bir örnek yok, sıfırdan tasarlanmalı (timeout, PATH arama, encoding/output capture hataları).

## Open Questions
Yok — atdd.md'deki kullanıcı onaylarıyla (WORD_TO_PDF, PathWhitelistError ile çakışma reddi, 60sn timeout, unit/integration oranı) kapsam net. `pdfFileName` alan adı bu planda PDF_COMPRESS'in `compressedFileName` desenine göre kesinleştirildi (atdd.md'nin "Unknowns" bölümündeki soru burada cevaplandı).
