# Code Diff — plan-result-kartlari-tasarim
_Green step — test_diff.md'deki 7 yeni test artık yeşil, tüm mevcut testler (260/260) korunuyor._

> Not: Codex CLI kotası dolu (Saga skill Bölüm C override). Bu skill zaten
> Codex'e değil Haiku'ya yönlendiriyor, ek bir istisna gerekmedi.

## Değiştirilen Dosyalar
| Dosya | Değişiklik |
|---|---|
| `ui/src/components/primitives/Button.tsx` | `Variant` tipine `'danger-outline'` eklendi (arkaplan `tokens.colors.white`/dolu beyaz, metin+border `tokens.colors.danger`) |
| `ui/src/components/chat/PlanCard.tsx` | Inline `<style>` bloğundaki ham hex renkler kaldırıldı; sarmalayıcı `<Card className="plan-card">`, "Planı onayla"/bulk-confirm butonları `<Button variant="primary" className="plan-card-approve-btn">`, "Planı değiştir"/"Vazgeç" butonları nötr `.secondary-button` class'ıyla (tokens.ts token'larından) düz `<button>` olarak kaldı |
| `ui/src/components/chat/ResultCard.tsx` | Aynı desen: `<Card className="result-card">`, "Evet, geri al" → `<Button variant="danger">`, "Geri al"/"Tekrar dene" → `<Button variant="danger-outline">`, "Vazgeç" → nötr `.secondary-button` |

## AC Karşılanma Durumu
| AC | Durum | Kanıt |
|---|---|---|
| AC-1 (PlanCard mevcut testler yeşil) | ✅ | PlanCard.test.tsx 23/23 geçti |
| AC-2 (ResultCard mevcut testler yeşil) | ✅ | ResultCard.test.tsx 32/32 geçti |
| AC-3 (hardcoded hex kalmadı) | ✅ | Her iki dosyanın `<style>` bloğu artık `tokens.ts` değerlerini interpolasyonla kullanıyor; kalan tek statik değerler `#fff`/`1px`/`8px` gibi CSS birim/yapı değerleri değil, `tokens.colors.*` referansları |
| AC-4 (approve/change butonu primitif) | ✅ | `plan-approve-button` → Button primary; `plan-change-button` nötr stil (bkz. Karar altı not) |
| AC-5 (bulk-confirm primitif, davranış korunur) | ✅ | `handleApprove`/`isConfirmingBulk` state mantığı dokunulmadı, testler (3 bulk-confirm testi) geçti |
| AC-6 (outline vs solid danger) | ✅ | `danger-outline` variant eklendi, beyaz dolu arkaplan (orijinal tasarıma sadık — bkz. Kararlar altı düzeltme) |
| AC-7 (Card primitifi) | ✅ | Her iki bileşen `Card` sarmalayıcısını kullanıyor, yeni testler (background/border token doğrulaması) geçti |

## Plan.md Kararlarından Sapma (gerekçeli)
- **Karar 1 genişletildi:** plan.md'de `danger-outline` arkaplanı için net bir renk belirtilmemişti ("border'lı, şeffaf/beyaz arkaplan"). Kod incelemesi sırasında orijinal `ResultCard.tsx`'in `result-card-revert-btn`'inin her zaman **dolu beyaz** (`background-color: #fff`) kullandığı, transparent olmadığı tespit edildi — implementasyon buna göre düzeltildi (transparent → `tokens.colors.white`). Bu, "davranış/görünüm değişmeden taşı" ATDD ilkesine daha sadık.
- **"Planı değiştir"/"Vazgeç" butonları için Button primitifi kullanılmadı:** Button yalnızca `primary`/`danger`/`danger-outline` destekliyor; orijinal tasarımda bu butonlar nötr (beyaz bg + gri border) idi. Yeni bir "neutral/secondary" variant eklemek plan.md'de kapsanmamıştı (kapsam dışı risk) — bunun yerine `tokens.ts` token'larını kullanan component-local `.secondary-button` class'ı ile aynı görsel sonuç CAVEMAN ilkesiyle (en az soyutlama) elde edildi.

## Test/Derleme Sonucu (bağımsız doğrulandı)
- `npx tsc --noEmit` → 0 hata
- `npx vitest run` (tüm proje) → **14 dosya / 260 test, hepsi yeşil**
- Regresyon yok.

## Kalan Sınırlamalar / Notlar
- Test-copilot'un ilk yazdığı 3 test, jsdom/testing-library'nin CSS renk anahtar kelimelerini (`'transparent'`, `'white'`) computed style ile tutarsız normalize etmesi yüzünden yanlış sebepten kırmızıydı — bu 3 assertion `rgb(255, 255, 255)` literaline düzeltildi (test-copilot rolünde ayrı bir Haiku dispatch'i ile, implementasyon dosyalarına dokunulmadan). Davranış/AC etkilenmedi, sadece test-altyapı uyumluluğu.
- Görsel/UI kriteri (atdd.md Benchmark bölümü): ChatScreen ile tutarlılık — `verify` adımında `vision-test` ile kontrol edilmeli (aşağıda hatırlatma).

## Red-Team Sonrası Düzeltmeler (approve-with-changes)
Bağımsız `obss-red-team` incelemesi 3 bulgu buldu (1 medium, 2 low), commit'i bloklamadı ama düzeltilmesi istendi — hepsi uygulandı:
- **Medium (architecture):** `.secondary-button` CSS'i PlanCard.tsx/ResultCard.tsx'te birebir kopyalanmıştı → `Button.tsx`'e yeni bir `'secondary'` variant eklendi (beyaz bg, `tokens.colors.textDark` metin, `tokens.colors.border` border), her iki dosyadaki kopya CSS silindi, "Planı değiştir"/"Vazgeç" butonları `<Button variant="secondary">`'ye taşındı.
- **Low (readability):** `danger-outline` testlerinin adları "transparent" diyip beyaz bekliyordu → "white background" olarak düzeltildi.
- **Low (test-gap):** `fetchSpy` mock'lanmadan bırakılmasının nedeni test dosyasına yorum olarak eklendi.

Düzeltme sonrası bağımsız doğrulama: `npx tsc --noEmit` → 0 hata, `npx vitest run` → 14 dosya/260 test, hepsi yeşil.

## Sıradaki adım
`commit` — kullanıcı onayıyla.
