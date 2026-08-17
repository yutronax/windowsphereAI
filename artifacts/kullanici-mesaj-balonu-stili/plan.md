# Plan — Kullanıcı mesaj balonu stili (Saga #260)

## Değiştirilecek dosya
- `ui/src/components/chat/ChatScreen.tsx`
  - Mesaj `<li>` içindeki `{message.text}` bir `<div className="chat-message-bubble"
    data-testid={...}>` ile sarmalanır (PlanCard dışarıda kalır).
  - CSS: `.chat-message-bubble` (padding:16px, border-radius:14px,
    max-width:65ch, word-wrap:break-word).
  - `.chat-message-item[data-role="user"] .chat-message-bubble` —
    background:#1E3A8A, color:#fff.

## Yeni bağımlılık yok
