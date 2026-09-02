# Test Diff — arama-paneli-gorsel-tutarlilik
_Red step — implementasyon henüz yok, aşağıdaki 5 yeni test BAŞARISIZ olması beklenir._

## Genişletilen Dosya
`ui/src/components/search/SearchPanel.test.tsx` — 5 yeni test eklendi, mevcut 9 test dokunulmadan korundu.

## AC Eşlemesi
| Test | AC |
|---|---|
| `applies Card primitif token styles to the search-panel wrapper` | AC-2 |
| `applies input style tokens to the nameContains input` | AC-3 |
| `applies result list style tokens when results are present` | AC-4 |
| `applies danger color token to the error message` | AC-5 |
| `applies hint and empty message style tokens` | AC-6 |

AC-1 (mevcut testler değişmeden yeşil) ve AC-7 (read-only liste) zaten mevcut 9 test tarafından kapsanıyor, yeni test gerekmedi.

## Varsayımlar
- Testler şu an RED: `SearchPanel.tsx` hiç `<style>` bloğu içermiyor.
- Token referansları literal string değil, doğrudan `tokens.colors.*`/`tokens.fontSize.*`/`tokens.radius.*` objesi üzerinden (jsdom keyword-normalizasyon sorunundan kaçınmak için, önceki task'ta kanıtlanmış yaklaşım).

## Sıradaki adım
`code-copilot` — SearchPanel.tsx'e Card primitifi + tokens.ts tabanlı stil ekleyecek implementasyonu yazacak.
