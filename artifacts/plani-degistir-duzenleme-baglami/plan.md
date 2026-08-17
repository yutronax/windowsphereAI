# Plan — Planı değiştir düğmesi (Saga #264)

## Değiştirilecek dosyalar
- `ui/src/components/chat/PlanCard.tsx`
  - `onChangePlan?: () => void` ve `stale?: boolean` prop'ları eklenir.
  - "Planı değiştir" düğmesi eklenir (`data-testid="plan-change-button"`),
    tıklanınca sadece `onChangePlan?.()` çağırır (onApprove ÇAĞRILMAZ).
  - `stale` true ise: onay düğmesi disabled, statusText
    "Bu plan artık geçerli değil, yeni plan bekleniyor." olur
    (`data-testid="plan-stale-status"`), mevcut rejection/pending mantığından
    önce kontrol edilir.
- `ui/src/components/chat/ChatScreen.tsx`
  - `textareaRef` (useRef<HTMLTextAreaElement>) eklenir.
  - `editingPlanMessageId: string | null` state.
  - `staleMessageIds: Set<string>` state.
  - `handleChangePlan(messageId)`: `setEditingPlanMessageId(messageId)`,
    `textareaRef.current?.focus()`.
  - İpucu metni: `editingPlanMessageId` varken textarea üstünde
    `data-testid="chat-edit-plan-hint"`, `aria-live="polite"` ile gösterilir:
    "Planı değiştirmek için ne yapmak istediğinizi yazın."
  - `sendDraft()`: mesaj başarıyla eklendiğinde (trimmed boş değilse),
    `editingPlanMessageId` set ise o id `staleMessageIds`'e eklenir ve
    `editingPlanMessageId` null'a çekilir.
  - `PlanCard` render edilirken `onChangePlan={() => handleChangePlan(message.id)}`
    ve `stale={staleMessageIds.has(message.id)}` geçilir.

## Yeni bağımlılık yok
Mevcut React state/ref yeterli, yeni paket gerekmiyor.

## Riskler
- `staleMessageIds` bir `Set` — her render'da yeni referans oluşturulmalı
  (immutable update) yoksa React değişikliği algılamaz.
