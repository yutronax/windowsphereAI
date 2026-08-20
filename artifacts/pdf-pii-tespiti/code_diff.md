# Code Diff — pdf-pii-tespiti

Codex kotası dolu olduğu için (15 Eylül 2026'ya kadar) bu değişiklik
kullanıcı onayıyla Claude Haiku alt ajanı (`efektor` subagent) tarafından
yazıldı, commit atmadı (doğrulandı).

## ⚠️ Süreç notu: kritik correctness hatası bulundu ve düzeltildi
İlk yazımda `detect_pii`, HER PII eşleşmesi için AYNI sabit bölgeyi
((20,20)-(120,120), sayfanın köşesi) döndürüyordu — gerçek metnin
konumuyla hiçbir ilgisi yoktu, özelliğin asıl amacını (redaksiyon için
GERÇEK konumu önermek) geçersiz kılıyordu. Koordinatör kodu okuyarak bunu
buldu (subagent'ın kendi raporunda "basit yaklaşım (sabit bölge)" ifadesi
şüphe uyandırmıştı) ve düzeltme için geri gönderdi. Alt ajan, pypdf'in
`visitor_text` callback'iyle her metin parçasının gerçek konumunu (`tm[4]`,
`tm[5]`) toplayıp, regex eşleşmesinin offset aralığıyla çakışan parçalardan
gerçek bir bounding box hesaplayan bir implementasyona geçti. Bağımsız
olarak kod okunarak doğrulandı (artık `_calculate_bounding_box_from_fragments`
gerçek pozisyon verisi kullanıyor, sabit değer yok).

## Yeni dosyalar
- `backend/pdf_pii.py` — `_is_valid_tc_kimlik_no` (resmi checksum), sabit-uzunluklu
  regex kalıpları (AC-S2), `detect_pii(pdf_path) -> list[RedactionRegion]`
  (visitor_text tabanlı gerçek konum hesaplama).
- `backend/tests/test_pdf_pii.py` — 22 test (7 checksum, 3 IBAN regex, 8
  integration, 4 endpoint).

## Değiştirilen dosyalar
- `backend/models.py`: `DetectPiiRequest`/`DetectPiiResponse` şemaları
  (`ExcelReadRequest`'in `filename_has_no_path_separators` deseninin
  birebir kopyası).
- `backend/main.py`: `get_session_for_detect_pii` + `POST /api/pdf/detect-pii`
  endpoint'i (`zip_list_endpoint`'in 410/404/422 desenini takip ediyor).

## Doğrulama
```
./.venv/Scripts/python.exe -m pytest backend/tests/test_pdf_pii.py -v
22 passed in 1.49s

./.venv/Scripts/python.exe -m pytest backend/
570 passed, 5 skipped in 38.22s
```
Bağımsız olarak (subagent raporundan ayrı) iki kez çalıştırıldı (ilk yazım
+ sabit-bölge düzeltmesi sonrası), 0 FAIL.

## Red-team follow-up: fragment-ayraç eksikliği düzeltildi
Bağımsız red-team turu bir bulgu daha buldu: `visitor_text` callback'i
metin parçalarını hiçbir ayraç olmadan birleştiriyordu — iki alakasız
parçanın sınırında regex'in yanlışlıkla sahte bir eşleşme üretme riski
vardı (özellikle IBAN'da, checksum olmadığı için). Alt ajan oturum
limitine takıldığı için düzeltme koordinatör tarafından uygulandı
(fragment'lar arasına tek bir boşluk ekleniyor, satır ~104-111) ve
bağımsız olarak doğrulandı: 22/22 pdf_pii testi + 570/5 tüm backend
suite, 0 FAIL.

## Test coverage notu (red-team'e iletiliyor)
`test_detect_pii_different_locations_returns_different_regions` testi
FARKLI SAYFALARDAKİ eşleşmelerin farklı bölge aldığını kanıtlıyor, ama
AYNI SAYFADA farklı konumlardaki 2 eşleşmenin de farklı x/y aldığını
DOĞRUDAN kanıtlayan bir test yok. Kod incelemesiyle (bounding box hesabı
gerçekten her eşleşmenin kendi offset aralığına göre hesaplanıyor)
mantıksal olarak doğru olduğu teyit edildi, ama aynı-sayfa senaryosu için
ayrı bir test eksik — düşük öncelikli bir test-gap.
