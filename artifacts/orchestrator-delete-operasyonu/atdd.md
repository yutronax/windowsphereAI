---
task_slug: orchestrator-delete-operasyonu
priority: high
coverage_target: "70/0/30"
performance_target: "yok"
test_strategy: "unit (pytest, tmp_path + in-memory sqlite)"
affected_modules:
  - backend/orchestrator.py
saga_task_id: 289
epic_id: 26
---

# ATDD — DELETE Operasyonu (Saga #289)

## Goal
`apply_plan`'a `OperationType.DELETE` desteği eklemek: silmeden önce
GERÇEK bir fiziksel yedek alınır, sonra kaynak silinir. Rollback yedeği
orijinal konuma geri getirir.

## Sorular ve Cevaplar (saga-oto tarafından otomatik seçildi)

**S1: Fiziksel yedek NEREDE saklanmalı?** Cevap:
`allowed_root/.windows-ai-files-backup/<transaction.id>/<dosya adı>` —
`allowed_root`'un kendisi altında, gizli (nokta ile başlayan) bir
klasör. Gerekçe: (a) whitelist dışına ASLA çıkmaz (biz kendimiz
`allowed_root`'a göre inşa ediyoruz, kullanıcı/LLM girdisi değil), (b)
`transaction.id` ile ayrıştırma aynı isimli dosyaların farklı
transaction'larda çakışmasını önler, (c) derinlik 3 (klasör+txn_id+
dosya) `MAX_PATH_DEPTH=3`'ü AŞMIYOR (Saga #272). (saga-oto tarafından
otomatik seçildi, dar kapsam — yeni bir external backup storage/config
gerektirmiyor)

**S2: `FileOperation.destination_path`/`backup_path` alanları DELETE
için ne anlama gelmeli?** Cevap: MOVE/COPY ile AYNI SÖZLEŞME korunuyor
— `destination_path` = "forward işlem sonrası dosyanın FİZİKSEL OLARAK
bulunduğu yer" (DELETE için bu, yedek konumu), `backup_path` =
"rollback'in geri yükleyeceği konum" (DELETE için bu, ORİJİNAL kaynak
konumu). Bu, mevcut rollback döngüsünün (`destination_path.exists()`
kontrolü + `backup_path`'e geri yükleme) DEĞİŞTİRİLMEDEN DELETE'i de
kapsamasını sağlıyor — Saga #288'in dispatch mimarisi bu sayede
GERÇEKTEN yeniden kullanılabilir çıkıyor (red-team'in öngördüğü
"imza değişikliği gerekebilir" endişesi bu tasarımla ortadan kalkıyor).
(saga-oto tarafından otomatik seçildi)

**S3: DELETE rollback'i, MOVE rollback'iyle AYNI fonksiyon mu (ikisi de
"hedefi backup_path'e taşı")?** Cevap: Evet — `_rollback_move` zaten
tam olarak bunu yapıyor (`shutil.move(destination_path, backup_path)`),
DELETE için ayrı bir fonksiyon YAZMAYA gerek yok, `_ROLLBACK_OPERATIONS[
OperationType.DELETE] = _rollback_move` olarak eşlenebilir. (saga-oto
tarafından otomatik seçildi, kod tekrarını önler)

## Kabul Kriterleri
1. **AC-1 (kritik):** DELETE step'i işlendiğinde kaynak dosya ÖNCE
   `.windows-ai-files-backup/<txn_id>/` altına kopyalanır, SONRA
   orijinal konumundan silinir.
2. **AC-2 (kritik):** Bir DELETE adımından SONRAKİ bir adım başarısız
   olursa, rollback yedek dosyayı ORİJİNAL konumuna geri getirir —
   silinen dosya "geri gelir".
3. **AC-3 (yüksek):** `FileOperation.operation_type` DELETE için
   `"Sil"` olarak kaydedilir.
4. **AC-4 (yüksek):** Whitelist/derinlik koruması yedek konumu için de
   geçerli — `.windows-ai-files-backup/<id>/dosya` derinliği
   `MAX_PATH_DEPTH`'i aşmıyor (matematiksel olarak garanti, ama bir
   testle de doğrulanmalı).

## Riskler / Varsayımlar / Bilinmeyenler
- **Bilinen sınırlama (kapsam dışı):** `PlanStep.targetFolder` DELETE
  için anlamsız (YYYY-MM formatına kilitli ama DELETE'in hedef klasörü
  yok) — LLM'in DELETE step'i için hâlâ geçerli bir `targetFolder`
  üretmesi gerekecek (örn. mevcut ayın adı, kullanılmayacak ama şema
  gereği zorunlu). Bu, plan_generation.py prompt güncellemesi task'ında
  (Saga #292, bu task'a depends_on) netleştirilmeli — kapsam dışı
  bırakıldı.
- **Varsayım:** `.windows-ai-files-backup` klasörü kullanıcının
  `discover_pdf_files` taramasını etkilemez (sadece `.pdf` dosyalarını
  arıyor, klasörleri değil) — doğrulanmalı.

## Test Stratejisi
`backend/tests/test_orchestrator.py`: DELETE başarı (kaynak silinir,
yedek oluşur), DELETE sonrası rollback (dosya orijinal konuma geri
gelir), yedek klasör derinlik doğrulaması.
