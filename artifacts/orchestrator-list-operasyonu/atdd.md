---
task_slug: orchestrator-list-operasyonu
priority: low
coverage_target: "70/0/30"
performance_target: "yok"
test_strategy: "unit (pytest, tmp_path + in-memory sqlite)"
affected_modules:
  - backend/orchestrator.py
saga_task_id: 291
epic_id: 26
---

# ATDD — LIST Operasyonu (Saga #291)

## Goal
`OperationType.LIST`'in `apply_plan` tarafından reddedilmeden kabul
edilmesini sağlamak — ama gerçek ürün anlamı netleştirilerek: LIST hiçbir
dosya sistemi mutasyonu yapmaz, tamamen salt okunur/inert bir adımdır.

## Sorular ve Cevaplar (saga-oto tarafından otomatik seçildi)

**S1: "Bu klasördeki dosyaları listele" dediğinde ne olmalı — sohbette
gösterim mi, DB'ye kaydedilen bir envanter mi?** Cevap: NE İKİSİ DE, bu
task'ın kapsamında. Gerekçe: "listeleme" zaten `/api/plan` çağrısının
KENDİSİNDE meydana geliyor — backend `discover_pdf_files` ile klasörü
tarıyor, LLM bir `PlanSkeleton` üretiyor, `PlanCard` bunu zaten sohbette
gösteriyor (Saga #262/#277). `OperationType.LIST` sadece LLM'in "hiçbir
şey taşıma/silme/kopyalama/adlandırma, sadece göster" niyetini ifade
etmesi için var — `apply_plan`'ın (onaydan SONRA çalışan, dosya
sistemini MUTASYONA UĞRATAN katman) bunun için yapması gereken TEK şey:
hiçbir şey yapmamak. Ayrı bir "envanter" DB kaydı ya da özel bir sohbet
gösterimi icat etmek gereksiz bir soyutlama olurdu (YAGNI) — gösterim
zaten plan üretimi anında oluyor. (saga-oto tarafından otomatik seçildi,
dar kapsam)

**S2: LIST için `FileOperation` kaydı oluşturulmalı mı (denetim
amaçlı)?** Cevap: HAYIR. Gerekçe: `FileOperation` "bir dosyaya ne
olduğunun" denetim kaydı (Saga #275) — LIST'te dosyaya HİÇBİR ŞEY
olmuyor, kaydedilecek bir "işlem" yok. Boş bir kayıt oluşturmak
`recover_incomplete_transactions`/rollback mantığını gereksiz yere
karmaşıklaştırır (LIST kaydının "hiçbir zaman pending/rollback'e
düşemeyeceği" özel bir durum olması gerekirdi). (saga-oto tarafından
otomatik seçildi)

## Kabul Kriterleri
1. **AC-1 (kritik):** `apply_plan`, `OperationType.LIST` içeren bir
   planı reddetmez (`_SUPPORTED_OPERATION_TYPES`'a eklendi).
2. **AC-2 (kritik):** LIST step'i için HİÇBİR dosya sistemi çağrısı
   (`shutil`/`os`/`Path.mkdir` vb.) yapılmaz, HİÇBİR `FileOperation`
   kaydı oluşturulmaz.
3. **AC-3 (yüksek):** LIST-only bir plan `apply_plan`'dan `"committed"`
   durumunda, boş `operations` listesiyle döner (transaction yine de
   oluşturulur — denetim için "bu plan onaylandı ve işlendi" izi kalır).
4. **AC-4 (yüksek):** LIST, MOVE/COPY/DELETE/RENAME ile AYNI planda karışık
   olarak bulunabilir — LIST step'leri atlanır, diğerleri normal
   işlenir.

## Riskler / Varsayımlar / Bilinmeyenler
- **Bilinen sınırlama (DELETE/RENAME ile tutarlı):** `targetFolder`
  LIST için de kullanılmıyor ama şema gereği hâlâ geçerli bir YYYY-MM
  değeri gerektiriyor.
- `_distribute_files_to_steps`'in LIST step'lerinin `fileNames`'ini de
  normal şekilde işlemesi gerekiyor (dosyalar hâlâ "bu step'e ait"
  olarak işaretlenmeli, aksi halde "hiçbir step'e atanmamış dosya"
  hatası yanlışlıkla tetiklenir) — ama bu dosyalarla apply_plan'ın ana
  döngüsünde HİÇBİR ŞEY yapılmaz.

## Test Stratejisi
`backend/tests/test_orchestrator.py`: LIST-only plan → hiçbir dosyaya
dokunulmaz + boş operations listesi + committed; karışık LIST+MOVE planı
→ sadece MOVE'un dosyaları taşınır.
