---
task_slug: rollback-bagimsiz-fonksiyon
priority: high
coverage_target: "80/0/20"
performance_target: "yok"
test_strategy: "unit (pytest, gerçek geçici dosya sistemi — mevcut test_orchestrator.py deseniyle tutarlı)"
affected_modules:
  - backend/orchestrator.py
saga_task_id: 293
epic_id: 28
---

# ATDD — apply_plan Rollback Mantığının Bağımsız Fonksiyona Çıkarılması (Saga #293)

## Goal
`apply_plan`'ın except-bloğundaki rollback mantığı (satır 231-263) şu an
SADECE kendi hata anında çalışıyor. Kullanıcının BAŞARIYLA TAMAMLANMIŞ
("committed") bir transaction'ı SONRADAN manuel geri alabilmesi için bu
mantık paylaşılan bir yardımcıya çıkarılıp, üstüne `revert_transaction`
adında yeni bir public fonksiyon eklenmeli.

## Sorular ve Cevaplar (saga-oto tarafından otomatik seçildi)

**S1: Paylaşılan yardımcı fonksiyonun sınırı nerede olmalı?** Cevap:
Mevcut except-bloğunun 231-263 satırları arası (tek bir operation'ı
geri alma + exists-check + OSError/ValueError/KeyError yutma +
status="rolled_back"/"rollback_failed" atama) `_rollback_completed_operations(operations) -> bool`
adında private bir yardımcıya çıkarılır (tüm başarılıysa True döner).
`apply_plan`'ın except-bloğu ve yeni `revert_transaction` bu TEK
fonksiyonu çağırır — kod tekrarı olmaz. (saga-oto tarafından otomatik
seçildi — mevcut mantığa dokunmadan en dar refactor)

**S2: `revert_transaction` hangi transaction durumlarını kabul eder?**
Cevap: SADECE `status == "committed"`. Zaten `pending`/`rolled_back`/
`reverted` bir transaction'ı geri almak anlamsız/tehlikeli (ör.
`rolled_back` bir transaction'ı tekrar "geri almak" dosyaları YANLIŞ
yöne taşır) — bu durumlarda `TransactionRevertError` fırlatılır, hiçbir
dosyaya dokunulmaz. (saga-oto tarafından otomatik seçildi — güvenli
varsayılan, dar kapsam)

**S3: Kısmi başarısız revert durumunda transaction'ın nihai durumu ne
olmalı?** Cevap: Yeni iki durum: tümü başarılıysa `"reverted"`, en az
biri `"rollback_failed"` ise transaction `"revert_failed"`. Her iki
durumda da DB'ye commit edilir (kısmi ilerleme asla sessizce kaybolmaz,
`apply_plan`'ın kendi except-bloğuyla AYNI ilke), `revert_failed`
durumunda fonksiyon `TransactionRevertError` fırlatır ki çağıran (ör.
gelecekteki endpoint) kullanıcıya net bir hata gösterebilsin. (saga-oto
tarafından otomatik seçildi — apply_plan'ın "asla sessiz kısmi başarı"
ilkesiyle simetrik)

**S4: `allowed_root` parametresi neden gerekli, DB'deki path'lere
güvenilmiyor mu?** Cevap: Savunma derinliği (defense-in-depth) —
`revert_transaction` DB'den okuduğu `destination_path`/`backup_path`
değerlerini DOĞRUDAN `shutil.move` ile kullanacağı için, bu path'lerin
HÂLÂ `allowed_root` altında olduğu `security.py: is_path_allowed` ile
tekrar doğrulanır (orijinal `validate_plan_paths` sadece PlanStep
seviyesinde, `apply_plan` çağrısı ANINDA çalışıyordu — DB satırları
sonradan bozulmuş/manipüle edilmiş olabilir teorik olarak). Path
`allowed_root` dışındaysa o operasyon atlanır, `"rollback_failed"`
işaretlenir (asla whitelist dışına yazma girişiminde bulunulmaz).
(saga-oto tarafından otomatik seçildi — mevcut projenin whitelist
disiplinine [Saga #272/#283] tutarlı genişleme)

## Kabul Kriterleri
1. **AC-1 (kritik):** `_rollback_completed_operations` yardımcı
   fonksiyonu var, `apply_plan`'ın except-bloğu VE `revert_transaction`
   AYNI fonksiyonu çağırıyor (kod tekrarı yok).
2. **AC-2 (kritik):** `revert_transaction(session, transaction, allowed_root) -> Transaction`
   committed bir transaction'ın tüm `completed` operasyonlarını TERS
   SIRAYLA geri alıyor, MOVE/COPY/DELETE/RENAME hepsi için doğru
   çalışıyor.
3. **AC-3 (yüksek):** `status != "committed"` olan bir transaction
   `revert_transaction`'a verilirse hiçbir dosyaya dokunulmadan
   `TransactionRevertError` fırlatılıyor.
4. **AC-4 (yüksek):** Bir rollback adımı fiziksel olarak başarısız
   olursa (ör. hedef dosya kilitli/silinmiş) transaction
   `"revert_failed"` olarak işaretleniyor VE `TransactionRevertError`
   fırlatılıyor, ama BAŞARILI olan diğer operasyonların durumu
   (`"rolled_back"`) DB'ye kaydedilmiş kalıyor.
5. **AC-5 (orta):** Mevcut `apply_plan` davranışı (kendi hata-anı
   rollback'i) BİREBİR aynı kalıyor — mevcut `test_orchestrator.py`
   testleri hiçbir değişiklik olmadan geçiyor.

## Riskler / Varsayımlar / Bilinmeyenler
- Bu task henüz bir HTTP endpoint'e bağlanmadı (Saga #294'ün işi) —
  `revert_transaction` şimdilik sadece çağrılabilir bir fonksiyon,
  `recover_incomplete_transactions` ile aynı durumda (Saga #286/#287).
- LIST operasyonları hiç `FileOperation` kaydı oluşturmadığı için
  (Saga #291) `revert_transaction`'ın işi zaten hiç görmüyor — ek bir
  filtre gerekmiyor.

## Test Stratejisi
`backend/tests/test_orchestrator.py`: gerçek geçici klasörde MOVE/COPY/
DELETE/RENAME içeren bir plan `apply_plan` ile commitlenir, ardından
`revert_transaction` çağrılıp dosyaların GERÇEKTEN eski konumlarına
döndüğü doğrulanır; `status != "committed"` reddi; kısmi başarısız
revert senaryosu (ör. hedefi silme/kilitleme simülasyonu).
