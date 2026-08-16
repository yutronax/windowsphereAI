# Verify Report — onboarding-istek-placeholder
_Reference: atdd.md, plan.md, code_diff.md, test_diff.md_

> **Not:** Codex CLI kotası 15 Eylül 2026'ya kadar dolu (`ERROR: You've hit
> your usage limit`). Bu, gate 12'nin normal yolu olan `vision-test`
> skill'inin de Codex'e bağlı olması nedeniyle çalışmamasına yol açtı —
> onun yerine Claude Browser MCP ile doğrudan ekran görüntüsü alınıp
> Claude tarafından görsel olarak incelendi (aşağıda gate 12'de detay).

## Verification Gates
| # | Gate | Result | Evidence / Reason |
|---|------|--------|--------------------|
| 1 | Dosya konumu | PASS | `git status --short` ile 3 değişen dosya doğrulandı: `ui/src/components/onboarding/OnboardingScreen.tsx`, `OnboardingScreen.test.tsx`, `ui/e2e/onboarding.spec.ts` (bkz. aşağıdaki komut çıktısı). |
| 2 | Build/derleme | PASS | `npm run build` (= `tsc --noEmit && vite build`, package.json'daki gerçek script): temiz, 0 hata, `dist/` üretildi. |
| 3 | Supabase şema/canlı doğrulama | N/A | Bu task hiçbir Supabase tablosuna/migration'a/`{supabase_url}/rest/v1/...` çağrısına dokunmuyor — `code_diff.md` sadece bir React component'inde placeholder attribute + CSS kuralı. |
| 4 | Lint/Format | N/A | Projede `.eslintrc*`/`.prettierrc*` yok, `package.json`'da `lint`/`format` script'i tanımlı değil — proje linter/formatter tanımlamıyor. |
| 5 | Type check | PASS | `tsc --noEmit -p tsconfig.json`: 0 hata (gate 2'nin build komutunun bir parçası olarak da doğrulandı). |
| 6 | Unit testler | PASS | `npx vitest run`: **18/18 geçti** (15 mevcut + 3 yeni). Kırmızı→yeşil sırası doğrulandı: implementasyondan önce 3 yeni test fail ediyordu (`expected '' to be 'Bu klasördeki PDF'leri tarihe göre sırala'`), implementasyon sonrası hepsi geçti. |
| 7 | E2E testler | PASS | `npx playwright test onboarding.spec.ts`: **14/14 geçti** (11 mevcut + 3 yeni), regresyon yok. |
| 8 | Lighthouse (performans) | N/A | Projede/ortamda `lighthouse` MCP sunucusu yapılandırılmamış. |
| 9 | Erişilebilirlik | N/A | Gate 8 ile aynı koşul — Lighthouse erişilebilirlik kategorisi çalıştırılamadı. Manuel not: değişiklik `aria-label`'a dokunmadı, `placeholder` erişilebilirlik ismini değiştirmez (WCAG placeholder-as-label anti-pattern'i bu task'ta zaten yok — aria-label ayrı ve kalıcı). |
| 10 | Güvenlik taraması | **FAIL (bu task'tan bağımsız, önceden var)** | `security-scan` skill çalıştırıldı, scope: 3 değişen dosya. `secrets`: PASS (0 bulgu). `node_deps`: **FAIL** — `npm audit`, devDependency zincirinde (`vite`→`esbuild`, `vitest`→`@vitest/mocker`) 5 açık buldu (3 moderate, 1 high, 1 critical — esbuild dev-server CORS açığı, GHSA-67mh-4wv8-2f99). Bu, projenin `package.json`'ındaki mevcut sürüm pinlerinden kaynaklanıyor — bu task hiçbir bağımlılık eklemedi/değiştirmedi, ve `npm audit --omit=dev` (üretim bağımlılıkları) **0 açık** raporluyor. Yani üretime giden kod etkilenmiyor, sorun geliştirme sunucusu (`vite dev`) ile sınırlı. **Bu task'ı bloklamıyorum ama ayrı bir task olarak flag'liyorum** (aşağıda). |
| 11 | AI code review | PENDING (red-team) | Sonraki adımda çalışacak. |
| 12 | Görsel regresyon | PASS | Codex vision (`vision-test`) kotası dolu olduğu için, dev server (`http://127.0.0.1:4173`) Claude Browser MCP ile açılıp ekran görüntüsü doğrudan Claude tarafından incelendi: placeholder metni ("Bu klasördeki PDF'leri tarihe göre sırala") görünür, gerçek yazılan metinden belirgin şekilde daha soluk/gri, textarea/buton layout'u bozulmamış. `read_page` ile de `placeholder="Bu klasördeki PDF'leri tarihe göre sırala"` attribute'u DOM'da doğrulandı. |
| 13 | İnsan onayı | PENDING | Kullanıcının (Yusuf) nihai görsel/işlevsel onayı bekleniyor. |

## AC -> Test Mapping
1. [Critical] Placeholder metni + düşük kontrast rengi (`#9CA3AF`) → `shows the guiding placeholder text with a muted #9CA3AF color when empty (AC-1)` (unit) + `shows the guiding placeholder text with a muted color on the empty request textarea (AC-1)` (e2e, `::placeholder` rengi `rgb(156, 163, 175)` olarak doğrulandı) → PASS
2. [Critical] Yazınca placeholder kaybolur → `keeps the placeholder attribute intact while the user types (AC-2)` (unit) + `hides the placeholder once the user starts typing (AC-2)` (e2e) → PASS
3. [High] Silince placeholder tekrar görünür → `clears the typed value back to empty so the placeholder is visible again (AC-3)` (unit) + `shows the placeholder again after the typed text is fully cleared (AC-3)` (e2e) → PASS
4. [Medium] Focus/blur davranışı bozulmaz (regresyon) → mevcut `shows a focus border and box-shadow...` + `reverts the request textarea border to #E5E7EB on blur` testleri → PASS (placeholder eklendikten sonra tekrar çalıştırıldı, hâlâ geçiyor)

## Coverage / Quality Notes
- Behavior-contract tablosundaki tüm satırlar (1-4) test edildi; #253 gibi
  bu task da saf görsel olduğu için diğer satırlar (hata/kaynak yok/vb.)
  atdd.md'de zaten N/A olarak işaretliydi.
- Test piramidi atdd.md'nin hedeflediği 20/15/65 (unit/integration/e2e)
  oranına yakın: 3 unit + 3 e2e eklendi, ayrı bir integration-seviyesi test
  yazılmadı çünkü `getComputedStyle` tabanlı stil doğrulaması zaten mevcut
  unit testlerin (AC-1 border/min-height testi) kapsamına giriyor ve
  `::placeholder` rengi jsdom'da güvenilir okunamadığı için (plan.md'de not
  edildi) bu doğrulama bilinçli olarak e2e katmanına bırakıldı.
- **Ayrı flag (bu task'ın kapsamı dışı):** `npm audit` bulguları (vite/
  vitest devDependency zincirindeki esbuild açığı) projenin genelinde var,
  bu task'la ilgisiz. Bağımsız bir Saga task olarak önerilir: "vite/vitest
  sürümlerini güncelle (esbuild CORS açığı GHSA-67mh-4wv8-2f99)".
