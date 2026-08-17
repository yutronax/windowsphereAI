---
task_slug: plan-tarih-kaynagi-klasor-yapisi-dogrulama
priority: high
coverage_target: "AC'lerin tamamı unit/integration test ile kapsanır"
performance_target: "yok (saf Pydantic doğrulaması)"
test_strategy: "90/10/0 (unit/integration) — mevcut pytest altyapısı"
affected_modules: ["backend/models.py", "backend/plan_generation.py"]
---

# Planı tarih kaynaklarını ve hedef klasör yapısını açıkça tanımlayacak şekilde doğrula (Saga #270)

## Persona
Plan-skeleton'ı tüketecek olan Security katmanı (Saga #271/#272) ve
dolaylı olarak, planı onaylamadan önce gören kullanıcı.

## Goal
Plan; tarih önceliğini (dosya oluşturulma tarihi veya güvenilir
metadata), artan/azalan sıralamayı ve YYYY-MM hedef klasörlerini açıkça
içermelidir. Belirsiz ya da desteklenmeyen bir plan (bu alanlar eksik/
geçersizse) güvenlik incelemesine (Saga #271/#272) hiç GEÇMEMELİDİR.

## User Story
Bir geliştirici/sistem olarak, LLM'den gelen bir plan-skeleton'ın hangi
tarih kaynağını ve sıralama yönünü kullandığını, hedef klasörlerin
gerçekten `YYYY-MM` formatında olduğunu ŞEMA SEVİYESİNDE bilmek
istiyorum — belirsiz bir plan Security katmanına asla ulaşmamalı.

## Acceptance Criteria (öncelik sırasına göre)
1. `PlanSkeleton` artık zorunlu iki alan taşır: `dateSource` (şu an
   tek desteklenen değer: `"created_at"` — dosya oluşturulma tarihi) ve
   `sortOrder` (`"ascending"` | `"descending"`). Bu alanlar eksikse veya
   bilinmeyen bir değer taşıyorsa Pydantic `ValidationError` fırlatır —
   `generate_plan_skeleton` bunu zaten `PlanGenerationError`'a çeviriyor
   (Saga #269), yani böyle bir plan Security katmanına HİÇ ulaşmaz.
2. Her `PlanStep.targetFolder`, `YYYY-MM` formatına (`^\d{4}-\d{2}$`)
   uymalıdır — başka bir format (ör. sadece "2026", "Ağustos-2026", boş
   dize) reddedilir.
3. Boş `steps` listesi (Saga #269'daki "PDF yok" davranışı) İSTİSNADIR —
   `dateSource`/`sortOrder` boş bir plan için de sağlanmalıdır (LLM'in
   tercih ettiği tarih kaynağı/sıralama boş plan durumunda bile açık
   olmalı — tutarlılık, ama fiilen kullanılmaz).
4. Mevcut Saga #269 davranışı (metadata-only prompt, LLM hata/JSON/şema
   hatalarının `PlanGenerationError`'a çevrilmesi, model env override)
   DEĞİŞMEDEN korunur — bu task sadece şemayı SIKILAŞTIRIYOR.

## Behaviour-contract tablosu
| Girdi | Beklenen sonuç |
|---|---|
| `dateSource`/`sortOrder` eksik | `ValidationError` → `PlanGenerationError` |
| `dateSource="unknown"` | `ValidationError` → `PlanGenerationError` |
| `sortOrder="random"` | `ValidationError` → `PlanGenerationError` |
| `targetFolder="2026-08"` | Geçerli |
| `targetFolder="2026"` veya `"Ağustos"` veya `""` | `ValidationError` → `PlanGenerationError` |
| Tüm alanlar geçerli | `PlanSkeleton` başarıyla oluşturulur |

## Risks/Assumptions/Unknowns
- Assumption: "Güvenilir metadata" ifadesi şu an SADECE `"created_at"`
  ile somutlaştırıldı — task açıklaması "dosya oluşturulma tarihi VEYA
  güvenilir metadata" diyor ama bu MVP'de PDF metadata okuma (ör. PDF
  içindeki "Oluşturulma Tarihi" alanı) henüz YOK (ayrı bir dosya-sistemi
  entegrasyon task'ı gerektirir, kapsam dışı) — `DateSource` enum'u
  şimdilik tek üyeli (`created_at`), ileride yeni bir kaynak eklendiğinde
  enum'a yeni bir üye eklemek yeterli olacak (kod değişikliği küçük,
  şema geriye dönük genişleyebilir). (saga-oto tarafından otomatik
  seçildi — dar kapsam ilkesi)
- Assumption: `YYYY-MM` regex'i (`^\d{4}-\d{2}$`) ay değerinin 01-12
  aralığında olup olmadığını KONTROL ETMİYOR (ör. "2026-13" formatı
  geçer) — task sadece "YYYY-MM hedef klasörleri" diyor, ay aralığı
  doğrulaması ayrı bir iş; LLM zaten gerçek tarihlerden ürettiği için
  pratikte risk düşük, ama bu bilinçli bir kapsam sınırı olarak
  kaydedildi. (saga-oto tarafından otomatik seçildi)

## Test Strategy
90/10/0 unit/integration. `backend/tests/test_plan_generation.py`'e yeni
testler eklenir; mevcut `VALID_PLAN_JSON` sabitleri `dateSource`/
`sortOrder` içerecek şekilde güncellenir (regresyon).

## Benchmark
Kabul kriteri: `python -m pytest backend/ -q` içinde tüm testler yeşil.

## Sorular ve Cevaplar (saga-oto otomatik)
- S: `dateSource` için başka değerler (ör. "modified_at", "pdf_metadata")
  bu task'ta desteklenmeli mi? C: Hayır — MVP'de sadece dosya oluşturulma
  tarihi kullanılıyor, gerçek PDF-içi metadata okuma henüz yok. Enum tek
  üyeli ama genişleyebilir şekilde tasarlandı. (saga-oto tarafından
  otomatik seçildi)
- S: Ay aralığı (01-12) doğrulanmalı mı? C: Hayır, dar kapsam — regex
  formatı yeterli, gerçek ay-aralığı doğrulaması ayrı bir iyileştirme.
  (saga-oto tarafından otomatik seçildi)
