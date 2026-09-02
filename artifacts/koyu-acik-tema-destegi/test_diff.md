# Test Diff — koyu-acik-tema-destegi
_Red step — implementasyon henüz yok, aşağıdaki testler BAŞARISIZ olması beklenir._

## Dosyalar
| Dosya | İşlem | Test Sayısı |
|---|---|---|
| `ui/src/tokens.test.ts` | Güncellendi (CSS var kontratına göre) | 8 test (colors grubu + değişmeyenler) |
| `ui/src/lib/theme.test.ts` | Yeni | 15 test (`applyStoredTheme`, `toggleTheme`, `getTheme`, entegrasyon) |
| `ui/src/App.test.tsx` | Genişletildi (mevcut testler dokunulmadı) | +2 test (toggle butonu her iki ekranda) |

## AC / Davranış Sözleşmesi Eşlemesi
| AC / Satır | Test |
|---|---|
| AC-1, Satır 1 (ilk yükleme, boş localStorage) | `applyStoredTheme() does not set data-theme when localStorage is empty` |
| AC-2, Satır 2-3 (toggle) | `toggleTheme() toggles from dark to light...`, `toggleTheme() toggles from light to dark...` |
| AC-3, Satır 4 (kayıtlı tercih, mount) | `applyStoredTheme() applies "light" theme from localStorage`, `persists the toggle choice across browser reload...` |
| AC-4, Satır 5-6 (bozuk/erişilemez localStorage) | `does not set data-theme when localStorage has an invalid value...`, `silently defaults to dark theme when localStorage.getItem raises an error`, `correctly handles localStorage error during toggleTheme` |
| AC-5, Satır 7 (7 bileşenin testleri etkilenmez) | `tokens.test.ts` güncellemesi (kasıtlı kontrat değişikliği) — 7 bileşenin KENDİ test dosyaları hiç değiştirilmedi |
| AC-6 (theme.css tam CSS var seti) | Implementasyon aşamasında `code_diff.md`'de doğrulanacak (bu, dosya-varlığı/içerik kontrolü — JS testiyle doğrudan test edilmiyor) |
| AC-7 (toggle butonu erişilebilir) | `App.test.tsx`: toggle butonu render testleri |

## Varsayımlar
- 7 bileşenin (Button/Card/ChatScreen/PlanCard/ResultCard/SearchPanel/TransactionHistoryPanel) testleri `tokens.colors.X`'i dinamik referans aldığı için DEĞİŞTİRİLMEDİ — plan.md'nin teorik varsayımı, `verify` adımında gerçek `vitest run` ile kanıtlanacak.
- `theme.css`'in içerik doğruluğu (iki tema bloğu, tüm renk anahtarları) otomatik JS testiyle değil, code_diff.md incelemesiyle doğrulanacak.

## Sıradaki adım
`code-copilot` — `tokens.ts`, `lib/theme.ts`, `theme.css`, `main.tsx`, `App.tsx` implementasyonunu yazacak.
