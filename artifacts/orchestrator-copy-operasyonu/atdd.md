---
task_slug: orchestrator-copy-operasyonu
priority: high
coverage_target: "70/0/30"
performance_target: "yok"
test_strategy: "unit (pytest, tmp_path + in-memory sqlite)"
affected_modules:
  - backend/orchestrator.py
saga_task_id: 288
epic_id: 26
---

# ATDD — COPY Operasyonu (Saga #288)

## Goal
`apply_plan`'a `OperationType.COPY` desteği eklemek: kaynak dosya
kopyalanır, SİLİNMEZ. Mevcut MOVE-only kısıt kaldırılıp COPY için
ayrı bir fiziksel işlem + rollback semantiği kurulmalı.

## Sorular ve Cevaplar (saga-oto tarafından otomatik seçildi)

**S1: `backup_path` COPY için ne anlama gelmeli?** Cevap: MOVE'da
`backup_path` = orijinal kaynak konumu (taşındıktan sonra oraya geri
dönülür). COPY'de kaynak hiç taşınmıyor/silinmiyor — `backup_path`'in
"rollback'te oraya dön" anlamı YOK. Bunun yerine `backup_path` alanını
COPY için de `source_path` ile aynı değere ayarlamak (tutarlılık için,
mevcut alan boş bırakılmasın) ama rollback mantığının COPY'de "kaynağa
geri taşı" DEĞİL "hedeftekini sil" yapması gerekiyor — bu, rollback
kod yolunun artık `operation_type`'a göre dallanması gerektiği anlamına
geliyor. (saga-oto tarafından otomatik seçildi, DESIGN kararı — mevcut
"tek tip rollback" mimarisini değiştiriyor)

**S2: Kaynak dosya kopyalama sonrası whitelist/derinlik kontrolü
tekrar mı yapılmalı?** Cevap: Hayır, `validate_plan_paths` zaten
`apply_plan`'ın başında TÜM `pdf_files`+`plan.steps` için çalışıyor
(hem kaynak hem hedef path'leri kapsıyor) — COPY için ekstra bir
çağrıya gerek yok, mevcut mekanizma zaten hem source hem destination'ı
kapsıyor. (saga-oto tarafından otomatik seçildi)

## Kabul Kriterleri
1. **AC-1 (kritik):** COPY step'i işlendiğinde kaynak dosya hedefe
   `shutil.copy2` ile kopyalanır, kaynak dosya YERİNDE KALIR (silinmez).
2. **AC-2 (kritik):** Bir COPY adımından SONRAKİ bir adım başarısız
   olursa, rollback COPY'nin oluşturduğu HEDEF kopyayı siler — kaynağa
   dokunmaz (kaynak zaten hiç değişmedi).
3. **AC-3 (yüksek):** `FileOperation.operation_type` COPY için
   `"Kopyala"` olarak kaydedilir; `record_file_operation`/DB şeması
   değişmez (mevcut alanlar yeterli).
4. **AC-4 (yüksek):** Whitelist/derinlik/sistem-klasörü koruması COPY
   hedefi için de MOVE ile aynı şekilde uygulanır (zaten `validate_plan_paths`
   üzerinden otomatik).

## Riskler / Varsayımlar / Bilinmeyenler
- Rollback kod yolunun operation_type'a göre dallanması, gelecekte
  DELETE (Saga #289) eklendiğinde ÜÇÜNCÜ bir dal daha gerektirecek —
  bu task'ta rollback fonksiyonunu operation_type-aware bir yapıya
  (ör. bir dispatch dict/if-elif) kurmak, DELETE task'ının işini
  kolaylaştıracak şekilde tasarlanmalı.

## Test Stratejisi
`backend/tests/test_orchestrator.py`: COPY başarı senaryosu (kaynak+hedef
ikisi de var), COPY sonrası başka bir adım başarısız → rollback (hedef
kopya silinir, kaynak dokunulmamış kalır).
