---
task_slug: vite-vitest-guvenlik-guncellemesi
jira_id: null
saga_task_id: 278
priority: medium
coverage_target: null
performance_target: null
memory_target: null
test_strategy:
  unit: 0
  integration: 0
  e2e: 100
affected_modules:
  - package.json
  - package-lock.json
---

# ATDD — vite-vitest-guvenlik-guncellemesi

_Bu ATDD `saga-oto` skill'i tarafından otomatik cevaplarla oluşturuldu.
Bu bir bakım/bağımlılık güncelleme task'ı olduğu için kategoriler
mekanik doğası gereği kısa tutuldu — persona/user-story gibi bölümler
bir bağımlılık yükseltmesi için anlamlı içerik taşımıyor._

## Jira Kaynağı
Jira'ya bağlı değil. Saga task #278, epic #23. Saga #250'de bilinçli olarak ertelenmişti.

## Hedef (Neden)
`npm audit`, `esbuild<=0.24.2` (dev-server CORS açığı, moderate) üzerinden `vite`/`vitest` zincirinde 5 zafiyet (3 moderate, 1 high, 1 critical) raporluyor. Düzeltme `vite@8.2.1`'e (breaking change) geçiyor. Bu task, o yükseltmeyi yapıp TÜM test paketinin (unit+e2e+build) hâlâ yeşil kaldığını doğruluyor.

## Acceptance Criteria
1. [Critical] Given `npm audit fix --force` çalıştırılır, When `npm audit` tekrar çalıştırılır, Then bu 5 zafiyet (esbuild/vite/vitest/@vitest-mocker/vite-node zinciri) artık raporlanmaz.
2. [Critical] Given bağımlılıklar yükseltildi, When `npx vitest run` çalıştırılır, Then tüm mevcut unit testler (yükseltme öncesi 42) hâlâ geçer.
3. [Critical] Given bağımlılıklar yükseltildi, When `npx playwright test` çalıştırılır, Then tüm mevcut e2e testler (yükseltme öncesi 26) hâlâ geçer.
4. [Critical] Given bağımlılıklar yükseltildi, When `npm run build` çalıştırılır, Then build hatasız tamamlanır.
5. [High] Given yükseltme breaking change içerebilir (vite config API'si, vitest config API'si değişmiş olabilir), When testler/build kırmızıysa, Then yalnızca konfigürasyon/import uyumluluk düzeltmeleri yapılır — hiçbir uygulama davranışı (mevcut AC'ler, route'lar, component mantığı) değiştirilmez.

## Davranış Sözleşmesi
Bu bir bağımlılık güncelleme task'ı — geleneksel "girdi/çıktı" davranış sözleşmesi tablosu anlamlı değil. Tek "davranış": yükseltme sonrası mevcut tüm testlerin (unit+e2e) ve build'in hâlâ yeşil kalması. Kırmızı kalan bir test varsa, düzeltme SADECE konfigürasyon/import seviyesinde yapılır — bir testin veya uygulama davranışının kasıtlı olarak değiştirilmesi bu task'ın kapsamı dışıdır (böyle bir ihtiyaç ortaya çıkarsa red-team'e/kullanıcıya rapor edilir, sessizce yapılmaz).

## Test Strategy
Bu task yeni bir test YAZMIYOR — mevcut tüm test paketinin (unit %100 zaten var olan 42 test + e2e zaten var olan 26 test) yükseltme sonrası hâlâ geçtiğini doğruluyor. `test_strategy` alanı bu nedenle "e2e: 100" olarak işaretlendi (yeni testin tamamı zaten var olan regresyon testleri).

## Benchmark / Başarı Ölçütü
`npm audit` → 0 zafiyet (esbuild/vite/vitest zincirinde). Mevcut 42 unit + 26 e2e test + build, yükseltme sonrası da yeşil.

## Kapsam Dışı
- Uygulama kodunda (backend/ui/src) davranış değişikliği — sadece bağımlılık sürümleri ve gerekiyorsa config dosyaları (`vite.config.ts`, `vitest` config'i eğer ayrıysa) değişir.
- `npm audit`'in henüz raporlamadığı başka bağımlılıkların yükseltilmesi.
- `@tauri-apps/*` paketlerinin yükseltilmesi (ayrı bir kaygı, bu task'ın kapsamı dışı).

## Etkilenen Dosyalar/Modüller (bilinen)
- `package.json`, `package-lock.json` (versiyon değişiklikleri)
- `vite.config.ts` (yükseltme breaking change içeriyorsa, config API uyumluluğu için değişebilir)
- Playwright config (`playwright.config.ts`) — vite ile ilişkiliyse kontrol edilecek

## Rollback Beklentisi
`git revert` yeterli — `package-lock.json` önceki haline döner, `npm install` ile eski sürümlere dönülür.

## Risks
- `vite@8.2.1`, mevcut `vite@5.4.x`'ten 3 major sürüm ileride — config API'sinde, plugin uyumluluğunda (`@vitejs/plugin-react`) veya Node.js sürüm gereksinimlerinde breaking change'ler olabilir. Bu risk atdd.md'nin kendi amacı (yükseltmeyi deneyip ne kırıldığını görmek).
- `vitest`'in de büyük bir sürüm atlaması gerekebilir (mevcut `vitest@2.1.9`) — `@testing-library/react`, `jsdom` gibi ilişkili paketlerle uyumluluk sorunu çıkabilir.

## Assumptions
- `npm audit fix --force`'un önerdiği spesifik sürümlere güvenilecek (npm'in kendi bağımlılık çözümleyicisi) — elle belirli bir sürüm pinlenmeyecek, npm'in önerdiği en uyumlu setle ilerlenecek (saga-oto tarafından otomatik seçildi).

## Unknowns
- Yükseltme sonrası hangi spesifik config/import değişikliklerinin gerekeceği — implementasyon sırasında ortaya çıkacak.

## Sorular ve Cevaplar (ham kayıt)
1. Yükseltme stratejisi ne olmalı? → `npm audit fix --force`'un önerdiği sürümler kullanılsın (saga-oto tarafından otomatik seçildi, npm'in kendi resolver'ına güvenmek en düşük riskli yol)
2. Test/build kırılırsa ne yapılmalı? → Sadece config/import düzeltmesi yapılsın, davranış değiştirilmesin (saga-oto tarafından otomatik seçildi)
3. Task-slug 'vite-vitest-guvenlik-guncellemesi' uygun mu? → Evet (saga-oto tarafından otomatik seçildi)
