# Verify Report — diff-tray-onizleme-ui
_Reference: atdd.md, code_diff.md, test_diff.md_

> Not: Bu task'ta testler VE implementasyon Codex kotası dolu olduğu için
> kullanıcı onayıyla Claude tarafından yazıldı — gate 11 (AI code review)
> için bağımsız `red-team` adımı NORMALDEN DE KRİTİK önemde.

## Verification Gates
| # | Gate | Result | Evidence / Reason |
|---|------|--------|--------------------|
| 1 | Dosya konumu | PASS | `git status --short backend/tests/test_main_integration.py ui/src/components/chat/ResultCard.test.tsx backend/models.py backend/main.py ui/src/components/chat/ResultCard.tsx artifacts/diff-tray-onizleme-ui/` — hepsi gerçek proje kökünde değişmiş/yeni görünüyor. |
| 2 | Build/derleme | PASS | Backend: `.venv/Scripts/python.exe -c "import backend.main; import backend.models"` → "OK import". Frontend: `npm run build` (proje script'i: `tsc --noEmit && vite build`) → temiz, 0 hata, `dist/` üretildi. |
| 3 | Supabase şema/canlı doğrulama | N/A | Bu proje Supabase kullanmıyor (SQLite + SQLAlchemy, `backend/db_models.py`) — kod tabanında `supabase` referansı yok. |
| 4 | Lint | N/A | Ne backend'de (`requirements-dev.txt`'te ruff/flake8 yok) ne frontend'de (`package.json` script'lerinde `lint` yok, `.eslintrc` yok) yapılandırılmış bir linter var — proje genelinde N/A, bu task'a özgü değil. |
| 5 | Type check | PASS (frontend) / N/A (backend) | Frontend: `tsc --noEmit` (build script'inin parçası, gate 2'de çalıştı) → 0 hata. Backend: `requirements-dev.txt`'te mypy/pyright yapılandırılmış değil (proje genelinde), N/A. |
| 6 | Unit testler | PASS | Backend: `.venv/Scripts/python.exe -m pytest backend/tests/test_main_integration.py -q` → **85 passed** (red-team sonrası üst-seviye `available`/`reason` assertion'ı eklendi, regresyon yok). Frontend: `npx vitest run ui/src/components/chat/ResultCard.test.tsx` → **26 passed** (red-team sonrası 3 yeni test: fetch hatası, transaction bulunamadı, üst-seviye unavailable). |
| 7 | E2E testler | N/A | Proje Playwright'a sahip (`test:e2e`) ama bu dar kapsamlı task için ayrı bir Playwright spec'i yazılmadı — atdd.md'nin test_strategy'sindeki "E2E %10" payı, RTL ile yazılan hover etkileşim testleriyle (component-seviyesinde) karşılandı, tam tarayıcı e2e'si kapsam dışı bırakıldı (dar kapsam kararı, plan.md). |
| 8 | Lighthouse (performans) | N/A | `lighthouse` MCP sunucusu bu ortamda yapılandırılmamış/mevcut değil. |
| 9 | Erişilebilirlik | N/A | Gate 8 ile aynı sebep — Lighthouse çalıştırılamadı. |
| 10 | Güvenlik taraması | PASS | `security-scan` skill'i değişen 3 dosyaya karşı çalıştırıldı (`backend/models.py`, `backend/main.py`, `ui/src/components/chat/ResultCard.tsx`) → verdict: **PASS** (secrets/python_sast/python_deps/node_deps hepsi PASS, 0 bulgu). |
| 11 | AI code review | DONE (red-team, approve) | `obss-red-team` subagent'ı bağımsız inceledi — 1 high (transaction-seviyesi `available` hiç set edilmiyordu, AC-4 gerçekte karşılanmıyordu) + 1 medium (preview fetch hatasında UI sessiz kalıyordu) bulgu buldu, ikisi de düzeltildi ve testlerle doğrulandı. Bkz. `red_team.json`. |
| 12 | Görsel regresyon | N/A | `vision-test` skill'i Codex CLI'ya (vision model) bağımlı — Codex kotası dolu, bu adım çalıştırılamadı. Kullanıcı isterse manuel gözden geçirebilir (dev server + hover). |
| 13 | İnsan onayı | PENDING | Kullanıcı onayı bekleniyor — bu skill/red-team onay VEREMEZ, sadece önerebilir. |

## AC -> Test Mapping
1. [Critical] İlk 10 dosya adı hover'da gösterilir → `test_transactions_endpoint_preview_lists_file_names_only_not_full_paths` (backend) + `fetches and shows the file name preview list on hover` (frontend) → PASS
2. [Critical] preview alanı GET /api/transactions'a eklendi, ayrı endpoint yok → aynı testler + `code_diff.md`'deki mimari karar → PASS
3. [High] Değişiklik yoksa "Değişiklik yok" → `test_transactions_endpoint_preview_is_empty_when_transaction_has_no_operations` + `shows a "no changes" message...` → PASS
4. [High] Purge edilmiş DELETE yedeği → "Önizleme mevcut değil" → `test_transactions_endpoint_preview_marks_delete_as_unavailable_when_backup_is_physically_purged` + `test_transactions_endpoint_preview_move_operation_is_never_marked_backup_purged` (negatif) + `shows an "unavailable" message...` → PASS
5. [Medium] 10'dan fazla dosyada "+N daha" → `test_transactions_endpoint_preview_truncates_after_ten_files_and_reports_total_count` + `shows a "+N daha" summary...` → PASS
6. [Medium] Hesaplanamayan dosya "?" ile işaretlenir, önizleme iptal edilmez → `test_transactions_endpoint_preview_marks_unreadable_file_as_unknown_without_failing_the_whole_preview` + `marks a file whose before/after state could not be computed...` → PASS

Tüm 6 Acceptance Criteria'nın en az bir backend + bir frontend testi var — hiçbiri kapsamsız değil.

## Coverage / Quality Notes
- Test piramidi: atdd.md hedefi Unit 60/Integration 30/E2E 10 idi; gerçekleşen dağılım backend tarafında entegrasyon-ağırlıklı (FastAPI TestClient + gerçek SQLite), frontend tarafında component-testi ağırlıklı — saf "unit" (örn. `_build_transaction_preview` fonksiyonunun izole test edilmesi) yazılmadı, sadece endpoint üzerinden dolaylı test edildi. Küçük bir sapma, düşük öncelikli bir task için kabul edilebilir ama not düşülüyor.
- `_build_transaction_preview` fonksiyonu `backend/main.py` içinde — proje genelinde bu tarz yardımcı fonksiyonlar genelde aynı dosyada kalıyor (mevcut `_transaction_to_summary` deseniyle tutarlı), ayrı bir modüle çıkarılmadı.
- Kod incelemesinde dikkat edilmesi gereken nokta: `ResultCard.tsx`'teki hover-tetiklemeli `fetch` çağrısı debounce/throttle içermiyor — hızlı ardışık hover/leave/hover döngüsünde `previewState !== 'idle'` kontrolü ikinci isteği engelliyor (test edildi), ama bu red-team'de ayrıca gözden geçirilebilir.
