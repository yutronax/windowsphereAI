# test_diff.md — dosya-arama-frontend-ui (ATDD red step)

Saga task: #334

## Eklenen dosya
`ui/src/components/search/SearchPanel.test.tsx` (yeni, implementasyon YOK — `SearchPanel.tsx` henüz mevcut değil)

## Eklenen testler ve kapsadıkları AC'ler

| # | Test adı | AC |
|---|---|---|
| 1 | renders an empty result list with the "enter a filter" hint and does not call fetch initially | AC-1 |
| 2 | debounces nameContains input and calls fetch exactly once after 300ms, rendering results | AC-2 |
| 3 | only shows the result of the most recently sent request when requests race | AC-3 |
| 4 | shows an error message and clears the result list when fetch rejects | AC-4 |
| 5 | shows an error message and clears the result list when response.ok is false | AC-4 |
| 6 | shows a "no results" message distinct from the initial hint when filters match nothing | AC-5 |
| 7 | resets filters/results state when unmounted and remounted | AC-6 |
| 8 | does not trigger any action when a result row is clicked (read-only list) | AC-7 |

## Test deseni notları
- Vitest `vi.useFakeTimers()` + `vi.advanceTimersByTime(300)` ile debounce doğrulandı (ChatScreen/PlanCard testlerindeki `fireEvent`/`screen` deseniyle tutarlı).
- `vi.stubGlobal('fetch', vi.fn())` ile fetch mock'landı; App.tsx'teki `latestRequestIdRef` yarışan-istek desenine paralel olarak AC-3 testinde iki ayrı `deferred()` promise ile "geç çözülen ilk istek, ekranı geri almamalı" senaryosu kuruldu.
- Beklenen prop arayüzü: `<SearchPanel sessionId={string} />`, fetch çağrısı `${BACKEND_ORIGIN}/api/search` POST body'sinde `sessionId` içerir (görev talimatındaki varsayıma göre).
- AC-7 testi component'in henüz yazılmamış olması nedeniyle `<button>`/`<a>` rolü OLMADIĞINI varsayıyor; SearchPanel implementasyonu satırları `<li>`/`<div>` gibi tıklanamaz elemanlarla render etmeli.

## Test çalıştırma sonucu (red step — beklenen)
Komut (proje kökünden, `vite.config.ts`'nin `include: ['ui/src/**/*.test.{ts,tsx}']` deseni gereği `ui/` alt dizininden DEĞİL, kök dizinden çalıştırılmalı):

```
npx vitest run ui/src/components/search/SearchPanel.test.tsx
```

Sonuç: **FAIL** (beklenen) — `SearchPanel.tsx` henüz yok:

```
FAIL  ui/src/components/search/SearchPanel.test.tsx [ ui/src/components/search/SearchPanel.test.tsx ]
Error: Failed to resolve import "./SearchPanel" from "ui/src/components/search/SearchPanel.test.tsx". Does the file exist?
Test Files  1 failed (1)
Tests  no tests
```

Bu, ATDD "red" adımının beklenen çıktısıdır: testler mevcut olmayan `SearchPanel` component'ini import ettiği için modül çözümleme hatasıyla kırmızı. Implementasyon (`SearchPanel.tsx`) yazılınca bu test dosyası gerçek AC doğrulamalarını çalıştıracak.

## Açık sorular
- Yok — görevde verilen prop/fetch sözleşmesi (sessionId, BACKEND_ORIGIN, body alanları) yeterince netti; SearchPanel implementasyonu bu sözleşmeye göre yazılmalı.
