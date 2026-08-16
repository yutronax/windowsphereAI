---
task_slug: klasor-yolu-tek-satir-erisim
jira_id: null
saga_task_id: 252
priority: high
coverage_target: 80
performance_target: null
memory_target: null
test_strategy:
  unit: 15
  integration: 15
  e2e: 70
affected_modules:
  - ui/src/components/onboarding/OnboardingScreen.tsx
  - ui/src/components/onboarding/OnboardingScreen.test.tsx
  - ui/e2e/onboarding.spec.ts
---

# ATDD — klasor-yolu-tek-satir-erisim

## Jira Kaynağı
Jira'ya bağlı değil — yerel görev (Saga task #252, epic #23).

## Persona
Türkiye pazarında muhasebeci/avukat gibi teknik olmayan masaüstü kullanıcısı
(kullanıcı mesajından — DESIGN_DECISIONS.md §1).

## Hedef (Neden)
Task #250'de seçilen klasör yolu JS ile sabit 80 karaktere kesiliyordu,
sadece mouse `title` tooltip'iyle tam yol görülebiliyordu — klavye
kullanıcısı için tam yol hiç erişilebilir değildi. Bu task, kesmeyi CSS
tabanlı (konteyner genişliğine duyarlı) hale getirip hem fare hem klavye
kullanıcısı için tutarlı bir erişim mekanizması kuruyor.

## User Story
As a teknik olmayan masaüstü kullanıcısı
I want seçtiğim klasör yolunu (uzun olsa bile) tek satırda net görebilmek ve gerektiğinde tam halini (fare veya klavye ile) görebilmek
So that hangi klasöre izin verdiğimi onaylamadan önce yanlış anlamayayım

## Acceptance Criteria (Given-When-Then, önceliklendirilmiş)
1. [Critical] Given seçilen klasör yolu konteyner genişliğinden uzun, When `selected-folder-path` render edilir, Then CSS (`white-space:nowrap; overflow:hidden; text-overflow:ellipsis`) ile tek satırda üç noktayla kısaltılır (JS tabanlı `truncateWindowsPath` kaldırılır).
2. [Critical] Given yol elementi, When Tab ile klavye odağı gelir, Then odaklanan elementte tam (kesilmemiş) yol içeren bir tooltip/balon görünür.
3. [High] Given yol elementi, When fare ile üzerine gelinir (hover), Then aynı tooltip mekanizmasıyla tam yol görünür (tutarlı, native `title` yerine).
4. [Medium] Given seçilen klasör yolu konteyner genişliğine sığıyor (kısa), When render edilir, Then hiçbir kesme/ellipsis uygulanmaz, yol olduğu gibi görünür.

## Davranış Sözleşmesi (hangi durumda ne döner)
Bu task salt görsel/erişilebilirlik değişikliği — "dönen değer" yerine
render/etkileşim durumu tablosu kullanıldı:

| # | Durum | Görsel/DOM Beklentisi | Yan etki | Kullanıcı ne görür | AC |
|---|---|---|---|---|---|
| 1 | Happy path — uzun yol, hiçbir etkileşim yok | `white-space:nowrap`, `text-overflow:ellipsis`, tek satır | Yok | "...\Deliller" gibi kısaltılmış tek satır | AC-1 |
| 2 | Klavye odağı (Tab) | `tabIndex=0` elementte tooltip görünür, tam yol metni DOM'da | Yok | Tam yolu gösteren balon | AC-2 |
| 3 | Fare hover | Aynı tooltip mekanizması tetiklenir | Yok | Tam yolu gösteren balon | AC-3 |
| 4 | Kısa yol (kesme gerekmiyor) | Ellipsis uygulanmaz, tam metin zaten görünür | Yok | Tam yol, kesilmeden | AC-4 |

**Silinen satırlar ve neden:** "Girdi geçersiz/eksik", "kaynak yok",
"yetkisiz erişim", "dış bağımlılık hatası", "zaman aşımı", "kısmi başarı",
"hiçbir şey yapılamadı ama hata yok" — bu element yalnızca
`{selectedFolder && ...}` guard'ı zaten true olduğunda render ediliyor
(task #250'den), burada hiçbir veri/ağ/dosya sistemi etkileşimi yok, salt
CSS/DOM görüntüleme.

Kısmi başarı: Uygulanmaz.
Hiçbir şey yapılamadı ama hata da yok: Uygulanmaz.
Boş sonuç ↔ hata ayrımı: Uygulanmaz.

## Test Strategy
Unit: 15% — (varsa) tooltip açık/kapalı state mantığı için component-test.
Integration: 15% — `getComputedStyle` ile CSS truncation özelliklerinin
(white-space/overflow/text-overflow) doğru uygulandığının component test
seviyesinde doğrulanması.
E2E: 70% — Playwright ile gerçek tarayıcıda Tab-focus ve hover
senaryolarının her ikisinde tam yolun görünür olduğunun doğrulanması, kısa
yol senaryosunda ellipsis olmadığının doğrulanması.

## Benchmark / Başarı Ölçütü
Coverage Target: 80%
Performance Target: Yok
Memory: Yok
Görsel/UI kriteri: Ekran görüntüsü kullanıcıya (Yusuf) gösterilip görsel
onay alınacak.
Diğer ölçülebilir kriterler: Yok.

## Kapsam Dışı
- Tooltip'in gelişmiş pozisyonlama mantığı (viewport taşmasını önleme) ve
  animasyon — basit görünür/gizli geçişi yeterli.
- "Devam" düğmesi veya diğer form elemanlarının stili (ayrı task'lar).

## Etkilenen Dosyalar/Modüller (bilinen)
- `ui/src/components/onboarding/OnboardingScreen.tsx` — `truncateWindowsPath`
  fonksiyonu ve onu çağıran satır kaldırılacak, CSS class + tooltip mantığı
  eklenecek.
- `ui/src/components/onboarding/OnboardingScreen.test.tsx` — task #250'nin
  `describe('truncateWindowsPath', ...)` bloğu kaldırılacak (fonksiyon
  kaldırıldığı için), yeni testler eklenecek. **Diğer 8 test dokunulmayacak.**
- `ui/e2e/onboarding.spec.ts` — mevcut testler (özellikle "shows the chosen
  native-dialog folder..." testi, `selected-folder-path` metnini kontrol
  ediyor) CSS-tabanlı kesmeyle uyumlu kalmalı, gerekirse güncellenecek.

## Rollback Beklentisi
Uygulanmaz (N/A) — salt CSS/erişilebilirlik değişikliği, kalıcı yan etki yok.

## Risks
- `truncateWindowsPath`'in kaldırılması, task #250'nin mevcut testlerinden
  birini (kendi describe bloğu) kırıyor — bilinçli bir "temizlik" (ölü kod
  bırakmama), kullanıcı onayı alındı. Diğer 8 test bu değişiklikten
  etkilenmemeli, `code-copilot`/`efektor` bunu doğrulamalı.
- Mevcut e2e testindeki `toHaveText('C:\\Users\\Yusuf\\Documents\\Müvekkiller')`
  assertion'ı (task #250'den) tam metin kontrolü yapıyor — CSS truncation
  DOM metnini değiştirmez (sadece görsel kesme), bu yüzden bu assertion
  muhtemelen bozulmayacak, ama doğrulanmalı.

## Assumptions
- Tooltip basit bir CSS `:focus`/`:hover` ile görünürlüğü değişen bir
  `<span>`/`<div>` olacak, ek bir kütüphane (örn. Radix Tooltip) eklenmeyecek
  (proje henüz hiçbir UI kütüphanesi seçmedi — CAVEMAN minimalizm).

## Unknowns
(Yok — tüm kategoriler netleşti.)

## Sorular ve Cevaplar (ham kayıt)
1. Persona/hedef → DESIGN_DECISIONS.md'den (kullanıcı mesajından, tekrar
   sorulmadı).
2. Kesme yöntemi CSS'e mi taşınsın? → Evet, CSS tabanlı, JS kesme kaldırılır.
3. Klavye ile tam yol nasıl gösterilsin? → Focus'ta açılan tooltip/balon.
4. Test stratejisi oranı? → 15/15/70.
5. Kabul kriteri sahibi kim? → Otomatik test + kullanıcının (Yusuf) görsel
   onayı.
6. truncateWindowsPath'in kendi testi ne olacak? → Fonksiyon ve testi
   birlikte kaldırılır (ölü kod bırakılmaz).
7. Rollback geçerli mi? → Hayır, N/A.
8. Kapsam dışı bir şey var mı? → Evet, tooltip pozisyonlama/animasyon detayı
   yok.
