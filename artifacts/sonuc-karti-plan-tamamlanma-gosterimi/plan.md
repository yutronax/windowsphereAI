# Plan — Sonuç Kartı (Saga #277)

## Dosyalar

- **Yeni:** `ui/src/components/chat/ResultCard.tsx`
  - `TransactionResult = { fileCount: number; destinationFolders: string[]; status: 'completed' | 'partial' | 'failed' }`
  - Props: `{ result: TransactionResult }`
  - `data-testid="result-card"`, dosya sayısı `data-testid="result-file-count"`,
    klasör listesi `data-testid="result-destination-folders"`, boş liste
    durumu için ayrı bir metin, durum metni `aria-live="polite"` bölgesinde.
  - PlanCard'daki stil deseniyle tutarlı (`<style>` bloğu, aynı renk paleti).

- **Yeni:** `ui/src/components/chat/ResultCard.test.tsx`
  - AC-2/AC-3/AC-4/AC-6'yı izole test eder.

- **Düzenlenecek:** `ui/src/components/chat/ChatScreen.tsx`
  - `ChatMessage` tipine `result?: TransactionResult` eklenir.
  - Mesaj render bloğunda (`PlanCard`'ın yanına, satır ~244-252
    civarı) `message.result &&  <ResultCard result={message.result} />`
    eklenir.
  - `ChatScreen.test.tsx`'e AC-1 (render/render-etmeme) ve AC-5
    (input etkinliği) testleri eklenir.

## Kapsam dışı (bilinçli)
- Backend'e endpoint/response şeması eklemek — Saga #285'e bağlı.
- `App.tsx` wiring — Saga #285.
- Hata/rollback sonucu UI'ı — kapsam dışı, task başlığı "başarılı
  işlem sonucu" diyor.
- Yeni bir `isApplyingPlan` state'i — bugün test edilemez, kapsam dışı.

## Doğrulama
- `npx vitest run` (ui/) — mevcut 103 test + yeni testler yeşil olmalı.
- Red-team: obss-red-team subagent, gerçek diff üzerinden.
