# Test Diff — buton-kart-primitifleri (red step)
_Reference: atdd.md, plan.md_

## Oluşturulan Dosyalar
- `ui/src/components/primitives/Button.test.tsx` (9 test)
- `ui/src/components/primitives/Card.test.tsx` (8 test)

Klasör (`ui/src/components/primitives/`) bu adımda oluşturuldu. `Button.tsx`,
`Card.tsx`, `index.ts` henüz yok — testler import hatasıyla FAIL vermesi
beklenen "red" durumda.

## AC ↔ Test Eşlemesi
| AC | Test dosyası | Test(ler) |
|---|---|---|
| AC-1 (Button variant/disabled + tokens) | Button.test.tsx | primary variant colors/dimensions, danger variant, default variant, disabled styling, height/radius/padding/fontSize tokens, enabled-by-default, danger+disabled kombinasyonu, children text |
| AC-2 (Card panelBackground/border/radius + children) | Card.test.tsx | panelBackground/border/radius, children render, panelBackground tekil, border tekil, radius tekil, multiple children, empty Card, tüm tokenlar birlikte |
| AC-3 (RTL render testleri her variant/prop için) | Button.test.tsx + Card.test.tsx | Yukarıdaki tüm testler |
| AC-4 (TS derleme zamanı — geçersiz variant) | Button.test.tsx | Runtime test yazılamaz — dosyada satır 97-100'de yorum olarak not düşüldü, `tsc --noEmit` ile `verify` adımında doğrulanacak |
| AC-5 (mevcut ekranlarda regresyon yok) | — | Bu task kapsamında yeni dosya, mevcut ekran testleri değişmedi; regresyon `verify` adımında mevcut test suite çalıştırılarak doğrulanacak |
| AC-6 (`index.ts` named export) | — | `index.ts` henüz yok (code-copilot yazacak); Button/Card testleri doğrudan `./Button`/`./Card`'dan import ediyor, `index.ts`'in doğruluğu code-copilot sonrası ayrı bir smoke test veya `verify`'de derleme kontrolüyle teyit edilecek |

## Davranış Sözleşmesi ↔ Test Kapsamı
| # | Durum | Kapsam |
|---|---|---|
| 1 | Happy path Button | ✓ (Button.test.tsx satır 8-21) |
| 1b | Happy path Card | ✓ (Card.test.tsx satır 8-22) |
| 2 | Geçersiz variant (TS hatası) | Runtime N/A — yorum + `tsc --noEmit` ile verify'da |
| 2b | variant verilmez → default primary | ✓ (Button.test.tsx satır 33-40) |
| 7 | Kısmi başarı (Button ✓ Card ✗) | Uygulanamaz — her iki dosya da bu adımda birlikte yazıldı |
| 8 | Hiçbir şey yapılamadı ama hata yok | Uygulanamaz — tsc/Vitest açıkça FAIL verir (code-copilot sonrası doğrulanacak) |

## Not
Disabled buton rengi (`#94A3B8`) testlerde sabit string olarak doğrulanıyor
(plan.md Kararlar bölümüne uygun — `tokens.ts` genişletilmedi).

## Güncelleme (code-copilot sonrası)
`code-copilot` implementasyonu yazdıktan sonra `Button.test.tsx`'teki
`color: 'white'` satırının jest-dom'un bu sürümünde jsdom'un computed
`rgb(255, 255, 255)` çıktısına normalize edilmediği tespit edildi
(implementasyon doğruydu, sadece bu tek assertion string-eşleşmesi
kırılgandı). test-copilot'a geri dönülüp satır `color: 'rgb(255, 255, 255)'`
olarak düzeltildi. Tam test suite: **238/238 PASS**.

## Sıradaki Adım
`verify` — gerçek test/build/lint gate'lerini çalıştıracak.
