# Plan — arama-paneli-gorsel-tutarlilik
_Reference: atdd.md_

## Files to Modify
| File | Why | Risk |
|------|-----|------|
| ui/src/components/search/SearchPanel.tsx | Şu an tamamen stilsiz — `Card` primitifi + `<style>` bloğu (tokens.ts referanslı) eklenecek (AC-1..AC-7) | low — test dosyası saf davranışsal, className/style assertion'ı yok |

## New Files
Yok — atdd.md'nin Assumptions bölümünde de belirtildiği gibi input alanları için yeni bir primitif GEREKMİYOR, mevcut `ChatScreen.tsx`'teki `.chat-input-textarea` deseni (aşağıya bakınız) component-local class olarak SearchPanel'e uygulanabilir.

## Dependencies / Gerçek Kod Keşfi
- `ui/src/tokens.ts` (mevcut, DEĞİŞMEYECEK) — gerçek token'lar: `colors.{primary,border,danger,textSecondary,textMuted,textDark,panelBackground,white,...}`, `radius.default` ('8px'), `size.buttonHeight` ('44px'), `fontSize.{small,base}` ('14px'/'16px'), `spacing.buttonPadding` ('0 20px'). **atdd.md'nin Risks bölümünde işaretlediği gibi `tokens.spacing.md`/`tokens.spacing.sm` GERÇEKTE YOK** — Haiku'nun ATDD aşamasındaki önerisi hatalıydı, kullanılmayacak. Spacing için literal px değerleri (mevcut projede zaten `padding: '12px 16px'`, `marginTop: '8px'` gibi literal kullanım yaygın — bkz. PlanCard.tsx/ChatScreen.tsx) kullanılacak.
- `ui/src/components/primitives/Card.tsx` (mevcut, DEĞİŞMEYECEK) — `backgroundColor: tokens.colors.panelBackground`, `border: 1px solid ${tokens.colors.border}`, `borderRadius: tokens.radius.default`. `style` prop kabul ETMİYOR (`Omit<HTMLAttributes, 'style'>`) — PlanCard/ResultCard görevinde bu yüzden `className` + inline `<style>` bloğu deseni kullanılmıştı, aynı desen burada da izlenecek.
- **Gerçek input stil emsali bulundu:** `ChatScreen.tsx` satır 228-241, `.chat-input-textarea` class'ı:
  ```
  border-radius: 8px;              → tokens.radius.default
  border: 1px solid ${tokens.colors.border};
  padding: 8px 12px;
  font-size: 16px;                 → tokens.fontSize.base
  ```
  Bu desen SearchPanel'in 4 `<input>` elemanına aynen uygulanacak — "SearchPanel ilk input stili" değil, ChatScreen'in zaten kurduğu deseni takip ediyor (atdd.md'nin Unknowns bölümündeki soru burada çözüldü: yeni token GEREKMİYOR, mevcut desen yeterli).
- `ui/src/components/chat/PlanCard.tsx` (referans, DEĞİŞMEYECEK) — liste/meta/durum-metni deseni (`tokens.colors.textSecondary`, `tokens.fontSize.small`) SearchPanel'in sonuç listesi ve hint/empty mesajları için birebir uygulanacak.
- `ui/src/components/chat/ResultCard.tsx` (referans, DEĞİŞMEYECEK) — `is-failed`/danger metin deseni (`tokens.colors.danger`) SearchPanel'in `search-panel-error` mesajı için uygulanacak.

## Migration Required?
Hayır — DB/schema değişikliği yok, saf frontend CSS ekleme.

## Risks
- (atdd.md'den taşındı, ÇÖZÜLDÜ) `tokens.spacing.md`/`sm` halüsinasyonu — gerçek tokens.ts'de yok, kullanılmayacak, literal px değerleri kullanılacak (projenin zaten yaygın deseni).
- (atdd.md'den taşındı, ÇÖZÜLDÜ) Input stili emsali — ChatScreen.tsx'in `.chat-input-textarea` deseni bulundu, yeni bir primitif/token gerekmiyor.
- Card'ın `style` prop kabul etmemesi (PlanCard/ResultCard görevinde TS2322 hatasına yol açmıştı) — `className` + inline `<style>` bloğu deseniyle baştan kaçınılacak, aynı hata tekrarlanmayacak.
- Label/input çiftlerinin dikey/yatay hizalanması (form layout) için hiçbir mevcut ekranda tam bir "form" deseni yok (ChatScreen'in textarea'sı tek alan) — plan bu yüzden basit bir `display: flex; flex-direction: column; gap` düzeni önerir (CAVEMAN: en basit çözüm), özel bir grid/form kütüphanesi kullanılmayacak.

## Open Questions
Yok — atdd.md'nin Unknowns'ı (input stil emsali) yukarıda gerçek kod keşfiyle çözüldü, claude-omni/Haiku dispatch'ine gerek kalmadı.

## Not
`SearchPanel.tsx` bir `.tsx` dosyası (rendered web UI) — `verify` adımında gate 12 (`vision-test`) N/A değil, önceki task'takiyle aynı gerekçeyle (PlanCard/ResultCard'a ulaşmak gibi SearchPanel'e ulaşmak da backend + oturum akışı gerektiriyor) muhtemelen yine N/A gerekçeli olacak — ama `verify` adımı kendi karar versin, burada varsayım yapılmıyor.
