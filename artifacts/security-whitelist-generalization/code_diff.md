# Code Diff — security-whitelist-generalization

Codex kotası dolu olduğu için (15 Eylül 2026'ya kadar) bu değişiklik
kullanıcı onayıyla Claude Haiku alt ajanı (`efektor` subagent) tarafından
yazıldı — plan.md'nin "Files to Modify" listesindeki dosyalarla sınırlı,
ARTI bir regresyon düzeltmesi için `backend/tests/test_orchestrator.py`'de
1 satırlık ek değişiklik (aşağıda ayrıca not edildi).

## Değiştirilen dosyalar
- `backend/security.py`
- `backend/tests/test_security.py`
- `backend/tests/test_orchestrator.py` (plan.md'nin öngörmediği, ama
  değişikliğin doğal sonucu olan 1 satırlık regresyon düzeltmesi)

## backend/security.py
1. **`_DESTINATION_FIELD_BY_OPERATION`** (yeni sabit sözlük, satır 174-186):
   `OperationType` → hedef-alan-adı eşlemesi, 11 operasyon (MERGE, REDACT,
   EXCEL_SORT, EXCEL_CREATE, EXCEL_FILTER, PDF_EXTRACT_PAGES,
   PDF_DELETE_PAGES, PDF_COMPRESS, ZIP_CREATE, ZIP_ADD, ZIP_MERGE). RENAME
   kasıtlı olarak dict'te yok (hedefi `newFileNames` — liste, tekil alan
   değil).
2. **`validate_plan_paths`** (satır 138-155): eski 4 ayrı
   `if step.operationType == X: _validate_single_path(...)` bloğu, dict
   üzerinden tek bir döngüye + RENAME'in ayrı ele alınmasına dönüştürüldü
   (AC-1, AC-S1). Sondaki 4 ayrı `validate_*_destinations` çağrısı, TEK
   `validate_destination_collisions` çağrısına indirildi.
3. **`validate_destination_collisions`** (yeni fonksiyon, satır 189-299):
   eski `validate_rename_destinations`/`validate_merge_destinations`/
   `validate_redact_destinations`/`validate_excel_sort_destinations`
   fonksiyonlarının (silindi) yerini alıyor. TÜM 11 operasyon + RENAME'in
   hedeflerini tek bir listede toplayıp: (a) plan-içi çapraz çakışma,
   (b) planın bilmediği var olan dosyayla çakışma, (c) RENAME'e özel
   zincirleme kaynak/hedef kontrolünü tek yerde yapıyor (AC-2, AC-S2).
   Mevcut 4 fonksiyonun docstring'lerindeki red-team bulgu notları
   (case-insensitive normalize, zincirleme rename vb.) korundu.

## backend/tests/test_security.py
- Import: `validate_rename_destinations` → `validate_destination_collisions`.
- Satır 191/197'deki doğrudan çağrılar yeni fonksiyon adına güncellendi.
- Yeni 7 operasyonun her biri için 2'şer test eklendi (14 yeni test):
  whitelist reddi (`allowed_root` dışına çıkma) + çakışma reddi (planın
  bilmediği var olan dosya).
- Toplam: 40 test (26 eski + 14 yeni).

## backend/tests/test_orchestrator.py (plan.md'nin öngörmediği ek değişiklik)
`test_apply_plan_rejects_excel_create_when_target_already_exists` testinin
beklediği exception tipi `PlanApplicationError` → `PathWhitelistError`
olarak güncellendi. Gerekçe: genelleştirilmiş `validate_destination_collisions`
artık `apply_plan`'ın kendi EXCEL_CREATE-özel "hedef zaten var" kontrolünden
ÖNCE, `validate_plan_paths` aşamasında bu çakışmayı yakalıyor — davranış
DAHA ERKEN ve DAHA GENEL bir katmanda tespit ediliyor (AC-S2'nin doğal
sonucu), dosyaya dokunulmadığı (orijinal içerik korunuyor) doğrulaması
aynı kalıyor. Bu, plan.md'nin "Risks" bölümünde önceden öngörülen bir
senaryoydu ("genelleştirilmiş kontrol artık daha geniş, mevcut testlerin
BEKLEMEDİĞİ yeni bir çapraz-kontrol").

## Red-team follow-up: IMAGE_CROP/IMAGE_THUMBNAIL eklendi
Bağımsız red-team turu, atdd.md'nin Kapsam Dışı bölümünün YANLIŞ bir
varsayım içerdiğini buldu: IMAGE_CROP/IMAGE_THUMBNAIL "hedef dosya adı
üretmiyor" denilerek dışlanmıştı, oysa `models.py` bunların
`croppedFileName`/`thumbnailFileName` ile EXCEL_FILTER'la aynı desende
gerçek hedef ürettiğini gösteriyordu — bu görevin kapatmaya çalıştığı açık
sınıfının aynısı. Commit'ten önce düzeltildi:
- `_DESTINATION_FIELD_BY_OPERATION` dict'ine 2 giriş eklendi (`security.py`
  satır 187-188) — artık 13 operasyon kapsanıyor.
- `test_security.py`'ye 4 yeni test eklendi (IMAGE_CROP/IMAGE_THUMBNAIL ×
  whitelist-reddi/çakışma-reddi).
- `atdd.md`'nin Kapsam Dışı listesi düzeltildi.

## Doğrulama
```
./.venv/Scripts/python.exe -m pytest backend/tests/test_security.py -v
44 passed in 0.86s

./.venv/Scripts/python.exe -m pytest backend/
540 passed, 5 skipped in 28.49s
```
Bağımsız olarak (subagent raporundan ayrı) iki kez çalıştırıldı (ilk yazım
+ IMAGE_CROP/IMAGE_THUMBNAIL düzeltmesi sonrası), her ikisinde de aynı
sonuç, 0 FAIL.
