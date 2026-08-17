# Plan — Entry katmanı normalizasyonu (Saga #268)

## Yeni dosya
- `backend/request_normalization.py`
  - `normalize_request_text(text: str) -> str`: `text.strip()` döner;
    trim sonrası boşsa `ValueError` fırlatır.

## Değiştirilecek dosya
- `backend/models.py`
  - `SessionRequest.not_blank` validator'ı `requestText` alanı için
    `normalize_request_text` kullanacak şekilde güncellenir (trim edilmiş
    değeri DÖNDÜRÜR — mevcut kod trim etmiyordu, bu bir bug fix).
    `selectedFolder` için mevcut boş-kontrolü korunur (trim davranışı
    gerekmiyor, klasör yolları baştan/sondan boşluk almaz — Windows
    yol semantiği).

## Yeni test dosyası
- `backend/tests/test_request_normalization.py`

## Güncellenecek test dosyası
- `backend/tests/test_main_integration.py` — trim edilmiş requestText'in
  gerçekten trim edilmiş olarak döndüğünü doğrulayan yeni bir entegrasyon
  testi.

## Yeni bağımlılık yok
