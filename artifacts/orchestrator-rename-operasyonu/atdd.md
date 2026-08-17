---
task_slug: orchestrator-rename-operasyonu
priority: medium
coverage_target: "70/0/30"
performance_target: "yok"
test_strategy: "unit (pytest, tmp_path + in-memory sqlite)"
affected_modules:
  - backend/models.py (PlanStep)
  - backend/orchestrator.py
saga_task_id: 290
epic_id: 26
---

# ATDD — RENAME Operasyonu (Saga #290)

## Goal
RENAME için gerçek bir şema boşluğunu kapatmak (`targetFolder` YYYY-MM
formatına kilitli, yeni dosya adı taşımıyor) ve `apply_plan`'a
`OperationType.RENAME` desteği eklemek.

## Sorular ve Cevaplar (saga-oto tarafından otomatik seçildi)

**S1: Yeni dosya adı `PlanStep`e nasıl eklenmeli?** Cevap:
`newFileNames: list[str] | None = None` — `fileNames` ile PARALEL bir
liste (aynı sırada, aynı uzunlukta). `operationType == RENAME` ise
ZORUNLU ve `len(newFileNames) == len(fileNames)` olmalı; başka bir
operationType'ta `None` OLMALI (şema netliği — RENAME dışı step'lerde
bu alanın var olması anlamsız/kafa karıştırıcı olurdu). Gerekçe:
`fileNames`/`newFileNames` deseni, Saga #286'nın zaten kurduğu
"isimle eşleştirme, pozisyonel varsayım yok" ilkesiyle tutarlı — ayrı
bir dict/obje yapısı yerine mevcut paralel-liste desenini genişletiyor.
(saga-oto tarafından otomatik seçildi)

**S2: RENAME aynı klasör içinde mi kalır, yoksa farklı bir klasöre de
taşıyabilir mi?** Cevap: SADECE isim değişikliği — aynı klasörde kalır
(`allowed_root` doğrudan altında, `targetFolder` YOK SAYILIR, DELETE'teki
"bilinen sınırlama" deseniyle tutarlı). Gerekçe: "yeniden adlandırma" ve
"taşıma" farklı kullanıcı niyetleri — ikisini birleştirmek kapsamı
büyütür, MOVE zaten taşıma için var. (saga-oto tarafından otomatik
seçildi, dar kapsam)

**S3: İki dosya aynı yeni isme yeniden adlandırılırsa ne olur?**
Cevap: Şema seviyesinde reddedilmeli (`newFileNames` içinde tekrar eden
değer → `ValidationError`) — aksi halde ikinci rename birinciyi
sessizce üzerine yazar (whitelist bunu yakalamaz, dosya sistemi
seviyesinde sessiz veri kaybı olurdu). (saga-oto tarafından otomatik
seçildi — güvenlik/veri bütünlüğü gerekçesiyle)

## Kabul Kriterleri
1. **AC-1 (kritik):** `PlanStep.newFileNames` eklendi;
   `operationType==RENAME` ise zorunlu+uzunluk eşleşmesi, aksi halde
   `None` olmalı (`model_validator`).
2. **AC-2 (kritik):** `newFileNames` içindeki değerler tekil olmalı
   (aynı step içinde), boş/whitespace olamaz, path separator içeremez
   (Saga #272 defense-in-depth deseniyle tutarlı).
3. **AC-3 (kritik):** RENAME step'i işlendiğinde dosya AYNI klasörde
   yeni isimle yer alır, eski isim artık yok.
4. **AC-4 (yüksek):** RENAME sonrası başka bir adım başarısız olursa,
   rollback dosyayı ESKİ ismine geri döndürür (MOVE'un rollback'iyle
   aynı — `_rollback_move` paylaşılabilir).
5. **AC-5 (yüksek):** Whitelist/derinlik koruması yeni dosya adı için de
   uygulanır (yeni isim de `allowed_root` altında olmalı — path
   separator içermediği için yapısal olarak zaten öyle).

## Riskler / Varsayımlar / Bilinmeyenler
- **Bilinen sınırlama (kapsam dışı, DELETE ile tutarlı):**
  `targetFolder` RENAME için de kullanılmıyor ama şema gereği hâlâ
  geçerli bir YYYY-MM değeri gerektiriyor — Saga #292'ye bırakıldı.
- `validate_plan_paths` yeni dosya adının kendisini AYRICA
  doğrulamıyor (sadece `fileNames`/`targetFolder`) — RENAME'in yeni
  hedefi (`allowed_root/newFileName`) whitelist'e karşı AYRICA
  doğrulanmalı mı, yoksa `newFileNames`'in path-separator-free olması
  (şema seviyesi) yeterli mi? Karar: yeterli — `allowed_root/name`
  (ayraçsız tek segment) yapısal olarak her zaman `allowed_root`
  altındadır, MOVE/COPY'nin `targetFolder` kontrolüne denk bir ekstra
  kontrol gerekmiyor.

## Test Stratejisi
`backend/tests/test_orchestrator.py`: RENAME başarı, RENAME-sonrası-
rollback; `backend/tests/test_models.py`(veya mevcut model testleri):
newFileNames zorunluluk/uzunluk/tekillik/path-separator validasyonları.
