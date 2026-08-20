# Plan — pdf-pii-tespiti
_Reference: atdd.md_

## Files to Modify
| File | Why | Risk |
|------|-----|------|
| backend/models.py | AC-1/AC-4: `DetectPiiRequest` (`sessionId`, `filename` — `ExcelReadRequest`/`ZipListRequest`'in BİREBİR aynı `filename_has_no_path_separators` field_validator deseni) ve `DetectPiiResponse` (`regions: list[RedactionRegion]`) şemaları eklenir. `RedactionRegion` zaten mevcut, DEĞİŞMEZ. | low |
| backend/main.py | AC-1/AC-2/AC-4: `get_session_for_detect_pii` (session lookup, `excel_read_endpoint`'in `get_session_for_excel_read`'iyle BİREBİR aynı desen) + `POST /api/pdf/detect-pii` endpoint'i (session/allowed_root doğrulama → `source_path.is_file()` 404 → `pdf_pii.detect_pii(source_path)` çağrısı → `DetectPiiResponse`). `excel_read_endpoint`/`zip_list_endpoint`'in (satır 594-663) TAM AYNI 3-katmanlı hata deseni: 410 (klasör yok) → 404 (dosya yok) → 422 (okuma/işleme hatası). | medium |

## New Files
| File | Purpose |
|------|---------|
| backend/pdf_pii.py | AC-1/AC-3/AC-5/AC-S1/AC-S2: `detect_pii(pdf_path: Path) -> list[RedactionRegion]`. TC kimlik no checksum fonksiyonu (`_is_valid_tc_kimlik_no`), sabit-uzunluklu regex kalıpları (`\d{11}` TC, `TR\d{24}` IBAN — AC-S2), `pypdf`'in `visitor_text` callback'iyle her sayfa için metin+konum toplanır, regex eşleşen aralıkların bounding box'ı hesaplanır, geçersiz/sayfa-dışı olanlar atlanır (AC-5), fonksiyon SADECE `RedactionRegion` listesi döner — eşleşen ham değer hiçbir yerde tutulmaz/loglanmaz (AC-S1). |
| backend/tests/test_pdf_pii.py | AC-1..AC-5, AC-S1, AC-S2 için unit+integration testler. |

## Dependencies
- `backend/pdf_redact.py` ve `backend/tests/test_pdf_redact.py`'nin
  `RedactionRegion` koordinat sözleşmesi (satır 119-128: PDF NOKTA uzayı,
  SOL-ALT kökenli) — `pdf_pii.py`'nin ürettiği bounding box'lar bu
  sözleşmeyle TUTARLI olmalı. pypdf'in `visitor_text` callback'i
  `transform_matrix`'ten `(x, y)` verir; bu koordinatlar PDF'in kendi
  content-stream uzayında ZATEN sol-alt kökenlidir (pypdf PDF spec'ini
  izler) — ek bir dönüşüm/flip GEREKMEZ, ama gerçek bir PDF ile bu
  test-copilot aşamasında DOĞRULANMALI (atdd.md Risks'te zaten işaretli).
- `backend/main.py`'deki `excel_read_endpoint`/`zip_list_endpoint` (satır
  594-663) TAM olarak taklit edilecek "salt-okunur senkron sorgu" deseni:
  session lookup → `allowed_root.is_dir()` 410 → `source_path.is_file()`
  404 → işlem hatası 422. Bu endpoint'ler `_validate_single_path`/
  `validate_plan_paths` (Saga #338'in Plan-operasyonu whitelist'i)
  ÇAĞIRMIYOR — sadece `filename_has_no_path_separators` field_validator'ına
  güveniyorlar. Yeni endpoint TUTARLILIK için AYNI (daha hafif) deseni
  kullanacak — bu, Plan/apply_plan operasyonlarından FARKLI bir kod yolu
  (aşağıda Risks'te detaylandırıldı).
- `backend/models.py`'deki `RedactionRegion` (satır 119-128) — mevcut
  alan adları (`page`, `x0`, `y0`, `x1`, `y1`) birebir kullanılacak, yeni
  bir alan eklenmeyecek.

## Migration Required?
Hayır — sadece yeni Python kod + yeni Pydantic şemaları, şema/veri
değişikliği yok.

## Risks
- (atdd.md'den taşındı) pypdf `visitor_text`'in transform matrisi farklı
  PDF üreticilerinde tutarsız olabilir — test-copilot gerçek bir örnekle
  doğrulamalı.
- **Yeni (plan aşamasında bulundu):** `excel_read_endpoint`/`zip_list_endpoint`
  deseni (bu görevin de takip edeceği) `_validate_single_path`/
  `validate_plan_paths`'ı ÇAĞIRMIYOR — sadece field-seviyesi ayraç-engelleme
  validator'ına güveniyor. Bu, Saga #338'in Plan-operasyonları için
  kapattığı sınıfla AYNI (düşük riskli, sadece TAM OLARAK ".." değeriyle
  tetiklenebilen) boşluk, ama BU endpoint sınıfı (salt-okunur sorgular)
  hiç Saga #338'in kapsamında değildi. Bu görev bu boşluğu KAPATMIYOR
  (kapsamı değil), sadece MEVCUT deseni tekrarlıyor — tutarlılık tercih
  edildi, yeni bir whitelist mekanizması icat edilmedi. Kullanıcıya
  bildirilmeli, isterse ayrı bir takip görevi açılabilir.

## Open Questions
Yukarıdaki risk (mevcut `excel_read`/`zip_list` deseninin whitelist
zayıflığı) bir açık soru değil — atdd.md AC-4 zaten "mevcut whitelist
mekanizmasına TUTARLI" diyordu, bu plan o tutarlılığı MEVCUT (aynı sınıf)
davranışla sağlıyor. Yeni bir kullanıcı kararı gerekmiyor.
