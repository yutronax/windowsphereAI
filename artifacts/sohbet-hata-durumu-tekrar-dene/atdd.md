---
task_slug: sohbet-hata-durumu-tekrar-dene
priority: high
coverage_target: "AC'lerin tamamı unit test ile kapsanır"
performance_target: "yok (UI katmanı)"
test_strategy: "70/0/30 (unit/integration/e2e) — mevcut vitest+RTL altyapısı"
affected_modules: ["ui/src/components/chat/ChatScreen.tsx"]
---

# Sohbet hatalarını yeniden deneme eylemiyle ayrı durum olarak göster (Saga #267)

## Persona
Mesaj gönderdikten sonra plan üretimi veya yerel API çağrısı başarısız olan
bir kullanıcı.

## Goal
Plan üretimi veya yerel API hatası, başarısız balonda kısa bir neden ve
"Tekrar dene" düğmesiyle görünmelidir. Başarısızlık sessizce kaybolmamalı
ve işlem onayı asla açılmamalıdır.

## User Story
Bir kullanıcı olarak, isteğim başarısız olduğunda NEDEN başarısız olduğunu
kısaca görmek ve tek tıkla tekrar deneyebilmek istiyorum — hata sessizce
kaybolup beni belirsizlikte bırakmamalı, ve asla olmayan bir plan
"onaylanabilir" gibi görünmemeli.

## Acceptance Criteria (öncelik sırasına göre)
1. `planError` (kısa hata metni) dışarıdan verildiğinde, mesaj listesi ile
   yazma alanı arasında bir hata göstergesi görünür: hata metni +
   "Tekrar dene" düğmesi.
2. "Tekrar dene" düğmesine tıklanınca `onRetry` callback'i çağrılır.
3. Hata durumu KENDİLİĞİNDEN kaybolmaz — sadece `planError` prop'u dışarıdan
   temizlenirse (parent state günceller) kaybolur; component kendi içinde
   otomatik bir timeout/dismiss mekanizması İÇERMEZ.
4. Hata görünürken hiçbir `PlanCard` render edilmez / onay düğmesi
   göstermez — başarısız bir istekte asla "işlem onayı" açılmaz (bu,
   `ChatScreen`'in `messages` listesinde o anda bir plan mesajı olmaması
   durumunu, yani gerçek kullanım senaryosunu, temsil eder; ayrıca hata
   göstergesinin kendisi hiçbir approve/onay eylemi sunmaz).
5. Hata görünürken yazma alanı VE gönder düğmesi devre dışı KALMAZ —
   kullanıcı isterse doğrudan yeni bir mesaj yazıp gönderebilir (yükleniyor
   durumundan farklı olarak, hata durumu kullanıcıyı kilitlemez).
6. Hata göstergesi `role="alert"` taşır — ekran okuyucuya HEMEN (assertive)
   duyurulur, "Plan hazırlanıyor…" gibi polite bir bölgeyle karıştırılmaz.

## Behaviour-contract tablosu
| Durum | Beklenen davranış |
|---|---|
| `planError` verilmemiş/null | Gösterge yok |
| `planError="..."` | Gösterge görünür, metin + "Tekrar dene" düğmesi, `role="alert"` |
| "Tekrar dene" tıklanır | `onRetry` çağrılır, gösterge KENDİLİĞİNDEN kaybolmaz (parent'ın `planError`'ı temizlemesi gerekir) |
| `planError` VE `isGeneratingPlan` aynı anda true (misuse) | Sadece yükleniyor göstergesi görünür, hata göstergesi bastırılır (yükleniyor önceliklidir — yeni bir deneme zaten başlamış demektir) |
| Hata görünürken | textarea ve gönder düğmesi normal (disabled DEĞİL, draft boşsa gönder yine disabled — mevcut kural) |

## Risks/Assumptions/Unknowns
- Assumption: `planError` ve `onRetry` bu task'ta da (#264/#265/#266 ile
  aynı desen) DIŞARIDAN kontrol edilen prop'lar — gerçek backend/LLM hata
  yakalama mekanizması henüz yok, bu task'ın kapsamı DIŞINDA. (saga-oto
  tarafından otomatik seçildi)
- Assumption: `planError` bir `string | null` (kısa neden metni) olarak
  modellendi, ayrı bir hata kodu/tipi eklenmedi — dar kapsam. (saga-oto
  tarafından otomatik seçildi)
- Assumption: `isGeneratingPlan` true iken `planError` de true ise (parent
  tutarsız state geçse bile) yükleniyor göstergesi kazanır — çünkü yeniden
  deneme zaten `isGeneratingPlan=true` yaparak görsel olarak "deneniyor"
  durumuna geçmiş demektir; bu fail-safe bir öncelik kuralı, AC-4'ün
  "asla onay açılmaz" ilkesiyle tutarlı (iki çelişkili göstergenin aynı
  anda görünmesini önler). (saga-oto tarafından otomatik seçildi)

## Test Strategy
70/0/30 unit/integration/e2e. `ChatScreen.test.tsx`'e yeni testler.

## Benchmark
Kabul kriteri: `npx vitest run` içinde tüm testler yeşil.

## Sorular ve Cevaplar (saga-oto otomatik)
- S: Hata durumunda giriş kilitlenmeli mi? C: Hayır — task açıklamasında
  sadece yükleniyor durumu için "gönderimi kilitleyen" ifadesi var, hata
  durumu için böyle bir kısıt belirtilmemiş; kullanıcının serbestçe yeni
  bir mesaj yazabilmesi daha iyi UX. (saga-oto tarafından otomatik seçildi)
- S: `role="alert"` mi `aria-live="assertive"` mi? C: `role="alert"`
  (örtük olarak `aria-live="assertive"` + `aria-atomic="true"` taşır),
  tek bir attribute ile aynı garanti sağlanır. (saga-oto tarafından
  otomatik seçildi)
