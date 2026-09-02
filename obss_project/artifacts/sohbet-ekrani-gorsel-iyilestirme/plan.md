# Plan — sohbet-ekrani-gorsel-iyilestirme
_Reference: atdd.md_

## Files to Modify
| File | Why | Risk |
|------|-----|------|
| ui/src/components/chat/ChatScreen.tsx | Inline `<style>` bloğundaki ham hex renkler (#1E3A8A, #E5E7EB, #F3F4F6, #111827, #6B7280, #DC2626, #FEF2F2, #FCA5A5, #B91C1C, #D1FAE5, #065F46, #A7F3D0, #FEE2E2, #991B1B, #FECACA) `tokens.ts` referanslarına taşınmalı (AC-1, AC-2, AC-3). Rendered .tsx dosyası → `verify` adımında vision-test (gate 11) aktif olacak. | medium — çok sayıda görsel durum (mesaj balonu, loading, error, success, buton varyantları) var, pixel-perfect korunmalı |
| ui/src/components/chat/TransactionHistoryPanel.tsx | Inline `style` prop'larındaki hex renkler (#E5E7EB, #059669, #DC2626, #6B7280, #111827) `tokens.ts`'e taşınmalı; `connectionStatus==='disconnected'` durumu `tokens.colors.danger` kullanmalı (AC-1, AC-4). Rendered .tsx → vision-test aktif. | low — tek dosya, sınırlı stil yüzeyi |
| ui/src/tokens.ts | Danger tonlarının açık/koyu varyantları (plan-error-indicator: #FEF2F2/#FCA5A5/#B91C1C, clear-history-error: #FEE2E2/#FECACA/#991B1B, clear-history-success: #D1FAE5/#065F46/#A7F3D0, connected-status: #059669) için yeni alanlar eklenmeli — mevcut hex değerler birebir korunarak (AC-5). | low — sadece ekleme, mevcut alanlar değişmiyor |

## New Files
(yok)

## Dependencies
- `ui/src/components/primitives/Button.tsx` ve `Card.tsx` (Epic #36'da eklendi) — **mevcut ama hiçbir bileşen tarafından henüz kullanılmıyor** (OnboardingScreen dahil, Epic #37 tamamlanmış olmasına rağmen tokens/primitifleri kullanmıyor — atdd.md'nin "önceki epic'ler aynı deseni izledi" varsayımı YANLIŞ çıktı, düzeltildi).
- `Button.tsx` sadece `primary`/`danger` varyantlarını destekliyor, sabit `tokens.size.buttonHeight` (44px) yüksekliğinde. ChatScreen'in küçük butonları (scroll-to-latest, search-toggle, clear-history, plan-retry — hepsi 32px yükseklik) bu şekle UYMUYOR.
- `Card.tsx` düz bir panel wrapper (`tokens.colors.panelBackground` arkaplan + `tokens.colors.border` çerçeve + `tokens.radius.default`), padding prop'u yok — TransactionHistoryPanel'in 12px padding + sadece `border-right` (tam çerçeve değil) ihtiyacına birebir uymuyor.
- Mevcut `data-testid`, `role`, `aria-*` özellikleri (chat-message-list, plan-loading-indicator, plan-error-indicator, chat-clear-history-*-message, connection-status, transaction-history-loading/error vb.) DEĞİŞMEMELİ — testler bunlara bağlı.

## Migration Required?
Hayır — sadece frontend CSS/inline-style değişikliği, şema/veri değişikliği yok.

## Risks
- (atdd.md'den) tokens.ts'in mevcut inline hex değerlerle birebir eşleşmediği bir durum bulunursa sessizce "iyileştirme" yapılmamalı — bu görevde YASAK.
- (yeni) `Button`/`Card` primitiflerini ChatScreen'in 32px küçük butonlarına ZORLA uygulamaya çalışmak, ya primitifi genişletmeyi (yeni `size` prop'u) ya da görsel regresyonu (buton boyutu değişir) gerektirir — ikisi de atdd.md'nin "kapsam dışı: layout/davranış değişikliği yok" ve "pixel-perfect taşıma" kurallarıyla gerilim yaratıyor.
- (yeni) Card.tsx padding almıyor; TransactionHistoryPanel'e olduğu gibi uygulanırsa 12px padding'i kaybeder — ya Card className/style ile override edilmeli ya da Card kullanılmayıp sadece tokens renkleri her iki dosyada da düz inline style olarak kalmalı.

## Open Questions — Kararlar
(Tüm sorular `claude-omni`/OmniRoute üzerinden yanıtlandı — sadece atdd.md ve
bu plan.md okunarak, kod tabanı tekrar taranmadan.)

1. **32px küçük butonlar (scroll-to-latest, search-toggle, clear-history, plan-retry):**
   Karar: **(a) — sadece renkleri tokens'a taşı, Button primitifini KULLANMA, boyut/yapı aynen korunur.**
   (claude-omni/OmniRoute üzerinden yanıtlandı: Button primitifi sadece primary/danger + sabit 44px destekliyor; ona uydurmak ya primitifi genişletmeyi ["yeni özellik eklemek" → kapsam dışı] ya da görsel regresyonu ["pixel-perfect" ihlali] gerektirirdi.)

2. **TransactionHistoryPanel + Card primitifi:**
   Karar: **Card primitifi KULLANILMAYACAK — mevcut `<div>` yapısı ve 12px padding/`border-right` aynen korunur, sadece renkler `tokens.*`'a çevrilir.**
   (claude-omni/OmniRoute üzerinden yanıtlandı: Card.tsx padding prop'u desteklemiyor ve tam çerçeve/arkaplan uyguluyor, mevcut panel yapısına uymuyor; override etmek layout değişikliği riski taşır.)

3. **tokens.ts yeni alan isimlendirmesi:**
   Karar: `colors.dangerBg`/`colors.dangerBorder`/`colors.dangerText` ve `colors.successBg`/`colors.successBorder`/`colors.successText` ve `colors.connected` kalıbı kullanılacak.
   **Düzeltme (orkestratör tarafından, omni'nin gözden kaçırdığı nokta):** ChatScreen'de İKİ FARKLI danger-banner rengi var — plan-error-indicator (#FEF2F2/#FCA5A5/#B91C1C) ile chat-clear-history-error-message (#FEE2E2/#FECACA/#991B1B) farklı hex değerlere sahip; tek bir `dangerBg/dangerBorder/dangerText` grubu ikisini birden karşılayamaz (pixel-perfect kuralı ihlal olur). Bu nedenle iki ayrı grup eklenecek: `colors.dangerBannerBg`/`dangerBannerBorder`/`dangerBannerText` (plan-error-indicator, #FEF2F2/#FCA5A5/#B91C1C) ve `colors.dangerMessageBg`/`dangerMessageBorder`/`dangerMessageText` (clear-history-error, #FEE2E2/#FECACA/#991B1B). Success grubu (`successBg`/`successBorder`/`successText`, #D1FAE5/#065F46/#A7F3D0) ve `colors.connected` (#059669) tek grup olarak yeterli (tek kullanım yeri var).
