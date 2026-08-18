# ATDD — Saga #307: PDF OCR orchestrator entegrasyonunda allowed_root/is_path_allowed zorunlu

## Persona
Backend geliştirici / güvenlik incelemesi yapan red-team.

## Goal
Saga #306'da eklenen `backend/pdf_ocr.py::ocr_pdf_file(pdf_path)` fonksiyonu
şu an hiçbir endpoint/orchestrator'a bağlı değil ve ham bir `Path` alıyor.
Bu task, OCR'ı MERGE/SPLIT/DELETE ile AYNI desende `backend/orchestrator.py`
üzerinden yürütülen bir `OperationType` yapar — path validasyonu
`is_path_allowed`/`allowed_root` üzerinden merkezi noktada (orchestrator)
yapılır, `pdf_ocr.py`'ye asla ham/dış path geçirilmez.

## User Story
Bir plan step'i `operationType: "OCR"` içerdiğinde, orchestrator önce o
step'in kaynak dosyasının `allowed_root` altında olduğunu doğrular, SONRA
`ocr_pdf_file`'ı çağırır. `allowed_root` dışına çıkan bir path, diğer
operasyonlarla (MERGE/SPLIT/DELETE) aynı şekilde reddedilir.

## Sorular ve Cevaplar (saga-oto tarafından otomatik seçildi)
1. **OCR sonucu nereye yazılır/dönülür?** — Bu task'ın kapsamı SADECE
   path-validation güvenlik açığını kapatmak; OCR sonucunun bir dosyaya
   yazılması/DB'ye kaydedilmesi/endpoint'ten dönmesi KAPSAM DIŞI (henüz
   hiçbir endpoint OCR'ı çağırmıyor, Saga #306 açıklamasında da böyle).
   `apply_plan` OCR step'i LIST gibi "inert" (dosya sistemini
   DEĞİŞTİRMEZ) ama LIST'ten farklı olarak GERÇEKTEN OCR'ı ÇALIŞTIRIR
   (yan etkisiz, sadece okuma) — sonucu şimdilik atılır (discard).
   (saga-oto tarafından otomatik seçildi — dar kapsam ilkesi)
2. **OCR birden fazla dosya/step'te birden fazla kaynak alabilir mi?**
   — Hayır, SPLIT ile AYNI kısıt: `fileNames` TAM OLARAK 1 kaynak
   içermeli (OCR "1 PDF -> sayfa metinleri" anlamına geliyor, N kaynağı
   tek step'te OCR'lamak belirsizlik yaratır). (saga-oto tarafından
   otomatik seçildi — SPLIT ile tutarlılık ilkesi)
3. **`targetFolder` OCR için anlamlı mı?** — Hayır, DELETE/RENAME/MERGE/
   SPLIT ile aynı "bilinen sınırlama": şema gereği zorunlu ama
   kullanılmıyor. (saga-oto tarafından otomatik seçildi)
4. **Rollback gerekiyor mu?** — Hayır, OCR hiçbir dosyaya yazmıyor/
   taşımıyor, LIST gibi `FileOperation` kaydı da oluşturmuyor, rollback
   listesine hiç girmiyor. (saga-oto tarafından otomatik seçildi)
5. **`pdf_ocr.py`'de path-validasyon tekrarlanmalı mı?** — Hayır, red-team
   bulgusu ve proje kuralı (Saga #293 emsali) açıkça merkezi güvenlik
   noktasını (`orchestrator.py`) koruma talep ediyor; `pdf_ocr.py`
   DEĞİŞTİRİLMEZ. (görev tanımından doğrudan)

## Acceptance Criteria (öncelik sırasıyla)
- AC1 (P0): `OperationType.OCR` enum üyesi `backend/models.py`'ye eklenir,
  diğer üyelerle AYNI şekilde tanımlanır.
- AC2 (P0): `PlanStep`, `operationType == OCR` iken `fileNames` TAM OLARAK
  1 eleman içermeli (şema seviyesinde, SPLIT'in `file_names_length_exactly_one_for_split`
  validator'üyle AYNI desen).
- AC3 (P0): `apply_plan`, OCR step'inin kaynak dosyasını `allowed_root /
  fileNames[0]` olarak çözer, `is_path_allowed(source_path, allowed_root)`
  İLE DOĞRULAR, SADECE geçerse `backend.pdf_ocr.ocr_pdf_file(source_path)`
  çağırır.
- AC4 (P0): `allowed_root` dışına (veya derinlik/sistem-korumalı kök
  ihlaline) işaret eden bir OCR step'i, MERGE/SPLIT/DELETE ile AYNI
  mekanizma üzerinden (`validate_plan_paths` → `PathWhitelistError`, zaten
  `apply_plan`'ın en başında TÜM `pdf_files` için çalışıyor) reddedilir —
  `ocr_pdf_file` hiç çağrılmaz.
- AC5 (P1): `backend/pdf_ocr.py` DEĞİŞTİRİLMEZ (path-validasyon orada
  DUPLICATE edilmez).
- AC6 (P1): Var olan MERGE/SPLIT/DELETE testleri kırılmaz (regresyon yok).

## Davranış Sözleşmesi Tablosu
| Girdi | Beklenen Sonuç |
|---|---|
| `allowed_root` içinde geçerli 1 PDF, `operationType=OCR` | `ocr_pdf_file` çağrılır, `apply_plan` `transaction.status == "committed"` döner, hiçbir dosya taşınmaz/silinmez |
| `fileNames` `allowed_root` dışında bir dosyaya işaret ediyor (ör. `../../secret.pdf` gibi traversal sonrası dışarı çıkan bir isim `pdf_files` listesinde) | `PathWhitelistError` (veya `apply_plan` içinde eşdeğer red), `ocr_pdf_file` HİÇ ÇAĞRILMAZ, hiçbir dosya değişmez |
| OCR step'inde `fileNames` uzunluğu != 1 | Pydantic `ValidationError` (şema seviyesinde, `apply_plan`'a hiç ulaşmaz) |
| Kaynak dosya yok (`pdf_files` listesinde olmayan bir isim) | `PlanApplicationError` (`_distribute_files_to_steps`'in mevcut davranışı, değişmedi) |

## Risks / Assumptions / Unknowns
- Assumption: OCR sonucunun ne yapılacağı (endpoint, DB, response) ayrı
  bir Saga task'ı — bu task'ın kapsamı SADECE path-validation.
  (saga-oto tarafından otomatik seçildi — dar kapsam ilkesi)
- Risk: `pdf2image`/`pytesseract`/Poppler/Tesseract test ortamında kurulu
  olmayabilir — testler gerçek OCR çalıştırmak yerine `ocr_pdf_file`'ı
  `monkeypatch`/mock ile stub'layarak SADECE "çağrıldı mı / doğru path'le
  mi çağrıldı" davranışını doğrulamalı (gerçek OCR motoru zaten
  `pdf_ocr.py`'nin kendi sorumluluğu, Saga #306'da test edildi).

## Test Strategy
100% unit (orchestrator.apply_plan + models.PlanStep validator), test
piramidi zaten projede unit-ağırlıklı — e2e gerekmiyor (henüz hiçbir HTTP
endpoint OCR'ı tetiklemiyor).

## Benchmark
Yok (performans hedefi bu task'ın kapsamında değil).
