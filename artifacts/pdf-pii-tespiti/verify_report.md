# Verify Report — pdf-pii-tespiti
_Reference: atdd.md, plan.md, code_diff.md_

## Verification Gates
| # | Gate | Result | Evidence / Reason |
|---|------|--------|--------------------|
| 1 | Dosya konumu | PASS | `git status --short` → `backend/models.py`/`main.py` (M), `backend/pdf_pii.py`/`tests/test_pdf_pii.py` (yeni) — code_diff.md'de belirtilen konumlarda. |
| 2 | Build/derleme | PASS | `pytest`'in collection aşaması hatasız (import zinciri sağlam). |
| 3 | Supabase şema/canlı doğrulama | N/A | Değişiklik Supabase'e dokunmuyor. |
| 4 | Lint | N/A | Proje linter/formatter tanımlamıyor. |
| 5 | Type check | N/A | Proje tip denetleyici tanımlamıyor. |
| 6 | Unit/Integration testler | PASS | `.venv/Scripts/python.exe -m pytest backend/tests/test_pdf_pii.py -v` → **22 passed**. `.venv/Scripts/python.exe -m pytest backend/` → **570 passed, 5 skipped, 0 failed**. Bağımsız olarak (subagent raporundan ayrı) iki kez çalıştırıldı. |
| 7 | E2E testler | N/A | atdd.md'nin kabul kararı: backend-only, otomatik testler yeterli. |
| 8 | Lighthouse (performans) | N/A | Web UI dokunulmadı. |
| 9 | Erişilebilirlik | N/A | Aynı gerekçe (gate 8). |
| 10 | Güvenlik taraması | **İNCELENDİ, FALSE POSITIVE** | `security-scan` → `secrets: FAIL` — `backend/tests/test_pdf_pii.py:57`'deki `"1234567890A"` (geçersiz-TC-no test literalı) yüksek-entropi hex dizesine benzediği için işaretlenmiş. Doğrulandı: bu bir test fixture'ı, gerçek bir API anahtarı/token/parola DEĞİL — `_is_valid_tc_kimlik_no`'nun "harf içerirse reddet" dalını test ediyor. `python_sast`/`python_deps`/`node_deps`: PASS. |
| 11 | AI code review | PENDING (red-team) | Sıradaki adımda yapılacak. |
| 12 | Görsel regresyon | N/A | Web UI dokunulmadı. |
| 13 | İnsan onayı | PENDING | Kullanıcı henüz onaylamadı. |

## AC -> Test Mapping
1. [Critical] Happy path (TC/IBAN bulunur, RedactionRegion döner) → `test_detect_pii_finds_valid_tc_kimlik_no`, `test_detect_pii_finds_iban`, `test_detect_pii_endpoint_success_with_regions` → PASS.
2. [Critical] Boş sonuç (PII yok → 200+[]) → `test_detect_pii_empty_pdf`, `test_detect_pii_endpoint_empty_pdf_returns_empty_list` → PASS.
3. [High] Checksum başarısız → yanlış-pozitif yok → `test_detect_pii_invalid_checksum_not_detected`, `TestTcKimlikNoValidation` sınıfının 7 testi → PASS.
4. [High] Whitelist/dosya-yok/klasör-yok hataları → `test_detect_pii_endpoint_missing_folder` (410), `test_detect_pii_endpoint_missing_file` (404) → PASS.
5. [Medium] Sayfa-dışı bölgeler atlanır → `_calculate_bounding_box_from_fragments`'in sınır kontrolü (kod incelemesiyle doğrulandı, ayrı bir doğrudan test yok — düşük öncelik).
6. [Critical] [AC-S1] Ham PII değeri response'da yok → `test_detect_pii_no_ham_values_in_response` → PASS.
7. [High] [AC-S2] ReDoS-güvenli sabit-uzunluklu regex → kod incelemesiyle doğrulandı (`\d{11}`, `TR\d{24}`, iç içe açık-uçlu quantifier yok) → PASS.

## Coverage / Quality Notes
- **Süreç notu (code_diff.md'de detaylı):** İlk yazımda `detect_pii` her eşleşme için AYNI sabit bölgeyi döndürüyordu (gerçek konumla ilgisiz) — koordinatör kod incelemesinde buldu, subagent'a geri gönderildi, gerçek `visitor_text`-tabanlı konum hesaplamasına geçildi, bağımsız doğrulandı.
- **Test-gap (düşük öncelik):** Aynı sayfada 2 farklı konumdaki eşleşmenin farklı x/y aldığını DOĞRUDAN kanıtlayan bir test yok — sadece farklı-sayfa senaryosu test edilmiş. Kod incelemesiyle mantıksal doğruluk teyit edildi ama red-team'e iletiliyor.
- AC-5 (sayfa-dışı bölge atlama) için doğrudan bir test yok, sadece kod incelemesi — düşük öncelik.
