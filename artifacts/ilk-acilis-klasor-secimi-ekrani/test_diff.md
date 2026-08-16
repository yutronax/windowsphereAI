# Test Diff — ilk-acilis-klasor-secimi-ekrani
_Codex (gpt-5.6-terra) tarafından yazıldı, henüz implementasyon yok (RED adımı)._

## Oluşturulan Test Dosyaları

| Dosya | Hedef AC | Kapsam |
|---|---|---|
| `ui/src/components/onboarding/OnboardingScreen.test.tsx` | AC-1, AC-2, AC-3, AC-4 | Happy path render (<500ms), native dialog seçimi, Cancel senaryosu, backend starting/timeout durumları, `truncateWindowsPath` yardımcı fonksiyonu (unit) |
| `ui/src/lib/backendHealth.test.ts` | AC-4 | `waitForBackendHealth` polling mantığı: anında hazır, gecikmeli hazır, 10sn timeout sınırı (fake timers ile tam sınırda test) |
| `ui/e2e/onboarding.spec.ts` | AC-1..AC-5 | Playwright ile uçtan uca: render süresi, native dialog mock'u (Tauri `__TAURI__` köprüsü), Cancel, backend timeout+retry, config varken atlama |
| `backend/tests/test_config.py` | AC-5 | `%APPDATA%/windows-ai-files/config.json` ilk-kurulum tespiti: config yok→first-run, kaydetme→setup tamam, mevcut config→setup tamam |

## Davranış Sözleşmesi Tablosu Karşılığı
| # | Durum | Test |
|---|---|---|
| 1 | Happy path | `OnboardingScreen.test.tsx` satır 18-27, `onboarding.spec.ts` satır 9-17 |
| 2 | Cancel (sessiz başarı riski) | `OnboardingScreen.test.tsx` satır 40-49 — Devam düğmesinin disabled kaldığı açıkça assert ediliyor |
| 5 | Backend hazır değil | `OnboardingScreen.test.tsx` satır 51-57 |
| 6 | Backend timeout (10sn) | `backendHealth.test.ts` satır 34-48 (fake timer ile tam sınırda), `onboarding.spec.ts` satır 45-54 |
| — | AC-5 (config varsa atla) | `test_config.py` tüm dosya, `onboarding.spec.ts` satır 56-62 |

Kapsam dışı bırakılan satırlar (kaynak yok, yetkisiz erişim, kısmi başarı) için
test yazılmadı — atdd.md'de gerekçeleriyle işaretlendiği gibi.

## Beklenen Durum
Tüm testler şu an **kırmızı (fail)** — `ui/src/components/onboarding/OnboardingScreen.tsx`,
`ui/src/lib/backendHealth.ts`, `backend/config.py` henüz yazılmadı. Sonraki
adım `code-copilot`: bu testleri yeşile çevirecek implementasyonu yazmak.
