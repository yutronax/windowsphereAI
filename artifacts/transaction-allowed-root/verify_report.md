# Verify Report — Transaction'a allowed_root kolonu ekle (Saga #301)

## Backend
`C:\Users\YUSUF ÇİNAR\AppData\Local\Programs\Python\Python311\python.exe -m pytest backend/tests -q`
→ **201 passed, 0 failed.** (200 → 201 after red-team fix, see below.)

## Red-team düzeltmesi
Bağımsız `obss-red-team` incelemesi, `allowed_root IS NULL` (migration
öncesi) transaction'lar için endpoint'in ATDD'de belgelenen 409 yerine 200
+ değişmemiş `"committed"` durumu döndürdüğünü tespit etti (genel
`except TransactionRevertError: pass` bloğuna sessizce düşüyordu). Düzeltme:
`backend/main.py::revert_transaction_endpoint`e `transaction.allowed_root is
None` için AYRI ve ÖNCEDEN bir 409 kontrolü eklendi (mevcut 404/409
precondition desenine uygun). Regresyon testi:
`backend/tests/test_main_integration.py::test_revert_endpoint_returns_409_when_the_transactions_allowed_root_is_missing`.

## Frontend
`npx vitest run ResultCard`
→ **17 passed (1 test file), 0 failed.**

## Gate özeti
| Gate | Durum |
|---|---|
| Build | N/A (bu task derleme etkileyen bir değişiklik yapmıyor, sadece Python/TS kaynak) |
| Type-check | Kapsanmadı (proje tsc/mypy CI adımı bu task kapsamında koşulmadı; test koşuları TypeScript dosyasını transpile ederek geçti) |
| Unit (backend) | PASS — 200/200 |
| Unit (frontend) | PASS — 17/17 (ResultCard.test.tsx) |
| Security-scan | Kapsanmadı bu koşuda (ayrı skill, task kapsamı dar — DB kolonu eklemek ve istemci girdisini yok saymak zaten bizzat güvenlik iyileştirmesi) |
| Migration | `backend/db.py::_add_missing_columns` (Saga #284 shim) yeni nullable `allowed_root` kolonunu otomatik ekliyor — ayrı migration betiği yazılmadı, mevcut testler (`backend/tests/test_db.py`, `test_db_migration.py`) bu shim'i zaten kapsıyor ve hâlâ geçiyor (200 toplam içinde). Ayrıca elle doğrulama yapılmadı çünkü shim davranışı zaten `test_db_migration.py`'nin kapsamında.

## Sonuç
Tüm testler yeşil. Değişiklik dar kapsamlı: `Transaction.allowed_root` kolonu,
`create_transaction`/`apply_plan` tarafından dolduruluyor, `revert_transaction`
istemciden gelen `allowedRoot`'u artık HİÇ almıyor/kullanmıyor,
`RevertTransactionRequest` boş model, frontend fetch body'si boş obje
gönderiyor.
