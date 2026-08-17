---
task_slug: asistan-mesaj-balonu-stili
priority: low
coverage_target: "AC'lerin tamamı unit test ile kapsanır"
performance_target: "yok (UI katmanı)"
test_strategy: "70/0/30 (unit/integration/e2e) — mevcut vitest+RTL altyapısı, sınıf/attribute varlığı üzerinden doğrulama (Saga #260 ile aynı desen)"
affected_modules: ["ui/src/components/chat/ChatScreen.tsx"]
---

# Asistan mesaj balonlarını sola hizalı nötr yüzeyle biçimlendir (Saga #261)

## Persona
Asistanın plan/hata/sonuç mesajlarını okuyan kullanıcı.

## Goal
Asistan balonları `#F3F4F6` yüzey, koyu metin ve 14px köşe yarıçapı
kullanmalı. Plan, hata ve sonuç metinleri taranabilir başlıklar ve kısa
paragraflar halinde gösterilmelidir.

## User Story
Bir kullanıcı olarak, asistanın mesajlarını kendi mesajlarımdan görsel
olarak ayırt edebilmek ve okunabilir, dağınık olmayan bir yüzeyde
okuyabilmek istiyorum.

## Acceptance Criteria (öncelik sırasına göre)
1. Asistan mesajları (`data-role="assistant"`) sola hizalı kalır (zaten
   varsayılan `li` davranışı, `margin-left: auto` uygulanmaz).
2. Asistan balonu (`chat-message-bubble`, Saga #260'da eklenen yapısal
   sınıf) `#F3F4F6` arka plan + koyu metin (`#111827`) kullanır — WCAG AA
   kontrastı rahatça sağlanır.
3. Balon 14px köşe yarıçapı zaten `.chat-message-bubble` temel sınıfından
   miras alınıyor (Saga #260) — bu task'ta AYRICA belirtilmesine gerek
   yok, sadece doğrulanır.
4. Metin okunabilirliği için `line-height: 1.5` eklenir (taranabilirlik
   için minimal, düşük maliyetli bir iyileştirme).
5. "Plan, hata ve sonuç metinlerinin taranabilir başlıklar ve kısa
   paragraflar halinde gösterilmesi" — bu, mesaj metninin markdown/zengin
   metin olarak ayrıştırılıp başlık/paragraf yapısına bölünmesini
   gerektirir. Böyle bir ayrıştırıcı (markdown parser) PROJEDE HENÜZ YOK
   ve yeni bir bağımlılık eklemek dar-kapsam ilkesiyle çelişir — bu alt
   gereksinim bu task'ın kapsamı DIŞINDA bırakıldı (bkz. Risks). PlanCard
   zaten kendi yapılandırılmış (adım listesi) sunumuna sahip (Saga #262);
   hata göstergesi (Saga #267) ve yükleniyor göstergesi (Saga #265) zaten
   ayrı, kısa, taranabilir bileşenler. Düz metin asistan mesajları için
   sadece okunabilirlik (line-height) iyileştirmesi yapıldı.

## Behaviour-contract tablosu
| Durum | Beklenen davranış |
|---|---|
| Asistan mesajı | `.chat-message-bubble` arka plan `#F3F4F6`, metin `#111827` |
| Kullanıcı mesajı | Saga #260'daki mavi yüzey DEĞİŞMEDEN kalır (regresyon yok) |
| Asistan mesajı + plan | PlanCard yine balonun dışında (Saga #260 davranışı korunur) |

## Risks/Assumptions/Unknowns
- Assumption: "Taranabilir başlıklar ve kısa paragraflar" gereksinimi
  markdown/zengin metin ayrıştırma gerektirir — bu, yeni bir bağımlılık
  (ör. `react-markdown`) veya el yazımı bir parser gerektirecek büyük bir
  kapsam artışı olur. Dar-kapsam ilkesi gereği bu task'ta ERTELENDİ; PlanCard
  (yapılandırılmış adım listesi), hata göstergesi ve yükleniyor göstergesi
  zaten kendi taranabilir yapılarına sahip olduğu için gerçek risk düşük.
  Düz metin asistan mesajları (henüz backend entegrasyonu olmadığı için
  şu an sadece test verisi) için mimari bir değişiklik gerektirmeyen
  `line-height` iyileştirmesiyle sınırlı tutuldu. (saga-oto tarafından
  otomatik seçildi — dar kapsam ilkesi, büyük mimari karar yerine dar
  kapsamı seç)
- Assumption: `#111827` (koyu gri/siyah) metin rengi bu task'ta seçildi —
  `#F3F4F6` üzerinde WCAG AAA kontrastı sağlar (~15:1). (saga-oto
  tarafından otomatik seçildi)

## Test Strategy
70/0/30 unit/integration/e2e. `ChatScreen.test.tsx`'e yeni testler.

## Benchmark
Kabul kriteri: `npx vitest run` içinde tüm testler yeşil.

## Sorular ve Cevaplar (saga-oto otomatik)
- S: Markdown/zengin metin ayrıştırma bu task'a dahil mi? C: Hayır — yeni
  bir bağımlılık gerektirir, dar-kapsam ilkesiyle çelişir; PlanCard/hata/
  yükleniyor göstergeleri zaten yapılandırılmış olduğu için gerçek risk
  düşük, bir sonraki ihtiyaç net hale geldiğinde ayrı bir task olarak ele
  alınmalı. (saga-oto tarafından otomatik seçildi)
- S: Metin rengi ne olmalı? C: `#111827` — `#F3F4F6` üzerinde çok yüksek
  kontrast sağlayan, projede zaten `plan-card-status-text` gibi yerlerde
  kullanılan koyu gri tonlarına yakın bir seçim. (saga-oto tarafından
  otomatik seçildi)
