# Plan — Otomatik kaydırma / "En yeni mesaja dön" (Saga #266)

## Değiştirilecek dosya
- `ui/src/components/chat/ChatScreen.tsx`
  - `listRef = useRef<HTMLUListElement>(null)` eklenir, `ul`'a bağlanır.
  - `isAtBottom` state (varsayılan `true`).
  - `BOTTOM_THRESHOLD_PX = 24` sabiti.
  - `handleScroll()`: `list.scrollHeight - list.scrollTop - list.clientHeight
    <= BOTTOM_THRESHOLD_PX` ise `isAtBottom(true)`, değilse `isAtBottom(false)`.
    `ul`'a `onScroll={handleScroll}` eklenir.
  - `useEffect(() => { if (isAtBottom) scrollToBottom(); }, [messages.length])`
    — sadece mesaj SAYISI değiştiğinde tetiklenir (her render'da değil).
  - `scrollToBottom(smooth = true)`: `list.scrollTo({ top: list.scrollHeight,
    behavior: smooth ? 'smooth' : 'auto' })`; jsdom'da `scrollTo` yoksa
    fallback olarak `list.scrollTop = list.scrollHeight` de atanır (jsdom
    HTMLElement.scrollTo native değil, testte manuel çağrılabilir hale
    getirilecek — gerekirse basit bir `if (list.scrollTo) ... else ...`
    guard'ı).
  - `!isAtBottom` iken mesaj listesinden sonra bir düğme:
    `data-testid="chat-scroll-to-latest-button"`, "En yeni mesaja dön",
    `onClick`: `scrollToBottom(); setIsAtBottom(true);`.

## Yeni bağımlılık yok
Saf React state/ref + native `scrollTo`.

## Riskler
- jsdom'da `Element.prototype.scrollTo` tanımlı değil (`TypeError` riski) —
  guard ile korunacak.
