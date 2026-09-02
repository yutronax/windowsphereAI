# Plan — plan-result-kartlari-tasarim
_Reference: atdd.md_

## Files to Modify
| File | Why | Risk |
|------|-----|------|
| ui/src/components/chat/PlanCard.tsx | Inline `<style>` bloğunu kaldırıp `Card`/`Button` primitiflerine taşı (AC-1, AC-3, AC-4, AC-5, AC-7); `plan-approve-button`/`plan-change-button`/`plan-bulk-confirm-button`/`plan-bulk-confirm-cancel-button` butonları primitife geçer | medium — `canApprove`/`isBulk`/`hasApproved` state mantığı korunmalı, davranış testleri var |
| ui/src/components/chat/ResultCard.tsx | Inline `<style>` bloğunu kaldırıp `Card`/`Button` primitiflerine taşı (AC-2, AC-3, AC-6, AC-7); `result-revert-button`/`-confirm-button`/`-cancel-button`/`-retry-button` primitife geçer | medium — outline-danger (`result-card-revert-btn`) stili Button primitifinin şu anki `danger` variantıyla (dolu arkaplan) birebir örtüşmüyor, bkz. Open Questions |
| ui/src/components/primitives/Button.tsx | AC-6 gereği muhtemelen yeni bir outline/danger-outline variant eklenmesi gerekebilir | medium — mevcut `primary`/`danger` variant sözleşmesini kırmadan genişletme; `Button.test.tsx`'teki mevcut testler bozulmamalı |
| ui/src/components/chat/PlanCard.test.tsx | `plan-approve-button`'ın `toHaveClass('plan-card-approve-btn')` beklediği satır (satır 118) — primitife geçişte bu class'ın Button'a `className` prop'uyla açıkça verilmesi gerekiyor, aksi halde test kırılır | high — bu satır atlanırsa test kırmızıya döner; ya className korunur ya da test bilinçli güncellenir (davranış değil, sadece görünüm-ilgili bir assertion) |
| ui/src/components/chat/ResultCard.test.tsx | Buton class'larına dair benzer bir assertion olup olmadığı doğrulanmalı (bulunan tek `toHaveClass` kullanımı `is-failed` — durum metnine ait, butona değil, düşük risk) | low |

## New Files
Yok — bu görev saf refactor, yeni dosya gerektirmiyor. (AC-6'nın çözümüne göre Button.tsx içinde yeni bir variant eklenmesi "New Files" değil "Files to Modify" kapsamında kalır.)

## Dependencies
- `ui/src/tokens.ts` — hem PlanCard/ResultCard hem Button/Card zaten buradan token okuyor; bu görev sadece PlanCard/ResultCard'ın bu kaynağa (primitifler üzerinden) bağlanmasını sağlıyor, tokens.ts'in kendisi değişmeyecek (atdd.md'nin varsaydığı gibi).
- `ui/src/components/primitives/index.ts` — Button/Card export barrel'ı; PlanCard/ResultCard import'ları muhtemelen `../primitives` üzerinden yapılacak (ChatScreen'in nasıl import ettiği örnek alınmalı — bkz. Open Questions).
- Mevcut `Button.test.tsx`/`Card.test.tsx` — yeni variant eklenirse bu dosyalara yeni test case'leri eklenmesi gerekecek (test-copilot'un scope'unda).

## Migration Required?
Hayır — DB/schema/backend değişikliği yok, saf frontend UI refactor.

## Risks
- (atdd.md'den taşındı) Button primitifi şu an sadece dolu (solid) `primary`/`danger` variant destekliyor; ResultCard'ın outline-kırmızı `result-card-revert-btn` butonu bu sözleşmeye uymuyor.
- (yeni bulgu) `PlanCard.test.tsx:118` doğrudan `plan-card-approve-btn` CSS class adını assert ediyor — primitife geçişte bu class'ın varlığı korunmalı (className prop'uyla) ya da test güncellenmeli. Testi "davranışsal olmayan, görünüme bağlı" olarak güncellemek ATDD'nin "testler değişmeden yeşil kalır" AC'siyle gergin bir nokta — kullanıcıya/test-copilot'a açıkça sorulmalı.
- Erişilebilirlik özellikleri (`aria-describedby`, `aria-live`, `aria-label`) primitife taşınırken JSX yapısı değiştiği için kaybolma riski var — Button/Card `...props` spread ile bunları kabul ediyor, ama entegrasyon sırasında elle doğrulanmalı.

## Open Questions
1. **Button primitifi outline-danger variant'ı destekleyecek mi?** (atdd.md Unknowns'tan taşındı) `result-card-revert-btn` (outline kırmızı) ile `result-card-revert-confirm-btn`/`plan-card-approve-btn` (dolu) farklı görsel diller — ya Button'a 3. bir variant (`danger-outline`) eklenmeli ya da bu tek buton component-local stilde bırakılmalı.
2. **`PlanCard.test.tsx:118`'deki `toHaveClass('plan-card-approve-btn')` assertion'ı ne olacak?** className prop'uyla Button'a bu sınıf adı açıkça geçirilip test aynen korunabilir (CSS olarak boş/anlamsız bir class, sadece test-hook) — bu en düşük riskli yol. Alternatif: testi primitif-aware bir assertion'a güncellemek (örn. `toHaveStyle` ile 44px yüksekliği kontrol etmek) — ama bu, atdd.md'nin "mevcut testler değişmeden yeşil kalır" AC-1'ini gevşetir. Öneri: className'i koru, testi değiştirme.
3. **PlanCard/ResultCard, primitifleri nasıl import edecek?** `../primitives` barrel'ından mı (`import { Button, Card } from '../primitives'`) yoksa doğrudan dosyadan mı (`from '../primitives/Button'`) — ChatScreen'in mevcut import deseni örnek alınmalı (test-copilot/code-copilot aşamasında `ChatScreen.tsx`'e bakılarak karar verilsin, ek bir soru turu gerektirmez).

## Kararlar
1. **Button primitifi `danger-outline` variant'ı destekleyecek.** (Haiku alt-ajanı tarafından yanıtlandı: tasarım sistemi tutarlılığı — AC-3 hedefi tüm renklerin tokens.ts'den gelmesi — ve component-local override yerine primitif genişletmenin uzun vadeli bakım kolaylığı sağlaması nedeniyle önerildi.) → `Button.tsx`'e `variant: 'primary' | 'danger' | 'danger-outline'` eklenecek, `Button.test.tsx`'e yeni case'ler eklenmesi gerekecek (test-copilot scope'unda).
2. **`PlanCard.test.tsx:118`'deki `toHaveClass('plan-card-approve-btn')` korunacak, test DEĞİŞTİRİLMEYECEK.** (Haiku alt-ajanı tarafından yanıtlandı: atdd.md AC-1 "mevcut testler değişmeden yeşil kalır" kritik işaretli; className'i Button'a prop olarak geçirmek — CSS'siz, sadece test-hook — en düşük riskli yol.) → `<Button className="plan-card-approve-btn" ...>` şeklinde kullanılacak.
