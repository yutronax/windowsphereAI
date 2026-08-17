---
task_slug: kullanici-mesaj-balonu-stili
priority: low
coverage_target: "AC'lerin tamamı unit test ile kapsanır"
performance_target: "yok (UI katmanı)"
test_strategy: "70/0/30 (unit/integration/e2e) — mevcut vitest+RTL altyapısı; görsel/computed-style doğrulaması sınıf/attribute varlığı üzerinden yapılır (mevcut proje deseni, bkz. PlanCard.test.tsx 44px buton testi)"
affected_modules: ["ui/src/components/chat/ChatScreen.tsx"]
---

# Kullanıcı mesaj balonlarını sağa hizalı mavi yüzeyle biçimlendir (Saga #260)

## Persona
Sohbet ekranında kendi mesajlarını okuyan/tarayan kullanıcı.

## Goal
Kullanıcı mesaj balonları en fazla okunabilir satır genişliğinde, 16px iç
boşlukta ve 14px köşe yarıçapında olmalı. Koyu mavi yüzey üzerindeki beyaz
metin erişilebilir kontrast sağlamalı.

## User Story
Bir kullanıcı olarak, kendi mesajlarımı asistan mesajlarından görsel olarak
kolayca ayırt edebilmek istiyorum — sağa hizalı, belirgin bir mavi balon
içinde, okunabilir bir genişlikte.

## Acceptance Criteria (öncelik sırasına göre)
1. Kullanıcı mesajları (`data-role="user"`) sağa hizalı kalır (mevcut
   `margin-left: auto` davranışı korunur).
2. Mesaj metni artık ayrı bir "balon" elemanı (`chat-message-bubble`)
   içinde render edilir; 16px iç boşluk (`padding: 16px`) ve 14px köşe
   yarıçapı (`border-radius: 14px`) taşır.
3. Kullanıcı balonu koyu mavi arka plan (`#1E3A8A`) + beyaz metin (`#fff`)
   kullanır — WCAG AA kontrast oranı (≥4.5:1) sağlanır (bu renk çifti
   ~8.6:1 kontrast verir).
4. Balon en fazla okunabilir bir satır genişliğinde kalır (`max-width:
   65ch`) — çok uzun tek satırlık mesajlarda bile okunabilirlik korunur.
5. Asistan mesajları (`data-role="assistant"`) bu task'ta GÖRSEL OLARAK
   DEĞİŞMEZ — sadece aynı `chat-message-bubble` yapısal sınıfını paylaşır
   (arka plan/metin rengi Saga #261'e bırakılıyor, dar kapsam).
6. `PlanCard`, balonun İÇİNDE DEĞİL, balondan sonra (mevcut konumunda)
   render edilmeye devam eder — plan kartının kendi stil sözleşmesi
   (Saga #262/#263/#264/#265) bozulmaz.

## Behaviour-contract tablosu
| Durum | Beklenen davranış |
|---|---|
| Kullanıcı mesajı | `.chat-message-bubble` + `data-role="user"` özel arka plan/metin rengi |
| Asistan mesajı | `.chat-message-bubble` var, ama rol-özel renk override'ı YOK (bu task kapsamında) |
| Mesajın planı varsa | `PlanCard` balonun dışında, `li` içinde balondan sonra render edilir |

## Risks/Assumptions/Unknowns
- Assumption: Renk değeri `#1E3A8A` (koyu mavi, Tailwind blue-900'e yakın)
  bu task'ta İLK KEZ seçildi — tasarım sistemi/marka rengi henüz
  tanımlanmadığı için makul, yüksek kontrastlı bir varsayılan seçildi.
  (saga-oto tarafından otomatik seçildi)
- Assumption: `max-width: 65ch` "en fazla okunabilir satır genişliği"
  ifadesinin somutlaştırılması — tipografide yaygın kabul edilen bir
  okunabilirlik sınırı (45-75 karakter/satır). (saga-oto tarafından
  otomatik seçildi)
- Assumption: Kontrast oranı testte GERÇEK bir renk-kontrast hesaplayıcı
  ile doğrulanmadı (jsdom'da layout/renk render edilmiyor) — CSS'te
  yazılı renk değerleri okunarak (kaynak metin araması) doğrulandı; bu,
  projenin zaten kullandığı test deseniyle (PlanCard 44px buton testi
  className kontrolü) tutarlı. (saga-oto tarafından otomatik seçildi)

## Test Strategy
70/0/30 unit/integration/e2e. `ChatScreen.test.tsx`'e yeni testler
(className/data-role varlığı + stil bloğunda renk değerlerinin var olduğu
kontrolü).

## Benchmark
Kabul kriteri: `npx vitest run` içinde tüm testler yeşil.

## Sorular ve Cevaplar (saga-oto otomatik)
- S: Balon rengi ne olmalı? C: `#1E3A8A` (koyu mavi) — WCAG AA'yı rahatça
  geçen, tasarım sistemi henüz yokken makul bir varsayılan. (saga-oto
  tarafından otomatik seçildi)
- S: Asistan balonları da bu task'ta mı stillendirilsin? C: Hayır, ayrı
  bir Saga task'ı (#261) zaten var — dar kapsam, tekrar iş yapmamak için
  sadece yapısal `chat-message-bubble` sınıfı paylaşılıyor. (saga-oto
  tarafından otomatik seçildi)
