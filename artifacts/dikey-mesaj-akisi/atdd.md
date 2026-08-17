---
task_slug: dikey-mesaj-akisi
priority: high
coverage_target: "AC'lerin tamamı unit test ile kapsanır"
performance_target: "yok (UI katmanı, ölçülebilir performans hedefi yok)"
test_strategy: "70/0/30 (unit/integration/e2e) — proje zaten vitest+RTL unit ve Playwright e2e altyapısına sahip"
affected_modules: ["ui/src/components/chat/ChatScreen.tsx", "ui/src/App.tsx"]
---

# Sohbet alanını kullanıcı ve asistan mesajları için dikey akış olarak oluştur (Saga #259)

## Persona
Masaüstü uygulamasını kullanan, klasör onboarding'ini tamamlamış bir kullanıcı.

## Goal
Mesaj listesi ana alanı doldurmalı, yazma alanı sabit alt bölgede kalmalı; mesajlar
sıralı, seçilebilir ve ekran okuyucuya anlamlı biçimde sunulmalı.

## User Story
Bir kullanıcı olarak, sohbet geçmişimi yukarıdan aşağıya sırayla görmek ve her zaman
aynı yerde duran bir yazma alanına mesaj yazabilmek istiyorum, böylece asistanla
doğal bir sohbet akışı sürdürebilirim.

## Acceptance Criteria (öncelik sırasına göre)
1. Mesaj listesi ana alanı (flex: 1 1 auto, overflow-y: auto) doldurur, yazma alanı
   sabit alt bölgede (flex: 0 0 auto) kalır.
2. Mesajlar gönderilme sırasına göre yukarıdan aşağıya dizilir (sequential).
3. Mesaj metni `user-select: text` ile seçilebilir durumda kalır.
4. Mesaj listesi konteyneri `role="log"` + `aria-live="polite"` taşır — yeni mesajlar
   ekran okuyucuya otomatik duyurulur.
5. Enter (Shift olmadan) mesajı gönderir; Shift+Enter satır başı ekler; boş/whitespace
   metin gönderilmez.
6. `App.tsx`'teki mevcut `data-testid="main-chat-screen"` sözleşmesi korunur (App.test.tsx
   buna bağlı).

## Behaviour-contract tablosu
| Durum | Beklenen davranış |
|---|---|
| `initialMessages` boş | Liste boş render edilir, hata yok |
| Kullanıcı boş/whitespace metinle Gönder'e basar | Hiçbir mesaj eklenmez, buton zaten disabled |
| Enter (shiftKey yok) | Mesaj gönderilir, draft temizlenir |
| Shift+Enter | Mesaj gönderilMEZ, satır başı eklenir (preventDefault çağrılmaz) |
| Mesaj gönderilir | `onSendMessage` callback'i gönderilen mesajla çağrılır |

## Risks/Assumptions/Unknowns
- Assumption: Asistan mesajlarının nasıl üretileceği (LLM/backend entegrasyonu) bu
  task'ın kapsamı DIŞINDA — sadece yerel state ile kullanıcı mesajı ekleniyor. Gerçek
  backend entegrasyonu sonraki task'larda (262-267) ele alınacak. (saga-oto tarafından
  otomatik seçildi — dar kapsam ilkesi)
- Risk: `nextMessageId` modül seviyesinde global sayaç — çoklu ChatScreen instance'ı
  aynı sayaçı paylaşır. Tek sayfalı uygulamada (tek instance) sorun değil.

## Test Strategy
70/0/30 unit/integration/e2e. Yeni: `ChatScreen.test.tsx` (7 unit test, RTL).
Var olan `App.test.tsx` regresyonu için de çalıştırıldı (testid sözleşmesi korundu).

## Benchmark
Kabul kriteri: `npx vitest run` içinde tüm testler (49/49) yeşil.

## Sorular ve Cevaplar (saga-oto otomatik)
- S: Asistan mesajı üretimi bu task'a dahil mi? C: Hayır, dar kapsam — sadece UI
  iskeleti ve kullanıcı mesajı ekleme. (saga-oto tarafından otomatik seçildi)
- S: Mesaj listesi için `role="log"` mu `aria-live="polite"` bölge mi? C: İkisi
  birlikte (role="log" zaten polite varsayılan taşır ama açık belirtmek netlik
  sağlar, düşük maliyetli erişilebilirlik iyileştirmesi). (saga-oto tarafından
  otomatik seçildi)
