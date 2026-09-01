# Verify Report — buton-kart-primitifleri
_Reference: atdd.md, plan.md, test_diff.md, code_diff.md_

## Verification Gates
| # | Gate | Result | Evidence / Reason |
|---|------|--------|--------------------|
| 1 | Dosya konumu | PASS | `git status --short ui/src/components/primitives` → `?? ui/src/components/primitives/` (Button.tsx, Card.tsx, index.ts, Button.test.tsx, Card.test.tsx gerçek proje konumunda) |
| 2 | Build/derleme | PASS | `npm run build` (`tsc --noEmit && vite build`) → sıfır hata, `dist/index.html` + `dist/assets/index-BvAZKmVx.js` (177.72 kB) üretildi, `built in 287ms` |
| 3 | Supabase şema/canlı doğrulama | N/A | Bu task'ın `code_diff.md`'si sıfır Supabase çağrısı ve sıfır migration dosyası içeriyor — statik React bileşenleri, DB'ye dokunmuyor |
| 4 | Lint | N/A | Repo'da yapılandırılmış bir ESLint/Prettier config'i yok (`.eslintrc*`, `eslint.config.*`, `.prettierrc*` yok, `package.json`'da lint/format script'i yok) |
| 5 | Type check | PASS | `tsc --noEmit` gate 2'nin (`npm run build`) parçası olarak çalıştı — sıfır hata |
| 6 | Unit testler | PASS | `npx vitest run` → **238/238 test PASS**, 14/14 test dosyası yeşil (yeni `Button.test.tsx` 8/8, `Card.test.tsx` 8/8 dahil, mevcut 6 ekranın testlerinde regresyon yok) |
| 7 | E2E testler | N/A | Primitifler bu task kapsamında hiçbir ekrana bağlanmadı (atdd.md "Kapsam Dışı" — ekranların taşınması ayrı task'larda) — gerçek uygulamada henüz render edilen bir kullanıcı akışı yok, sürülecek bir sayfa yok |
| 8 | Lighthouse (performans) | N/A | Aynı gerekçe — primitifler hiçbir sayfada render edilmiyor, ölçülecek canlı bir sayfa yok |
| 9 | Erişilebilirlik | N/A | Aynı gerekçe (gate 8 ile birlikte N/A) |
| 10 | Güvenlik taraması | PASS | `security-scan` runner, scope: `Button.tsx`, `Card.tsx`, `index.ts` → exit 0, verdict `PASS` (secrets: PASS/boş, python_sast: N/A, python_deps: PASS, node_deps: PASS) |
| 11 | AI code review | PENDING (red-team) | Bu skill'in kapsamı dışında — ayrı `red-team` adımında yapılacak |
| 12 | Görsel regresyon | N/A | atdd.md "Benchmark" bölümü açıkça belirtiyor: "Görsel/UI kriteri: Uygulanmaz — bu task hiçbir ekranı görsel olarak değiştirmiyor" — primitifler hiçbir ekrana bağlı değil, karşılaştırılacak bir ekran görüntüsü yok |
| 13 | DAST (ZAP) | N/A | `threat-model` bu task için hiçbir `AC-S<n>` güvenlik kriteri üretmedi (threat-model adımı bu pipeline'da çalıştırılmadı — task auth/PII/ödeme/multi-tenant sınırı içermiyor), ayrıca render edilen bir web UI de yok |
| 14 | İnsan onayı | PENDING | Kullanıcının açık onayı bekleniyor |

## AC -> Test Mapping
1. AC-1 (Button variant/disabled + tokens) → `Button.test.tsx`: 8 test (primary/danger/default variant, disabled #94A3B8, height/radius/padding/fontSize token, enabled-by-default, danger+disabled, children text) → **PASS**
2. AC-2 (Card panelBackground/border/radius + children) → `Card.test.tsx`: 8 test (panelBackground/border/radius birlikte, children, panelBackground tekil, border tekil, radius tekil, multiple children, empty Card, tüm tokenlar birlikte) → **PASS**
3. AC-3 (RTL render testleri her variant/prop için) → Yukarıdaki 16 testin tamamı → **PASS**
4. AC-4 (TS derleme zamanı — geçersiz variant) → Runtime test yazılamaz (doğası gereği), `tsc --noEmit` (gate 2/5) ile doğrulandı → **PASS**
5. AC-5 (mevcut ekranlarda regresyon yok) → Tam test suite 238/238, 6 mevcut ekranın (Onboarding/ChatScreen/PlanCard/ResultCard/TransactionHistoryPanel/SearchPanel) tüm testleri yeşil → **PASS**
6. AC-6 (`index.ts` named export) → `index.ts` var, `Button`/`Card` named export ediyor; testler `./Button`/`./Card`'dan import ediyor (index.ts'in kendisi için ayrı bir smoke test yok, ama `tsc --noEmit` ve build'in başarılı geçmesi export sözdiziminin geçerli olduğunu doğruluyor) → **PASS**

## Coverage / Quality Notes
- Davranış Sözleşmesi tablosundaki her satır testlerde karşılığını buldu;
  "kısmi başarı" (#7) ve "hiçbir şey yapılamadı ama hata yok" (#8) satırları
  atdd.md'de zaten "bu task'ta imkansız" olarak gerekçelendirilmiş ve
  test-copilot bunu doğru şekilde yorum olarak işlemiş.
- Test piramidi: atdd.md'nin planladığı %80 unit / %20 integration yerine
  fiilen tüm 16 test RTL render testi (unit-ağırlıklı) oldu — token
  değerlerinin doğru okunduğunu doğrulayan testler (`applies panelBackground
  token value...` gibi) zaten hem unit hem entegrasyon sınırında sayılabilir
  (component + tokens.ts birlikte test ediliyor), bu yüzden fiili oran
  planla tutarlı kabul edilebilir. Ayrı bir kusur değil.
- Bilinen tarihsel not: `Button.test.tsx`'teki `color: 'white'` satırı bu
  projedeki jest-dom sürümünün CSS keyword normalizasyonu yapmaması
  nedeniyle başarısız oluyordu; test-copilot'a geri dönülüp
  `color: 'rgb(255, 255, 255)'` olarak düzeltildi (bkz. test_diff.md).
  Şu anda tüm testler yeşil.
- `index.ts` için ayrı bir "index'ten import edilebilirlik" testi yok —
  AC-6'yı doğrudan hedefleyen bir RTL testi eksik (sadece `tsc`/build
  dolaylı kanıt sağlıyor). Düşük risk (3 satırlık re-export dosyası,
  sözdizimi hatası derleme zamanında zaten yakalanır) — bir eksiklik olarak
  not ediliyor, blocking değil.
