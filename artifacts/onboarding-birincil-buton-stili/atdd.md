---
task_slug: onboarding-birincil-buton-stili
jira_id: null
saga_task_id: 251
priority: high
coverage_target: 80
performance_target: null
memory_target: null
test_strategy:
  unit: 10
  integration: 10
  e2e: 80
affected_modules:
  - ui/src/components/onboarding/OnboardingScreen.tsx
---

# ATDD — onboarding-birincil-buton-stili

## Jira Kaynağı
Jira'ya bağlı değil — yerel görev (Saga task #251, epic #23).

## Persona
Türkiye pazarında muhasebeci/avukat gibi teknik olmayan masaüstü kullanıcısı
(kullanıcı mesajından — DESIGN_DECISIONS.md §1).

## Hedef (Neden)
"Klasör Seç" düğmesi onboarding ekranının tek birincil eylemi — görsel
hiyerarşi net olmalı ki kullanıcı ilk açılışta ne yapması gerektiğini
tereddütsüz anlasın.

## User Story
As a teknik olmayan masaüstü kullanıcısı
I want "Klasör Seç" düğmesinin belirgin, tıklanabilir bir birincil eylem gibi görünmesini
So that ilk açılışta ne yapmam gerektiğini anlamak için tahmin yürütmeyeyim

## Acceptance Criteria (Given-When-Then, önceliklendirilmiş)
1. [Critical] Given backend hazır (etkin durum), When düğme render edilir, Then yükseklik ≥44px, `border-radius: 8px`, arka plan `#2563EB`, metin rengi beyaz olur.
2. [Critical] Given düğme klavye ile odaklanır, When Tab ile gelinir, Then 2px görünür bir odak halkası (outline) görünür.
3. [High] Given backend hazır değil (disabled), When düğme render edilir, Then arka plan `#94A3B8`, `cursor: not-allowed`, tıklama hiçbir eylem tetiklemez.
4. [High] Given düğme etkin, When fare üzerine gelir (hover) veya tıklanır (active), Then sırasıyla `#1D4ED8` / `#1E40AF` arka plan rengine geçer.
5. [Medium] Given `#2563EB` arka plan + beyaz metin, When kontrast oranı hesaplanır, Then WCAG AA (≥4.5:1) karşılanır.

## Davranış Sözleşmesi (hangi durumda ne döner)
Bu task salt görsel/CSS state'i uyguluyor — "dönen değer" kavramı yerine
"hangi state'te hangi computed style" tablosu kullanıldı:

| # | Durum | Computed Style Beklentisi | Yan etki | Kullanıcı ne görür | AC |
|---|---|---|---|---|---|
| 1 | Happy path — enabled, hiçbir etkileşim yok | `height≥44px`, `border-radius:8px`, `background:#2563EB`, `color:#fff` | Yok | Belirgin mavi birincil buton | AC-1 |
| 2 | Klavye odağı (focus-visible) | `outline: 2px solid` (görünür renk) | Yok | Odak halkası | AC-2 |
| 3 | Disabled (backend hazır değil) | `background:#94A3B8`, `cursor:not-allowed` | Tıklama hiçbir state değiştirmez | Soluk, tıklanamaz görünen buton | AC-3 |
| 4 | Hover / Active (etkinken) | `background:#1D4ED8` (hover) / `#1E40AF` (active) | Yok | Koyulaşan buton (geri bildirim) | AC-4 |
| 5 | Kontrast hesaplaması | Kontrast oranı ≥4.5:1 | Yok | (Ölçülebilir, görsel fark yok) | AC-5 |

**Silinen satırlar ve neden:** Bu task hiçbir veri okuma/yazma/ağ çağrısı
içermiyor — orijinal şablondaki "kaynak yok", "yetkisiz erişim", "dış
bağımlılık hatası", "zaman aşımı", "kısmi başarı", "hiçbir şey yapılamadı
ama hata yok" satırlarının hiçbiri bu task'a uygulanmıyor (hepsi state'siz
bir CSS uygulamasıdır, network/DB/dosya sistemi etkileşimi yok).

Kısmi başarı: Uygulanmaz — tek adımlı stil uygulaması, ara durum yok.
Hiçbir şey yapılamadı ama hata da yok: Uygulanmaz — CSS her zaman
uygulanır ya da derleme hatası verir, sessiz kısmi uygulama senaryosu yok.
Boş sonuç ↔ hata ayrımı: Uygulanmaz — bu task'ta veri sorgusu yok.

## Test Strategy
Unit: 10% — varsa (renk/kontrast hesaplama gibi) saf yardımcı fonksiyonlar.
Integration: 10% — component'in doğru prop'larla doğru class/style'ı
uyguladığının component-test seviyesinde (vitest+RTL, `getComputedStyle`)
doğrulanması.
E2E: 80% — Playwright ile gerçek tarayıcıda `getComputedStyle` üzerinden
enabled/disabled/hover/active/focus durumlarının her biri.

## Benchmark / Başarı Ölçütü
Coverage Target: 80%
Performance Target: Yok (statik CSS, ölçülebilir bir performans hedefi yok)
Memory: Yok
Görsel/UI kriteri: Ekran görüntüsü kullanıcıya (Yusuf) gösterilip görsel
onay alınacak — `vision-test` skill'iyle `verify` adımında kontrol edilir.
Diğer ölçülebilir kriterler: WCAG AA kontrast oranı ≥4.5:1 (AC-5).

## Kapsam Dışı
- "Devam" düğmesinin stili (ayrı bir karar/task — bu round'da dokunulmuyor).
- Animasyon/geçiş (`transition`) efektleri — statik renk değerleri yeterli.
- Metin kutusu, placeholder, hata mesajı stilleri (Saga task #253/#254/#255).

## Etkilenen Dosyalar/Modüller (bilinen)
- `ui/src/components/onboarding/OnboardingScreen.tsx` (mevcut "Klasör Seç"
  butonuna inline style veya yeni bir küçük CSS dosyası eklenecek).
- `ui/src/components/onboarding/OnboardingScreen.test.tsx` — mevcut testler
  bozulmamalı, yeni style-doğrulama testleri eklenecek.
- `ui/e2e/onboarding.spec.ts` — mevcut testler bozulmamalı, yeni computed-style
  assertion'ları eklenecek.

## Rollback Beklentisi
Uygulanmaz (N/A) — salt CSS/görsel değişiklik, kalıcı yan etki yok.

## Risks
- Proje henüz bir CSS framework/dosya konvansiyonu seçmedi
  (DESIGN_DECISIONS.md'de belirtilmemiş) — bu task'ın seçeceği yöntem
  (inline style ya da basit .css) sonraki stil task'ları için emsal
  oluşturacak.

## Assumptions
- Proje henüz bir styling kütüphanesi/CSS framework'ü seçmediği için bu
  task inline style veya basit bir `.css` dosyasıyla yazılır, yeni bir
  styling kütüphanesi eklenmez. (kullanıcı onayı alındı)

## Unknowns
(Yok — tüm kategoriler netleşti.)

## Sorular ve Cevaplar (ham kayıt)
1. Persona/hedef → DESIGN_DECISIONS.md'den (kullanıcı mesajından, tekrar
   sorulmadı).
2. "Devam" düğmesine de dokunulsun mu? → Hayır, sadece Klasör Seç.
3. Disabled görünümü? → Soluk gri (#94A3B8) + cursor: not-allowed.
4. Hover/active state olsun mu? → Evet, basit koyulaşma (#1D4ED8/#1E40AF).
5. Test stratejisi oranı? → 10/10/80 (e2e ağırlıklı).
6. Kontrast hedefi olsun mu? → Evet, WCAG AA (4.5:1).
7. Kabul kriteri sahibi kim? → Otomatik test (computed style) + kullanıcının
   (Yusuf) görsel onayı.
8. Bilinen risk/varsayım? → Standart varsayım: inline style/CSS-in-JS
   kullanılır, yeni framework eklenmez.
9. Rollback geçerli mi? → Hayır, N/A.
10. Kapsam dışı bir şey var mı? → Evet, animasyon/geçiş efekti yok.
