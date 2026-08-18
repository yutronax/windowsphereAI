---
task_slug: pdf-birlestirme-merge-operasyonu
priority: medium
coverage_target: "80/0/20"
performance_target: "yok"
test_strategy: "unit (pytest, gerçek pypdf ile gerçek geçici PDF dosyaları)"
affected_modules:
  - backend/models.py
  - backend/security.py
  - backend/orchestrator.py
  - backend/plan_generation.py
saga_task_id: 304
epic_id: 29
---

# ATDD — PDF Birleştirme (MERGE) Operasyonu (Saga #304)

## Goal
Birden fazla PDF'i tek bir yeni PDF'te birleştiren bir operasyon
eklemek. Task'ın kendi sorduğu asıl mimari soru: mevcut Orchestrator
dispatch desenine mi (Saga #288-291) entegre edilecek, yoksa ayrı bir
"format agent" katmanı mı olacak?

## Sorular ve Cevaplar (saga-oto tarafından otomatik seçildi)

**S1: Mimari — mevcut dispatch'e mi, ayrı katmana mı?** Cevap: **Mevcut
`OperationType` dispatch desenine entegre edilir, AMA `apply_plan`'ın
ana döngüsünde LIST'e benzer bir ÖZEL DURUM olarak** (tamamen yeni bir
"format agent" modülü İCAT EDİLMEZ). Gerekçe: mevcut per-dosya forward/
rollback dispatch sözleşmesi (`_FORWARD_OPERATIONS[op](source_path,
destination_path)`) KESİNLİKLE "1 kaynak → 1 hedef" varsayıyor — MERGE
ise "N kaynak → 1 hedef" (N PDF okunur, TEK yeni bir PDF yazılır,
kaynaklara DOKUNULMAZ). Bu, generic per-dosya döngüsüne ZORLA
sığdırılamaz; LIST zaten `apply_plan`'ın ana döngüsünde bir özel durum
olarak ele alınıyor (Saga #291) — MERGE de AYNI desene uyar, ama LIST'in
aksine GERÇEKTEN bir dosya sistemi işlemi yapar (adım başına TEK bir
`FileOperation` kaydı, N tane değil). Ayrı bir "format agent" katmanı/
modülü kurmak bu task'ın kapsamını aşan bir mimari genişleme olurdu
(YAGNI — tek bir operasyon için yeni bir soyutlama katmanı gerekmiyor).
(saga-oto tarafından otomatik seçildi — dar kapsam, mevcut LIST
emsaline tutarlı)

**S2: Kaynaklara ne olur — taşınır/silinir mi, yoksa dokunulmaz mı?**
Cevap: **Dokunulmaz** — MERGE, kaynak PDF'leri OLDUĞU GİBİ bırakıp
SADECE yeni bir birleşik dosya oluşturur (COPY'nin "kaynak
etkilenmez" semantiğiyle AYNI). Kullanıcının "birleştir" isteğinin en
az sürpriz yaratan yorumu budur — orijinal dosyaların kaybolması/
taşınması ayrı, açıkça istenmiş bir DELETE/MOVE gerektirir, MERGE'in
kendisi bunu YAPMAMALI. Rollback de bu yüzden COPY'nin rollback'iyle
(`_rollback_copy`: sadece hedefteki yeni dosyayı sil, kaynaklara
dokunma) AYNI fonksiyonu paylaşır — kod tekrarı yok. (saga-oto
tarafından otomatik seçildi — en az sürpriz ilkesi, mevcut COPY
semantiğiyle tutarlı)

**S3: Birleşik dosyanın hedef konumu/adı nasıl belirlenir?** Cevap: Yeni
bir `PlanStep.mergedFileName: str | None` alanı (RENAME'in
`newFileNames`iyle AYNI desende — path separator yasak, sadece MERGE
için zorunlu). Hedef konum `allowed_root/mergedFileName` (KÖK seviyede,
YYYY-MM alt klasörü YOK) — MERGE'in ürettiği dosyanın doğal bir
"oluşturulma tarihi klasörü" kavramı yok (DELETE/RENAME'in `targetFolder`
kullanmama emsaliyle AYNI, Saga #289/#290). `targetFolder` şema gereği
yine zorunlu ama fiilen kullanılmaz. (saga-oto tarafından otomatik
seçildi — DELETE/RENAME emsaline tutarlı)

**S4: `mergedFileName` çakışma/doğrulama kuralları neler olmalı?**
Cevap: RENAME'in `validate_rename_destinations`iyle (Saga #290)
BİREBİR aynı ilkeler — (a) `mergedFileName`, planın bilmediği zaten var
olan bir dosyayla çakışamaz (whitelist reddeder), (b) plan genelinde
birden fazla MERGE/RENAME step'i AYNI `mergedFileName`/hedefi
üretemez (zincirleme çakışma), (c) tüm karşılaştırmalar
`_normalize_filename` (Windows case-insensitive) üzerinden. Ayrıca
`allowed_root/mergedFileName`in kendisi de whitelist/derinlik/sistem-
koruması kontrolünden (`_validate_single_path`) geçmeli — diğer tüm
hedef path'lerle AYNI. En az 2 dosya birleştirilmeden (`fileNames`
uzunluğu < 2) MERGE anlamsız — şema seviyesinde reddedilir. (saga-oto
tarafından otomatik seçildi — mevcut Saga #290 güvenlik disiplinine
tutarlı genişleme)

**S5: `PLAN_SYSTEM_PROMPT`a MERGE eklenmeli mi?** Cevap: EVET — Saga
#292'nin doğal-dil→operationType eşleme rehberine `"birleştir",
"tek dosya yap"` → `"Birleştir"` eklenir, `mergedFileName` şema
açıklaması `newFileNames`inkiyle AYNI desende eklenir. Bu olmadan LLM
gerçek bir "bu PDF'leri birleştir" isteğini asla doğru operationType'a
çeviremez (epic 26'daki AYNI boşluk sınıfı, Saga #292'nin çözdüğü). (saga-oto
tarafından otomatik seçildi — Saga #292 emsaliyle tutarlı, ATDD keşfinde
bulunan gerçek boşluk)

**S6: Hangi PDF kütüphanesi API'si?** Cevap: `pypdf.PdfWriter.append(reader)`
+ `.write(path)` — Saga #303'te seçilen `pypdf`, `PdfReader`/`PdfWriter`
üzerinden basit bir "birden fazla reader'ı sırayla append et, tek
dosyaya yaz" akışı sunuyor, ek bir soyutlama gerekmiyor. (saga-oto
tarafından otomatik seçildi)

## Kabul Kriterleri
1. **AC-1 (kritik):** `apply_plan`, `operationType: "Birleştir"` içeren
   bir step'i işleyip N kaynak PDF'i GERÇEKTEN okuyup TEK bir yeni PDF
   dosyası (`allowed_root/mergedFileName`) üretiyor, kaynaklara
   dokunmuyor.
2. **AC-2 (kritik):** MERGE step'i başarısız olursa (ör. plan'ın geri
   kalanı hata verirse) rollback SADECE yeni oluşturulan birleşik
   dosyayı siliyor, kaynaklara dokunmuyor (COPY rollback semantiği).
3. **AC-3 (yüksek):** `validate_plan_paths`, `mergedFileName`i hem
   whitelist/derinlik/sistem-koruması hem de RENAME'inkiyle aynı
   çakışma/zincir kurallarıyla doğruluyor.
4. **AC-4 (yüksek):** `PlanStep` şeması `mergedFileName`i SADECE MERGE
   için zorunlu kılıyor, `fileNames` uzunluğu MERGE için < 2 ise
   reddediliyor.
5. **AC-5 (orta):** `PLAN_SYSTEM_PROMPT`, "birleştir" isteğini doğru
   `operationType: "Birleştir"`e eşleyecek rehberi + `mergedFileName`
   şema açıklamasını içeriyor.
6. **AC-6 (orta):** Mevcut tüm testler (MOVE/COPY/DELETE/RENAME/LIST)
   hiçbir değişiklik olmadan geçmeye devam ediyor.

## Riskler / Varsayımlar / Bilinmeyenler
- Şifreli/bozuk bir PDF `pypdf.PdfReader`i açarken hata fırlatırsa,
  bu MERGE'in kendi forward-adım hatası olarak ele alınır (mevcut
  `apply_plan`in genel `except Exception` rollback mekanizması zaten
  bunu yakalar, MERGE'e özel ek bir hata yönetimi GEREKMEZ).
- Gerçek bir LLM'in "birleştir" isteğinden doğru `mergedFileName`
  üretip üretmediği bu oturumda uçtan uca DOĞRULANAMADI (stub LLM
  istemcisiyle test edildi) — canlı bir DeepSeek testiyle ayrıca
  doğrulanabilir (Saga #292'deki gibi, kullanıcı isterse).

## Test Stratejisi
`backend/tests/test_orchestrator.py`: gerçek geçici PDF dosyalarıyla
(pypdf ile oluşturulmuş, gerçek sayfa sayılarıyla) MERGE'in gerçekten
doğru sayfa sayısına sahip birleşik bir dosya ürettiği + kaynakların
dokunulmadan kaldığı + rollback'in sadece birleşik dosyayı sildiği
doğrulanır. `backend/tests/test_models.py`: şema validasyonu.
`backend/tests/test_security.py`: whitelist/çakışma kontrolleri.
`backend/tests/test_plan_generation.py`: prompt rehberi.
