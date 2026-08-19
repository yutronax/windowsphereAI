# Verify Report — scan-fuzzy-name-pattern-forward
_Reference: atdd.md, plan.md, code_diff.md, test_diff.md_

## Verification Gates
| # | Gate | Result | Evidence / Reason |
|---|------|--------|--------------------|
| 1 | Dosya konumu | PASS | `git status --short` — `backend/main.py`, `backend/tests/test_search_scan.py` değişti |
| 2 | Build/derleme | PASS | `.venv/Scripts/python.exe -c "import backend.main"` → OK |
| 3 | Supabase şema/canlı doğrulama | N/A | Bu görev Supabase'e dokunmuyor |
| 4 | Lint | N/A | Repoda yapılandırılmış linter yok |
| 5 | Type check | N/A | Yapılandırılmış type checker yok |
| 6 | Unit testler | PASS | `.venv/Scripts/python.exe -m pytest backend/tests/ -v` (PROJE GENELİ) → **371 passed, 4 skipped, 0 failed** — regresyon yok |
| 7 | E2E testler | N/A | Projede e2e altyapısı yok |
| 8 | Lighthouse | N/A | Backend-only |
| 9 | Erişilebilirlik | N/A | Backend-only |
| 10 | Güvenlik taraması | **PASS (tam)** | `security-scan`, scope=`backend/main.py`: secrets PASS, python_sast PASS, python_deps PASS (bir önceki task'ta pypdf/pillow güncellendiği için artık tam PASS) — genel verdict PASS |
| 11 | AI code review | PENDING (red-team) | Ayrı adımda yapılacak |
| 12 | Görsel regresyon | N/A | Backend-only |
| 13 | İnsan onayı | PENDING | Kullanıcı onayı bekleniyor |

## AC -> Test Mapping
1. [Critical] fuzzyName scan sonrası doğru filtrelenir -> AC-1 testi (yanlış-pozitif riski test-copilot turunda giderildi) -> PASS
2. [Critical] namePattern scan sonrası doğru filtrelenir -> AC-2 testi -> PASS
3. [High] Geçersiz regex → 422 (scan hiç başlamaz) -> AC-3 testi -> PASS
4. [High] İki mod birlikte → 422 -> AC-4 testi -> PASS

## Coverage / Quality Notes
- Bu task sıfır yeni davranış icat etmedi — mevcut, zaten test edilmiş senkron davranışı asenkron akışa taşıdı (`_validate_fuzzy_regex_or_422` ortak yardımcı ile kod tekrarı da önlendi).
- Test-copilot turunda önemli bir kalite notu: AC-1/AC-2 testleri ilk yazımda yanlış-pozitif veriyordu (filtre hiç uygulanmasa da "beklenen dosya var mı" testi geçiyordu) — filtrelenmemesi gereken bir dosyanın YOKLUĞUNU da doğrulayacak şekilde güçlendirildi, gerçek red step nedenini yakaladı.
