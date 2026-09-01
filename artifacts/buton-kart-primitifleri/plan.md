# Plan — buton-kart-primitifleri
_Reference: atdd.md_

## Files to Modify
(Yok — bu task saf ekleme, hiçbir mevcut dosya değişmiyor; AC-5 bunu zorunlu kılıyor.)

## New Files
| File | Purpose |
|------|---------|
| ui/src/components/primitives/Button.tsx | `variant` (`'primary' \| 'danger'`, default `'primary'`) ve `disabled` prop'u alan, `tokens.ts`'ten renk/ölçü okuyan React buton bileşeni. `PlanCard.tsx`'teki `.plan-card-approve-btn`/`.plan-card-change-btn` inline `<style>` deseni referans alınacak (aynı className+inline-style yaklaşımı, aynı data-testid konvansiyonu). |
| ui/src/components/primitives/Button.test.tsx | Vitest + RTL: her variant, `disabled` true/false, default variant render testleri (AC-1, AC-3). |
| ui/src/components/primitives/Card.tsx | `children` render eden, `tokens.colors.panelBackground`/`border` ve `tokens.radius.default` kullanan React kart bileşeni. |
| ui/src/components/primitives/Card.test.tsx | Vitest + RTL: children render, token değerlerinin uygulandığını doğrulayan testler (AC-2, AC-3). |
| ui/src/components/primitives/index.ts | `export { default as Button } from './Button'; export { default as Card } from './Card';` — named re-export (AC-6). |

## Dependencies
- `ui/src/tokens.ts` (Saga #345) — `colors.primary/primaryHover/primaryActive/danger`, `radius.default`, `size.buttonHeight`, `fontSize.base`, `spacing.buttonPadding`, `colors.panelBackground`, `colors.border`. Zaten var, değişmeyecek.
- Mevcut inline `<style>` + className deseni (`PlanCard.tsx` incelendi) referans alınacak — proje genelinde CSS-in-JS kütüphanesi yok, sade `<style>{`...`}</style>` bloğu + `className` kullanılıyor. Yeni primitifler bu deseni bozmadan sürdürecek.
- Test altyapısı: `ui/src/setupTests.ts` (RTL + jest-dom matcher kurulumu) zaten mevcut, yeni testler bunu otomatik miras alır — ek kurulum gerekmez.
- `package.json`'daki `"test": "vitest"` script'i doğrulandı, ek script gerekmiyor.

## Migration Required?
No — statik frontend bileşenleri, şema/veri değişikliği yok.

## Risks
- (atdd.md'den) Task #347 envanterinin örneklem olması riski — primitifler sadece `tokens.ts`'te açıkça var olan değerleri kullanacak, spekülatif prop eklenmeyecek.
- Yeni tespit: `PlanCard.tsx`'teki buton stilleri (`.plan-card-approve-btn`, `.plan-card-change-btn`) ile yeni `Button` primitifinin ürettiği görsel çıktı birebir aynı olmalı (ölçü/renk kaynağı zaten aynı `tokens.ts` olduğu için düşük risk, ama `code-copilot` bu iki tanımı satır satır karşılaştırmalı — border/hover/focus-visible/disabled state'leri (`#94A3B8` disabled rengi `tokens.ts`'te yok) primitife nasıl yansıyacağı netleştirilmeli).

## Open Questions
- `disabled` durumundaki buton rengi (`#94A3B8`, `PlanCard.tsx:125`) `tokens.ts`'te tanımlı değil — bu değeri primitif içinde sabit mi kullanacağız yoksa `tokens.ts`'e mi eklenecek? atdd.md bu task'ı "tokens.ts sadece import edilir, değişmez" olarak sınırlamış, bu yüzden `code-copilot` bu rengi primitif içinde yerel bir sabit olarak kullanmalı (token dosyasını genişletmeden) — bu karar aşağıda çözüldü.

## Kararlar
1. **Disabled buton rengi (`#94A3B8`) primitif içinde yerel sabit olarak kullanılacak, `tokens.ts` genişletilmeyecek** — atdd.md'nin "Etkilenen Dosyalar" bölümü `tokens.ts`'i "sadece import edilir, değişmez" olarak sabitlemiş; disabled state token envanterinde (task #347/#345) yer almıyor, bu nedenle mevcut sözleşmeyi bozmadan `Button.tsx` içinde `const DISABLED_COLOR = '#94A3B8'` gibi yerel bir sabit olarak tutulması en tutarlı seçim. (Karar, ana ajan tarafından atdd.md'nin kapsam sınırına dayanarak verildi — Haiku/claude-omni dispatch edilmedi çünkü tek bir açık soru vardı ve mevcut atdd.md kısıtı zaten cevabı belirliyordu.)

_(HTML/CSS UI dosyaları içeriyor — `verify` adımında gate 11 (`vision-test`) N/A değil AKTİF çalışacak.)_
