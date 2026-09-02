# Code Diff — koyu-acik-tema-destegi
_Green step — 15 dosya/282 test yeşil (bağımsız doğrulandı)._

## Oluşturulan Dosyalar
| Dosya | Amaç |
|---|---|
| `ui/src/theme.css` | `:root` (koyu, mevcut varsayılan) + `[data-theme="light"]` (açık) CSS custom property setleri |
| `ui/src/lib/theme.ts` | `applyStoredTheme()`, `toggleTheme()`, `getTheme()` — localStorage tabanlı tema kalıcılığı |

## Değiştirilen Dosyalar
| Dosya | Değişiklik |
|---|---|
| `ui/src/tokens.ts` | `colors` grubu hex → `var(--color-x)` referansları (radius/size/fontSize/spacing değişmedi) |
| `ui/src/main.tsx` | `import './theme.css';` eklendi |
| `ui/src/App.tsx` | `applyStoredTheme()` mount useEffect'i + tema toggle butonu (her iki ekranın ortak üstünde) |
| `ui/src/tokens.test.ts` | Yeni CSS-var kontratına göre güncellendi (test-copilot) |
| `ui/src/lib/theme.test.ts` | Yeni (test-copilot) — sonradan spy hedefi düzeltildi (aşağıya bakınız) |
| `ui/src/App.test.tsx` | Toggle butonu render testleri eklendi (test-copilot) |
| `ui/src/setupTests.ts` | **Plan.md'de öngörülmemiş, implementasyon sırasında gerekliliği ortaya çıkan** localStorage + CSS-var çözümleme shim'i (aşağıda detaylı) |

## AC Karşılanma Durumu
| AC | Durum | Kanıt |
|---|---|---|
| AC-1..AC-4 (tema davranışı) | ✅ | `theme.test.ts` (14 test, spy hedefi düzeltildikten sonra GERÇEKTEN hata yolunu da test ediyor) |
| AC-5 (7 bileşenin testleri değişmeden yeşil) | ✅ | Bileşen dosyaları hiç değişmedi; testleri de değişmedi — ama bunun için `setupTests.ts`'e bir CSS-var çözümleme shim'i eklenmesi GEREKTİ (aşağıya bakınız) |
| AC-6 (theme.css tam set) | ✅ | Her iki blok da tüm renk anahtarlarını kapsıyor |
| AC-7 (toggle erişilebilir) | ✅ | `data-testid="theme-toggle-button"`, `aria-label="Temayı değiştir"` |

## ÖNEMLİ: `setupTests.ts` üzerine şeffaf not (plan.md'de öngörülmemişti)

İlk implementasyon turu, plan.md'nin dosya listesinde OLMAYAN `ui/src/setupTests.ts`'i (global test konfigürasyonu, TÜM 282 testi etkiler) kendiliğinden değiştirdi. Bu, code-copilot review adımında yakalandı ve üç ayrı düzeltme turuyla ele alındı:

1. **Gerçek gereklilik doğrulandı (kabul edildi):** `setupTests.ts`'teki değişiklik olmadan proje genelinde **20 test gerçekten kırılıyor** (bağımsız `git checkout HEAD -- setupTests.ts` + `vitest run` ile kanıtlandı) — sebep: `border: 1px solid var(--x)` gibi CSS shorthand'ler içindeki `var()` referanslarını jsdom `borderColor` gibi longhand'lere çözemiyor; bazı önceki task'lardan kalma testler (`ChatScreen.test.tsx`, `TransactionHistoryPanel.test.tsx`, `Button.test.tsx`) hem shorthand hem hardcoded-çözümlenmiş-değer bekliyor. Bu, AC-5'in "hiçbir bileşen dosyası/testi değişmez" sözünü tutabilmenin TEK yolu — plan.md'nin teorik varsayımı (dinamik `tokens.colors.X` referansı yeterli olur) kısmen yanlış çıktı, gerçek çözümleme shim'i gerekliydi.
2. **Kalite sorunu bulundu ve düzeltildi:** İlk halinde `cssVariableMap` adlı elle yazılmış bir renk haritası `theme.css`'in `:root` değerlerini tekrarlıyordu (ikinci kaynak, drift riski) — artık açık bir senkronizasyon uyarı yorumu + `tokens.ts` ile anahtar-sayısı tutarlılık kontrolü (console.warn) eklendi.
3. **Gerçek bug bulundu ve düzeltildi:** `Object.defineProperty(global, 'localStorage', ...)` satırı `global` yerine `globalThis` kullanmalıydı — `npx tsc --noEmit` bunu TS2304 hatası olarak yakaladı, düzeltildi.
4. **Gizli test-gap bulundu ve düzeltildi:** Bu ortamda jsdom'un `window.localStorage`'ı gerçek bir `Storage` sınıfı örneği DEĞİL (`instanceof Storage` → `false`, `.clear()` yok — bağımsız olarak doğrulandı). `theme.test.ts`'in ilk hali `vi.spyOn(Storage.prototype, 'getItem')` kullanıyordu — bu, hem localStorage mock'undan ÖNCE hem SONRA hiçbir etki yaratmıyordu, "localStorage hata fırlatırsa" testleri YANLIŞ SEBEPTEN geçiyordu (try/catch hiç tetiklenmiyordu). test-copilot'a geri dönülüp spy hedefi `Storage.prototype`'tan doğrudan `localStorage` objesine çevrildi — artık testler gerçek hata yolunu doğruluyor.

## Test/Derleme Sonucu (bağımsız doğrulandı, birden fazla turda)
- `npx tsc --noEmit` → 0 hata
- `npx vitest run` (tüm proje) → **15 dosya / 282 test, hepsi yeşil**

## CAVEMAN Değerlendirmesi
- `setupTests.ts` değişikliği plan.md'de yoktu ama gerekliliği somut kanıtla (test kırılması) doğrulandı — spekülatif değil, zorunlu.
- Yeni dosya sayısı minimal (2: theme.css, lib/theme.ts).
- 7 bileşenin kaynak kodu HİÇ değişmedi (atdd.md'nin ana vaadi korundu).

## Red-Team Sonrası Düzeltmeler (approve-with-changes)
Bağımsız `obss-red-team` incelemesi 5 bulgu buldu (3 medium, 2 low), commit'i bloklamadı. 3 tanesi düzeltildi:
- **Medium (maintainability):** `setupTests.ts`'teki `cssVariableMap`/`tokens.ts` senkron kontrolü sadece anahtar SAYISINI karşılaştırıyordu → DEĞER-bazlı karşılaştırmaya çevrildi, eksik anahtar durumunda artık `Error` fırlatılıyor (fail-fast), sessiz `console.warn` değil.
- **Low (reliability):** Await edilmeyen async `import().then()` → static `import { tokens } from './tokens'` + senkron kontrol.
- **Medium (readability):** Tema toggle butonu stilsiz/konumsuzdu (gerçek tarayıcıda layout riski) → `position: fixed; top: 12px; right: 12px; zIndex: 10` eklendi.

Düzeltilmeyen 2 bulgu (kabul edilen risk, düşük öncelik):
- **Medium (architecture):** Global `CSSStyleDeclaration.prototype.getPropertyValue` monkeypatch'inin kapsamının sadece etkilenen test dosyalarına daraltılması — daha invaziv bir refactor gerektiriyor (per-dosya custom matcher), bu low-priority epic için orantısız; mevcut fail-fast senkron kontrolü riski büyük ölçüde azaltıyor.
- **Low (test-gap):** Açık temada kontrast doğrulaması — atdd.md zaten WCAG audit'ini kapsam dışı bırakmış.

Düzeltme sonrası bağımsız doğrulama: `npx tsc --noEmit` → 0 hata, `npx vitest run` → 15 dosya/282 test, hepsi yeşil.

## Sıradaki adım
`commit` — kullanıcı onayıyla.
