---
task_slug: otomatik-kaydirma-alt-durumu
priority: high
coverage_target: "AC'lerin tamamı unit test ile kapsanır"
performance_target: "yok (UI katmanı)"
test_strategy: "70/0/30 (unit/integration/e2e) — mevcut vitest+RTL altyapısı, scrollHeight/clientHeight jsdom'da manuel override edilerek test edilir"
affected_modules: ["ui/src/components/chat/ChatScreen.tsx"]
---

# Yeni mesajlarda kullanıcı alttaysa sohbeti otomatik kaydır (Saga #266)

## Persona
Sohbet geçmişini yukarı kaydırarak eski bir mesaja bakan veya en altta yeni
mesajları takip eden kullanıcı.

## Goal
Kullanıcı en alttaysa yeni plan/durum/sonuç mesajları görünür kalacak şekilde
yumuşakça kaydırılmalı. Kullanıcı en alttan uzaklaşmışsa otomatik kaydırma
yapılmamalı, bunun yerine "En yeni mesaja dön" düğmesi gösterilmelidir.

## User Story
Bir kullanıcı olarak, en alttaysam yeni mesajları otomatik görmek, ama eski
bir mesaja bakarken listenin ayağımın altından kaymasını istemiyorum — o
durumda yeni mesaj geldiğini bir düğmeyle fark edip istediğimde en alta
dönebilmeliyim.

## Acceptance Criteria (öncelik sırasına göre)
1. Kullanıcı listenin en altındayken yeni bir mesaj eklendiğinde liste en alta
   kaydırılır (auto-scroll).
2. Kullanıcı listeyi yukarı kaydırıp en alttan uzaklaştığında (`scrollTop +
   clientHeight < scrollHeight - eşik`) bu durum algılanır.
3. Kullanıcı en altta değilken yeni mesaj gelirse OTOMATİK KAYDIRMA YAPILMAZ;
   bunun yerine "En yeni mesaja dön" düğmesi görünür olur.
4. "En yeni mesaja dön" düğmesine tıklanınca liste en alta kaydırılır ve
   düğme kaybolur (kullanıcı tekrar "en altta" sayılır).
5. Kullanıcı zaten en alttaysa düğme hiç görünmez.

## Behaviour-contract tablosu
| Durum | Beklenen davranış |
|---|---|
| Kullanıcı en altta, yeni mesaj gelir | Liste en alta kaydırılır, düğme yok |
| Kullanıcı yukarı kaydırmış, yeni mesaj gelir | Kaydırma YAPILMAZ, "En yeni mesaja dön" düğmesi görünür |
| "En yeni mesaja dön" tıklanır | Liste en alta kaydırılır, düğme kaybolur |
| Kullanıcı manuel olarak tekrar en alta kaydırır | Düğme kaybolur (yeniden "en altta" sayılır) |

## Risks/Assumptions/Unknowns
- Assumption: "En altta" eşiği (threshold) 24px olarak seçildi — piksel-
  mükemmel bir eşleşme yerine küçük bir tolerans, tarayıcı rounding
  farklarına karşı dayanıklılık sağlar. (saga-oto tarafından otomatik seçildi)
- Assumption: jsdom test ortamında gerçek layout/scrollHeight hesaplanmadığı
  için testler `Object.defineProperty` ile `scrollHeight`/`clientHeight`/
  `scrollTop` değerlerini manuel override ediyor — bu, projenin zaten
  vitest+jsdom kullandığı için kabul edilen bir test-altyapısı deseni.
  (saga-oto tarafından otomatik seçildi)
- Assumption: "Yumuşak kaydırma" `scrollTo({ behavior: 'smooth' })` ile
  talep edilir; jsdom bunu gerçekten animasyonlu yapmaz ama tarayıcıda
  çalışır — davranışsal sözleşme testte `scrollTop` değerinin değiştiğini
  doğrulamakla sınırlı. (saga-oto tarafından otomatik seçildi)

## Test Strategy
70/0/30 unit/integration/e2e. `ChatScreen.test.tsx`'e yeni testler.

## Benchmark
Kabul kriteri: `npx vitest run` içinde tüm testler yeşil.

## Sorular ve Cevaplar (saga-oto otomatik)
- S: Eşik değeri (threshold) ne olmalı? C: 24px — küçük, pratik bir tolerans,
  literatürde yaygın kullanılan bir değer. (saga-oto tarafından otomatik
  seçildi)
- S: Düğme metni ne olmalı? C: "En yeni mesaja dön" — task açıklamasında
  zaten belirtilen ifade birebir kullanıldı. (saga-oto tarafından otomatik
  seçildi)
