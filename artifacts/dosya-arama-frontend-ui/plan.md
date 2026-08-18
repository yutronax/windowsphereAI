# Plan — dosya-arama-frontend-ui
_Reference: atdd.md_

## Files to Modify
| File | Why | Risk |
|------|-----|------|
| ui/src/App.tsx | `<ChatScreen>`'e `sessionId` prop olarak geçirilir — şu an ChatScreen'e hiç geçirilmiyor (atdd.md Unknowns'ta netleştirilen konu, koda bakılarak doğrulandı: satır 150-160) | low |
| ui/src/components/chat/ChatScreen.tsx | `sessionId` prop'u kabul eder, `isSearchPanelOpen` state'i + toggle butonu eklenir (input-area'nın üstünde, mevcut `.chat-input-area` bloğuna yakın), `isSearchPanelOpen` true iken `<SearchPanel>` render edilir | medium |

## New Files
| File | Purpose |
|------|---------|
| ui/src/components/search/SearchPanel.tsx | Arama input'ları (nameContains/extension/modifiedAfter/modifiedBefore), debounce, fetch(`/api/search`), sonuç listesi, hata/hint state yönetimi (AC-1..8) |
| ui/src/components/search/SearchPanel.test.tsx | Component testleri (test-copilot bu dosyayı yazacak) |

## Dependencies
- `ui/src/lib/backendHealth.ts::BACKEND_ORIGIN` — SearchPanel'in fetch çağrısı bunu kullanacak (App.tsx'teki `requestPlan`'ın deseniyle tutarlı: `fetch(\`${BACKEND_ORIGIN}/api/search\`, ...)`).
- `backend/models.py::SearchRequest`/`SearchResponse`/`SearchResultItem` — TypeScript tarafında karşılık gelen tipler SearchPanel.tsx içinde tanımlanacak (projede paylaşımlı bir tip-üretim mekanizması yok, `PlanCard.tsx`/`ResultCard.tsx`'in kendi local tip tanımlama deseni izlenecek).
- Yarışan istek sırası (AC-3) için App.tsx'teki `requestPlan`'daki `latestRequestIdRef` deseni SearchPanel içinde kendi local `useRef` ile tekrarlanacak (paylaşımlı bir hook yok, mevcut kod tabanı bu deseni her yerde inline tekrarlıyor — örnek: App.tsx satır 27, 43-44).

## Migration Required?
Hayır.

## Risks
- (atdd.md'den taşındı, plan'da doğrulandı) `sessionId` gerçekten ChatScreen'e geçirilmiyordu — App.tsx ve ChatScreen.tsx'in her ikisi de değişmeli, tek dosyalık bir iş değil.
- Debounce + yarışan istek testleri (AC-2, AC-3) `jest.useFakeTimers()`/`vi.useFakeTimers()` gerektirir — mevcut test dosyalarında (`ChatScreen.test.tsx`) fake timer kullanımı var mı kontrol edilmeli, yoksa test-copilot'a bu deseni kurması için extra_instructions gerekir.

## Open Questions
Yok — atdd.md'nin Unknowns'ı (sessionId prop yolu) bu plan turunda koda bakılarak çözüldü.
