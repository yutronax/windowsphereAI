# Plan — koyu-acik-tema-destegi
_Reference: atdd.md_

## Files to Modify
| File | Why | Risk |
|------|-----|------|
| ui/src/tokens.ts | `colors` grubundaki her hex değer `var(--color-x)` CSS custom property referansına çevrilecek (AC-1..AC-6) | medium — `tokens.test.ts`'in mevcut hardcoded-hex assertion'larını KIRAR (aşağıda çözüldü) |
| ui/src/tokens.test.ts | Yeni kontrata (CSS var referansları) göre GÜNCELLENECEK — bu, tokens.ts'in KENDİ testi, "7 bileşenin testleri değişmez" kuralının istisnası (tokens.ts'in davranışı kasıtlı olarak değişiyor) | medium — test-copilot bu dosyayı güncelleyecek, code-copilot DEĞİL |
| ui/src/main.tsx | `theme.css` import edilecek | low |
| ui/src/App.tsx | Mount sırasında `applyStoredTheme()` çağrısı (useEffect) + toggle butonu render edilecek (her iki ekranın da üstünde, tek yerde) | low — mevcut `App.test.tsx` testleri (OnboardingScreen mock, ChatScreen akışı) etkilenmemeli, toggle sadece bir kardeş eleman olarak eklenecek |

## New Files
| File | Purpose |
|------|---------|
| ui/src/theme.css | `:root` (koyu/mevcut varsayılan) ve `[data-theme="light"]` (açık) için tam CSS custom property seti — `tokens.ts`'teki her renk anahtarına karşılık gelir |
| ui/src/lib/theme.ts | `applyStoredTheme()` (mount'ta localStorage'dan oku + data-theme uygula, hata durumunda sessizce varsayılana düş), `toggleTheme()` (data-theme set/kaldır + localStorage yaz), `getTheme()` (mevcut temayı oku) — saf fonksiyonlar, React'a bağımlı değil |

## Dependencies / Gerçek Kod Keşfi
- **KRİTİK BULGU:** `ui/src/tokens.test.ts` şu an `expect(tokens.colors.primary).toBe('#1E3A8A')` gibi 9+ HARDCODED HEX assertion'ı içeriyor (AC-1 testleri, Saga #345). Bu dosya `tokens.ts`'in renkleri `var(--color-x)` string'ine çevrildiğinde KESİN KIRILIR — atdd.md'nin Risks bölümünde işaretlenen bu risk gerçek. **Karar:** bu, atdd.md'nin AC-5'inin ("mevcut testler değişmeden yeşil kalır") kapsamı DIŞINDA — AC-5 açıkça "7 bileşenin" testlerinden bahsediyor, `tokens.test.ts` tokens.ts'in KENDİ testi ve tokens.ts'in sözleşmesi bu görevde BİLİNÇLİ olarak değişiyor. `tokens.test.ts` test-copilot tarafından yeni kontrata göre güncellenecek (`toBe('var(--color-primary)')` gibi).
- **7 bileşenin testleri (Button.test.tsx, Card.test.tsx, ChatScreen.test.tsx, PlanCard.test.tsx, ResultCard.test.tsx, SearchPanel.test.tsx, TransactionHistoryPanel.test.tsx) muhtemelen KIRILMAYACAK:** bu testler `toHaveStyle({ backgroundColor: tokens.colors.primary })` şeklinde `tokens.colors.X`'i DİNAMİK olarak referans alıyor (hardcoded hex DEĞİL) — hem bileşenin gerçek render'ı hem test assertion'ı AYNI `tokens.colors.primary` değerini (artık `'var(--color-primary)'` string'i) okuyacağı için, jsdom'un CSS var'ı gerçekten çözümleyip çözümlememesinden BAĞIMSIZ olarak iki taraf da aynı ham string'i taşıyacak ve test geçecektir. **Bu varsayım `verify` adımında gerçek `npx vitest run` ile KANITLANACAK, teorik kalmayacak.**
- `App.tsx` (Read edildi) — `config === undefined` iken `null` dönüyor, sonra `config || sessionId` durumuna göre `ChatScreen` veya `OnboardingScreen` render ediyor. Toggle butonu bu iki dalın ORTAK üstünde (return bloğunda bir `<>` fragment içinde, `config === undefined` erken çıkışından SONRA) eklenecek — böylece hem OnboardingScreen hem ChatScreen ekranında görünür, mevcut `App.test.tsx`'in `findByTestId('main-chat-screen')`/`findByText('mock-onboarding-continue')` sorguları etkilenmez (toggle sadece bir kardeş eleman).
- `main.tsx` (Read edildi) — hiç CSS import etmiyor, `theme.css`'i buraya eklemek en doğru yer (uygulama başlangıcında bir kez yüklenir).
- **OnboardingScreen.tsx KAPSAM DIŞI** (atdd.md'de zaten belirtildi) — toggle butonu görünür olacak ama OnboardingScreen'in kendi hardcoded renkleri tema değişikliğinden ETKİLENMEYECEK (bilinen/kabul edilen sınırlama, atdd.md Kapsam Dışı'nda zaten var).

## Migration Required?
Hayır — DB/schema değişikliği yok, saf frontend CSS-değişkeni + localStorage.

## Risks
- (atdd.md'den taşındı, ÇÖZÜLDÜ) `tokens.test.ts` kırılacak → kasıtlı, test-copilot güncelleyecek, AC-5 kapsamı dışında olduğu netleştirildi.
- (atdd.md'den taşındı, KISMEN ÇÖZÜLDÜ — teorik) 7 bileşenin testleri muhtemelen etkilenmeyecek (dinamik `tokens.colors.X` referansı sayesinde) ama bu `verify` adımında GERÇEK test çalıştırmasıyla kanıtlanmalı, varsayım olarak bırakılmayacak.
- `theme.css`'teki açık tema renk paletinin gerçek değerleri atdd.md'de/plan.md'de belirtilmedi (sadece "açık tema" deniyor) — code-copilot'a dispatch edilirken makul bir açık palet (beyaz/açık gri arkaplan, koyu metin, aynı primary/danger tonları) TANIMLANMALI; bu bir tasarım kararı, code-copilot'un kendi taktığı rastgele bir renk seçimi olmamalı.

## Open Questions
Açık temanın gerçek renk paleti (spesifik hex değerleri) atdd.md'de tanımlanmadı — bu, code-copilot'un mimariyi bilmeden karar vermesini önlemek için burada netleştirilmeli.

## Kararlar
**Açık tema renk paleti** (Haiku alt-ajanına sorulmadan, CAVEMAN ilkesiyle doğrudan karar verildi — bu bir tasarım/estetik tercihi değil, standart bir açık/koyu tema ters-çevirme deseni): `panelBackground`/arkaplan tonları açığa, `textDark`/metin tonları koyuya çevrilir, `primary`/`danger`/`border` gibi marka/durum renkleri her iki temada da SABİT kalır (kontrastı bozmadan marka kimliğini korur — yaygın tema deseni). Kesin değerler code-copilot dispatch prompt'unda verilecek:
- `--color-panel-background`: koyu `#F3F4F6` → açık `#FFFFFF`
- `--color-border`: koyu `#E5E7EB` → açık `#D1D5DB` (açık zeminde biraz daha belirgin olması için)
- `--color-text-dark`: koyu `#111827` → açık `#111827` (zaten koyu metin, açık temada da koyu kalır — okunabilirlik)
- `--color-text-secondary`: koyu `#4B5563` → açık `#4B5563` (yeterli kontrast korunur, değişmez)
- `--color-white`: koyu `#fff` → açık `#1F2937` (kart/buton üzerindeki "beyaz" metin/arkaplan açık temada koyu bir yüzeye dönüşmeli — Button primary/danger metninin okunabilir kalması için)
- Diğer tüm renkler (primary, primaryHover, primaryActive, danger, textMuted, dangerBanner*, dangerMessage*, success*, connected) her iki temada SABİT kalır.

## Not
`ui/src/tokens.ts`, `ui/src/App.tsx`, `ui/src/theme.css` — App.tsx bir `.tsx` (rendered UI) dosyası, `verify` adımında gate 12 (`vision-test`) değerlendirilecek (önceki tasklardaki gibi muhtemelen backend-bağımlılığı nedeniyle N/A gerekçeli olacak).
