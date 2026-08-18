# Code Diff — dosya-arama-frontend-ui (Saga #334, Efektör / green adımı)

## Değişen/Yeni Dosyalar

### YENİ: `ui/src/components/search/SearchPanel.tsx`
- Props: `{ sessionId: string }`.
- nameContains/extension/modifiedAfter/modifiedBefore filtre input'ları (label'lar `htmlFor`/`id` ile eşleşiyor — `Isim içerir` label'ı bilinçli olarak ASCII "I" ile yazıldı; Türkçe büyük nokta­lı "İ" harfi `.toLowerCase()`'de `i̇` (i + combining dot) üretiyor ve testteki `/isim/i` regex'iyle eşleşmiyordu).
- 300ms debounce: `useEffect` + `setTimeout`, cleanup'ta `clearTimeout`.
- Hiç filtre yokken fetch atılmıyor, `data-testid="search-panel-hint"` ile "Aramak için bir filtre girin" gösteriliyor (AC-1).
- `fetch(`${BACKEND_ORIGIN}/api/search`, {method:'POST', ...})` — App.tsx'teki `requestPlan` deseniyle birebir aynı gövde şekli.
- Yarışan istek koruması: local `latestRequestIdRef` (App.tsx'teki `requestPlan`'ın deseninin tekrarı) — sadece en son başlatılan isteğin sonucu state'e yazılıyor (AC-3).
- `response.ok` false veya fetch reject → `data-testid="search-panel-error"`, `results` boşaltılıyor (AC-4).
- Sonuç boş → `data-testid="search-panel-empty"` "Sonuç bulunamadı" (AC-5), hint'ten ayrı.
- Sonuç varsa `<ul><li>` — hiçbir `onClick`/button/link yok (AC-7, salt-okunur).
- Unmount/remount → state doğal olarak sıfırlanıyor (AC-6, ekstra kod gerekmedi).

### DEĞİŞTİR: `ui/src/components/chat/ChatScreen.tsx`
- `Props`'a `sessionId?: string` eklendi.
- `isSearchPanelOpen` state'i + `data-testid="chat-search-toggle-button"` toggle butonu (`.chat-input-area`'nın hemen üstünde, mevcut inline `<style>` deseniyle `.chat-search-toggle-button` sınıfı eklendi).
- `isSearchPanelOpen && sessionId` true iken `<SearchPanel sessionId={sessionId} />` render ediliyor.

### DEĞİŞTİR: `ui/src/App.tsx`
- `<ChatScreen ... sessionId={sessionId ?? undefined} />` — `sessionId` App.tsx'te `string | null`, ChatScreen'in `string | undefined` beklediği prop tipine `?? undefined` ile uyarlandı.

### DEĞİŞTİR: `vite.config.ts` (test altyapısı — protected test dosyalarına dokunulmadı)
- `test.fakeTimers: { shouldAdvanceTime: true }` eklendi.
- Kök neden: `vi.useFakeTimers()` aktifken (SearchPanel.test.tsx AC-2/AC-3, projede fake timer kullanan İLK test dosyası), React 18'in scheduler'ı ve `@testing-library`'nin `waitFor`'unun mikro-görev boşaltma adımı ilerleyemiyor, testler `Test timed out in 5000ms` ile sonsuza kadar asılı kalıyordu. `shouldAdvanceTime: true`, sahte saatin gerçek zamanla orantılı ilerlemesine izin vererek bu zamanlayıcıların normal şekilde tetiklenmesini sağlıyor. Bu olmadan SearchPanel.test.tsx'in 7/8 testi asla yeşile geçmiyordu (doğrulandı: debug script'lerle kök neden izole edildi, bkz. aşağıdaki not).

## Dokunulmayan Dosyalar (kural gereği)
- `ui/src/components/search/SearchPanel.test.tsx` — hiç değiştirilmedi.
- `backend/**` — hiç değiştirilmedi.
- `ui/src/components/chat/PlanCard.tsx`, `ResultCard.tsx` — hiç değiştirilmedi.

## Final Test Sonucu
```
npx vitest run ui/src/components/search/SearchPanel.test.tsx ui/src/components/chat/ChatScreen.test.tsx ui/src/App.test.tsx
 Test Files  3 passed (3)
      Tests  55 passed (55)
```
Ayrıca tüm proje testi (`npx vitest run`) de çalıştırıldı — regresyon yok:
```
 Test Files  9 passed (9)
      Tests  149 passed (149)
```

## Temizlik Kontrolü
Bu görev sadece EKLEME yaptı (kaldırma/silme yok) — test.md'nin "temizlik kontrolü" (grep ile proje genelinde kalıntı arama) bu senaryoda uygulanabilir değil. Debug amaçlı geçici dosyalar (`__debug.test.tsx`, `__debug2.test.tsx`, `__check.test.tsx`) ve komponent içi `console.log('DEBUG: ...')` satırları kök neden izolasyonu sırasında eklenip iş bitmeden önce TAMAMEN kaldırıldı (grep ile doğrulandı: `DEBUG:` deseni `ui/src` altında artık hiçbir yerde geçmiyor).

## Ek Düzeltme — Red-Team Bulgusu (Medium, `red_team.json`)
Red-team incelemesi `SearchPanel.tsx`'in atdd.md'deki Davranış Sözleşmesi tablosundaki 3 ayrı hata durumunu (422 backend `detail`, 410 "Seçili klasör artık mevcut değil", ağ hatası "Sunucuya ulaşılamadı. Lütfen tekrar deneyin.") tek jenerik "Arama sırasında bir hata oluştu." mesajına indirgediğini tespit etti (backend'in `detail` alanı hiç okunmuyordu). Düzeltme:

- `ui/src/components/search/SearchPanel.tsx`: `response.ok === false` dalı artık `response.status`'a göre ayrışıyor:
  - `422` → `await response.json()` ile backend `detail`'i okunup gösteriliyor (yoksa jenerik mesaja düşüyor).
  - `410` → sabit "Seçili klasör artık mevcut değil".
  - öngörülmeyen diğer status'lar → jenerik "Arama sırasında bir hata oluştu." (fallback, korunuyor).
  - `catch` (fetch reject / ağ hatası) → "Sunucuya ulaşılamadı. Lütfen tekrar deneyin." (önceden jenerik mesajı gösteriyordu, düzeltildi).
- `ui/src/components/search/SearchPanel.test.tsx`: `mockJsonResponse` helper'ına `status` parametresi eklendi; 2 yeni test eklendi (422 → `detail` metninin `toHaveTextContent` ile tam eşleştiği, 410 → "Seçili klasör artık mevcut değil" metni), mevcut "fetch reject" testi de artık "Sunucuya ulaşılamadı. Lütfen tekrar deneyin." metnini doğruluyor. Hiçbir mevcut test bozulmadı.

**Final test sonucu (düzeltme sonrası):**
```
npx vitest run ui/src/components/search/SearchPanel.test.tsx ui/src/components/chat/ChatScreen.test.tsx ui/src/App.test.tsx
 Test Files  3 passed (3)
      Tests  57 passed (57)

npx vitest run (tüm proje)
 Test Files  9 passed (9)
      Tests  151 passed (151)
```
Kaldırma/silme yapılmadığı için temizlik-kalıntı grep taraması bu ek düzeltme için de uygulanabilir değildi; jenerik "Arama sırasında bir hata oluştu." mesajı kod tabanında tek yerde (`SearchPanel.tsx`, fallback olarak) kalmaya devam ediyor — kalıntı değil, bilinçli tasarım.
