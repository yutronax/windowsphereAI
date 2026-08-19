# Plan — security-whitelist-generalization
_Reference: atdd.md_

## Files to Modify
| File | Why | Risk |
|------|-----|------|
| backend/security.py | AC-1/AC-S1: `validate_plan_paths` içindeki 4 ayrı `if step.operationType == X: _validate_single_path(...)` bloğu, `OperationType` → hedef-alan-adı eşlemesi (dict, 11 giriş: MERGE→mergedFileName, REDACT→redactedFileName, EXCEL_SORT→sortedFileName, EXCEL_CREATE→createdFileName, EXCEL_FILTER→filteredFileName, PDF_EXTRACT_PAGES→extractedFileName, PDF_DELETE_PAGES→remainingFileName, PDF_COMPRESS→compressedFileName, ZIP_CREATE→zippedFileName, ZIP_ADD→addedFileName, ZIP_MERGE→mergedZipFileName) kullanan tek bir döngüye çıkarılır. AC-2/AC-S2: `validate_rename_destinations`/`validate_merge_destinations`/`validate_redact_destinations`/`validate_excel_sort_destinations` (satır 171-413) TEK bir genelleştirilmiş fonksiyona (öneri: `validate_destination_collisions`) birleştirilir — aynı 11-girişlik eşlemeyi kullanır, RENAME'in `newFileNames` alanı (liste, tekil alan değil) özel olarak ele alınmalı. | high |
| backend/tests/test_security.py | Satır 191 ve 197'deki `validate_rename_destinations(...)` DOĞRUDAN çağrıları, yeni genelleştirilmiş fonksiyon adına güncellenmeli (fonksiyon kaldırılıyor). Ayrıca yeni 7 operasyon için AC-3/AC-4/AC-S1/AC-S2'yi kapatan testler (whitelist reddi + çakışma reddi, en az 2/operasyon = en az 14 yeni test) eklenir. | medium |

## New Files
Yok.

## Dependencies
- `backend/models.py`'deki `OperationType` enum'ı ve `PlanStep`'in tüm hedef-alan
  isimleri (`mergedFileName`, `redactedFileName`, `sortedFileName`,
  `createdFileName`, `filteredFileName`, `extractedFileName`,
  `remainingFileName`, `compressedFileName`, `zippedFileName`,
  `addedFileName`, `mergedZipFileName`) — hepsi `str | None = None`,
  Pydantic model_validator'ları zaten operationType'a göre zorunluluğu
  garanti ediyor (security.py bunu tekrar doğrulamak zorunda değil, sadece
  `None` ise atlamalı).
- RENAME operasyonu ÖZEL DURUM: hedef alanı `newFileNames: list[str] | None`
  (TEKİL değil, LİSTE) — genelleştirilmiş dict/döngü tasarımı bunu
  `fileNames`/`newFileNames` çiftleri olarak ayrıca ele almalı, tek-alan
  varsayımı RENAME için çalışmaz. Mevcut `validate_rename_destinations`
  zaten bunu `zip(step.fileNames, step.newFileNames or [])` ile yapıyor —
  genelleştirilmiş fonksiyon bu deseni RENAME için korumalı, diğer 10
  operasyon için tekil-alan desenini kullanmalı.
- `backend/orchestrator.py` satır 642 SADECE `validate_plan_paths`'i
  çağırıyor (diğer 4 fonksiyona doğrudan bağımlılığı yok) — bu dosyada
  değişiklik gerekmez, import listesi (satır 17) zaten sadece
  `validate_plan_paths`'i alıyor.
- `backend/tests/test_orchestrator.py` de dolaylı olarak `validate_plan_paths`'e
  bağımlı (her `apply_plan` çağrısı önce onu çalıştırır) — regresyon riski
  bu dosyanın TÜM suite'inin (142 test) yeşil kalmasıyla ölçülür, ayrıca
  değiştirilmeyecek.

## Migration Required?
Hayır — sadece Python fonksiyon/dosya değişikliği, şema/veri değişikliği yok.

## Risks
- (atdd.md'den taşındı) 4 mevcut çakışma fonksiyonunun `all_destinations`
  listeleri BİRBİRİNDEN FARKLI kapsamdaydı (rename → rename+merge →
  +redact → +excel_sort, kümülatif). Genelleştirilmiş TEK fonksiyon TÜM
  11 operasyonun hedeflerini TEK bir listede toplayacağı için bu kümülatif
  fark ortadan kalkacak — davranışsal olarak DAHA GENİŞ bir çapraz-kontrol
  (ör. artık bir EXCEL_FILTER hedefi bir ZIP_CREATE hedefiyle de çakışma
  kontrolünden geçecek, önceden birbirini hiç görmüyorlardı). Bu bilinçli
  ve istenen bir davranış (atdd.md AC-2), ama mevcut testlerin BEKLEMEDİĞİ
  yeni bir çapraz-kontrol olduğu için dikkatli doğrulanmalı.
- test_security.py'nin satır 191/197'deki doğrudan `validate_rename_destinations`
  çağrıları unutulursa import hatası (ImportError) verir — code-copilot/
  test-copilot bu iki satırı MUTLAKA güncellemeli.
- RENAME'in liste-tipi (`newFileNames`) diğer 10 operasyonun tekil-tipinden
  (`str | None`) farklı olması, dict-driven tasarımın "her operasyon → tek
  alan adı" varsayımını RENAME için kırıyor — implementasyon bunu özel
  olarak ele almalı (bkz. Dependencies).

## Open Questions
Yok — atdd.md'deki kullanıcı onaylarıyla (tek genel fonksiyon, mevcut 4'ü
de dahil et, whitelist+çakışma ikisi de genelleştirilsin) kapsam net.
