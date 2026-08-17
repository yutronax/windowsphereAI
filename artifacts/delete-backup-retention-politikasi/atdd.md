---
task_slug: delete-backup-retention-politikasi
priority: medium
coverage_target: "80/0/20"
performance_target: "yok"
test_strategy: "unit (pytest, gerçek geçici dosya sistemi)"
affected_modules:
  - backend/orchestrator.py
saga_task_id: 300
epic_id: 28
---

# ATDD — DELETE Yedek Klasörü Retention/Temizlik Politikası (Saga #300)

## Goal
`allowed_root/.windows-ai-files-backup/<transaction_id>/` klasörü
DELETE işlemlerinin fiziksel yedeklerini SONSUZA DEK saklıyor. Bir
retention politikası + onu uygulayan bir fonksiyon eklemek.

## Sorular ve Cevaplar (saga-oto tarafından otomatik seçildi)

**S1: Hangi politika — (a) otomatik süre bazlı, (b) kullanıcının elle
tetiklediği, (c) hiç temizlik yok, sadece UI'da gösterim?** Cevap:
**(a) Otomatik süre bazlı, varsayılan 30 gün.** Bu, task'ın kendi
açıklamasındaki önerilen seçeneklerden en somut/otomatik-test edilebilir
olanı; (b)/(c) bir UI/ayarlar bileşeni gerektirir ki bu epic'in UI
kısmı zaten Saga #295'te tamamlandı ve yeni bir ayarlar ekranı İCAT
ETMEK bu task'ın kapsamını aşar (YAGNI). (saga-oto tarafından otomatik
seçildi — dar kapsam, somut/test edilebilir varsayılan)

**S2: KRİTİK güvenlik bulgusu (kod keşfinde ortaya çıktı, task
açıklamasında yoktu): yedek fiziksel olarak silinirse ama
`Transaction.status` hâlâ `"committed"` kalırsa ne olur?** Cevap:
`revert_transaction`in `_rollback_completed_operations`i, hedef
(`destination_path` = gizli yedek konumu) fiziksel olarak YOKSA bunu
"zaten geri alınmış" sayıp SESSİZCE `"rolled_back"` işaretliyor
(`orchestrator.py` satır 147-149) — backup PURGE EDİLMİŞ bir
transaction'ı geri almaya çalışmak, dosyayı GERÇEKTEN GERİ GETİRMEDEN
"başarılı" görünürdü. Bu, KULLANICI VERİSİ KAYBINI SESSİZCE MASKELERDİ.
Çözüm: purge edilen transaction'lar YENİ bir `"backup_purged"` durumuna
geçirilir — `revert_transaction`in ZATEN VAR OLAN "sadece committed
transaction'lar geri alınabilir" kontrolü (Saga #293) bunu OTOMATİK
OLARAK 409/`TransactionRevertError` ile reddeder (kod DEĞİŞİKLİĞİ
GEREKMEDİ, mevcut guard'ın doğal bir sonucu). (saga-oto tarafından
otomatik seçildi — güvenlik-kritik, sessiz veri kaybını önler)

**S3: KARIŞIK operasyonlu transaction'lar (ör. aynı transaction'da hem
MOVE hem DELETE) nasıl ele alınmalı?** Cevap: PURGE EDİLMEZ — sadece
TÜM operasyonları DELETE olan ("saf DELETE") transaction'lar purge
uygunluğuna girer. Karışık bir transaction'ı purge etmek, MOVE/RENAME
kısımlarının backup_path'i (orijinal konum, gizli klasör DEĞİL)
ETKİLENMEDİĞİ halde TÜM transaction'ı `"backup_purged"` yapıp
geri-alınamaz kılardı — bu, gerçekte hâlâ geri alınabilir MOVE/RENAME
adımlarını haksız yere kilitlerdi. Kısmi-purge (transaction içindeki
sadece DELETE adımlarını purge edip diğerlerini bırakma) bu task'ın
kapsamını aşan bir tasarım genişletmesi, dar kapsamla ATLANDI ve not
edildi. (saga-oto tarafından otomatik seçildi — dar kapsam, güvenli
varsayılan: belirsizlikte purge ETME)

**S4: Bu fonksiyon bir zamanlayıcıya/FastAPI startup event'ine
BAĞLANMALI MI?** Cevap: HAYIR, henüz değil — `recover_incomplete_transactions`
(Saga #286/#287) ile AYNI emsal: saf, çağrılabilir bir fonksiyon.
Gerçek bir zamanlama mekanizması (APScheduler, Tauri sidecar cron vb.)
henüz projenin hiçbir yerinde YOK — icat etmek büyük bir mimari
genişleme, bu task'ın kapsamı dışında. (saga-oto tarafından otomatik
seçildi — mevcut `recover_incomplete_transactions` emsaline tutarlı)

## Kabul Kriterleri
1. **AC-1 (kritik):** `purge_expired_delete_backups(session, allowed_root, older_than_days=30, now=None)`
   fonksiyonu var — `created_at`i `now - older_than_days`ten ESKİ,
   `status == "committed"` VE TÜM operasyonları DELETE olan
   transaction'ların gizli yedek klasörünü fiziksel olarak siliyor.
2. **AC-2 (kritik):** Purge edilen transaction `"backup_purged"`
   durumuna geçiyor — bu durumdaki bir transaction `revert_transaction`e
   verilirse (mevcut guard sayesinde, kod değişikliği gerekmeden)
   `TransactionRevertError` fırlatılıyor, HİÇBİR SESSİZ "başarılı"
   görünümü YOK.
3. **AC-3 (yüksek):** Karışık operasyonlu (DELETE + başka bir tür)
   transaction'lar PURGE EDİLMİYOR, `"committed"` kalıyor.
4. **AC-4 (orta):** `created_at`i eşikten YENİ olan committed DELETE
   transaction'ları PURGE EDİLMİYOR.
5. **AC-5 (orta):** Fonksiyon çağrılabilir ama HİÇBİR startup/scheduler
   akışına bağlanmadı (mevcut kod ile SIFIR entegrasyon değişikliği).

## Riskler / Varsayımlar / Bilinmeyenler
- Gerçek bir zamanlama/tetikleme mekanizması henüz yok — bu fonksiyon
  şimdilik manuel/gelecekteki bir cron/startup görevi tarafından
  çağrılmayı bekliyor (Saga #286/#287 ile aynı durum).
- Karışık-operasyonlu transaction'lar için kısmi purge desteklenmiyor
  (S3'te belgelendi) — gelecekte gerçek bir ihtiyaç ortaya çıkarsa ayrı
  bir task gerekir.

## Test Stratejisi
`backend/tests/test_orchestrator.py`: gerçek geçici klasörde saf-DELETE
bir transaction eski `created_at` ile oluşturulup purge edilir (backup
klasörünün fiziksel olarak silindiği + status'un `backup_purged`
olduğu doğrulanır); eşikten yeni olan bir transaction'ın
DOKUNULMADIĞI; karışık-operasyonlu bir transaction'ın PURGE
EDİLMEDİĞİ; purge edilmiş bir transaction'ın `revert_transaction`e
verilince reddedildiği (mevcut guard'ın doğal sonucu, regresyon testi).
