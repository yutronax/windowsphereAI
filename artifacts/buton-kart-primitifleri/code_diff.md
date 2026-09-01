# Code Diff — buton-kart-primitifleri (green step)
_Reference: atdd.md, plan.md, test_diff.md_

## Oluşturulan Dosyalar
- `ui/src/components/primitives/Button.tsx`
- `ui/src/components/primitives/Card.tsx`
- `ui/src/components/primitives/index.ts`

Hiçbir mevcut dosya değiştirilmedi (AC-5 gereği — plan.md "Files to Modify"
listesi zaten boştu).

## AC Karşılanma Durumu
| AC | Durum | Kanıt |
|---|---|---|
| AC-1 (Button variant/disabled + tokens) | ✓ | `Button.tsx` — `variant` (`'primary'\|'danger'`, default `'primary'`), `disabled`, tüm token değerleri (`primary`/`primaryHover`/`primaryActive`/`danger`/`buttonHeight`/`radius.default`/`fontSize.base`/`buttonPadding`) inline `style` ile uygulanıyor. **Güncelleme (red-team sonrası):** `primaryHover`/`primaryActive` başlangıçta eksikti (red_team.json finding #1, severity: high) — `onMouseEnter`/`onMouseLeave`/`onMouseDown`/`onMouseUp` + `useState` ile eklendi, `danger` variant için spekülatif "dangerHover" token'ı uydurulmadı (envanterde yok). |
| AC-2 (Card panelBackground/border/radius + children) | ✓ | `Card.tsx` — `panelBackground`, `border`, `radius.default` uygulanıyor, `children` render ediliyor |
| AC-3 (RTL render testleri) | ✓ (16/16) | `npx vitest run` → Card.test.tsx 8/8 PASS, Button.test.tsx 8/8 PASS (test-copilot'un `color: 'white'` → `color: 'rgb(255, 255, 255)'` düzeltmesinden sonra) |
| AC-4 (TS derleme hatasız) | ✓ | `npx tsc --noEmit` — sıfır hata |
| AC-5 (mevcut ekranlarda regresyon yok) | ✓ | Tam test suite: **237/238 PASS** — tek fail yeni primitif testinde (aşağıya bakın), 6 mevcut ekranın (Onboarding/ChatScreen/PlanCard/ResultCard/TransactionHistoryPanel/SearchPanel) testleri tamamı yeşil |
| AC-6 (index.ts named export) | ✓ | `export { default as Button } from './Button'; export { default as Card } from './Card';` |

## Bilinen Test Hatası (ÇÖZÜLDÜ)
`Button.test.tsx` → "renders Button with primary variant colors and
dimensions (AC-1, AC-3)" testi başlangıçta FAIL veriyordu, test-copilot'a
geri dönülüp `color: 'white'` → `color: 'rgb(255, 255, 255)'` satırı
düzeltilerek çözüldü. Tam test suite artık **238/238 PASS**. Kök neden
doğrudan izole edilerek doğrulanmıştı (bkz. aşağıdaki debug — tarihsel
kayıt için tutuluyor):

- Test `toHaveStyle({ color: 'white' })` bekliyor.
- jsdom'un `getComputedStyle` çıktısı HER ZAMAN `rgb(255, 255, 255)`
  döndürür — component'in `color` değeri `'white'`, `'#FFFFFF'` veya
  `'rgb(255, 255, 255)'` olarak yazılsa da fark etmiyor, jsdom bunu
  normalize edip rgb formunda geri veriyor.
- Bu projedeki jest-dom sürümünün `toHaveStyle` matcher'ı, beklenen
  tarafta CSS keyword'ü (`'white'`) rgb'ye normalize ETMİYOR — bu yüzden
  literal string karşılaştırması `'white' !== 'rgb(255, 255, 255)'`
  olarak başarısız oluyor.
- Doğrulama: `getComputedStyle(button)` doğrudan okunduğunda
  `backgroundColor: rgb(30, 58, 138)`, `borderRadius: 8px`,
  `color: rgb(255, 255, 255)`, `fontSize: 16px` — **tamamı doğru ve
  beklenen token değerleriyle birebir eşleşiyor.** İmplementasyon
  doğru; sorun test dosyasındaki `'white'` literal'inin bu jest-dom
  sürümüyle uyumsuzluğu.
- İmplementasyon tarafında bu testi geçirecek hiçbir `color` değeri
  yoktur (jsdom her zaman rgb'ye normalize ediyor) — bu code-copilot'un
  çözebileceği bir implementasyon hatası değil.
- **Bu satır test dosyasına ait bir düzeltme gerektiriyor** (örn.
  `color: 'white'` → `color: 'rgb(255, 255, 255)'` veya
  `color: '#FFFFFF'` olarak güncellenmeli) — `test-copilot`'un scope'una
  giriyor, code-copilot test dosyasına dokunamaz (kural gereği).

## Kalan Sınırlamalar
- Yukarıdaki 1 test-dosyası kusuru dışında sınırlama yok.

## Varsayımlar
- Yok — plan.md'deki "Kararlar" bölümündeki disabled renk kararına
  (`#94A3B8`, `tokens.ts` genişletilmeden yerel sabit) birebir uyuldu.

## CAVEMAN Self-Review
- 3 yeni dosya (`Button.tsx`, `Card.tsx`, `index.ts`) — plan.md'nin "New
  Files" listesiyle birebir eşleşiyor, fazlası yok.
- Yardımcı fonksiyon/soyutlama yok — sadece iki fonksiyonel bileşen +
  bir re-export dosyası.
- Mevcut proje deseni (inline `style` + `data-testid` prop, bkz.
  `PlanCard.tsx`) takip edildi; yeni bir CSS-in-JS kütüphanesi veya
  stil yaklaşımı eklenmedi.
- Spekülatif prop/variant yok (`Card`'a variant eklenmedi, `Button`'a
  icon/loading gibi kapsam dışı prop eklenmedi — atdd.md "Kapsam Dışı"
  bölümüyle tutarlı).

## Sıradaki Adım
`verify` — gerçek test/build/lint gate'lerini çalıştıracak. Tam test suite
238/238 PASS, önceden bilinen test hatası çözüldü.

UI dosyalarına dokunuldu (`Button.tsx`, `Card.tsx` — React bileşenleri) —
`verify` adımında gate 11 (`vision-test`) N/A değil AKTİF çalışmalı.
