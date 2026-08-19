# Verify Report — word-tablo-basligi
_Reference: atdd.md, plan.md, test_diff.md, code_diff.md_

## Verification Gates
| # | Gate | Result | Evidence / Reason |
|---|------|--------|--------------------|
| 1 | Dosya konumu | PASS | `git status --short`: `M models.py/orchestrator.py/requirements.txt/test_orchestrator.py`, `?? word_table.py/test_word_table.py/artifacts/` — code_diff.md ile birebir eşleşiyor |
| 2 | Build/derleme | PASS | `.venv/Scripts/python -c "import backend.word_table, backend.models, backend.orchestrator"` → "import OK" |
| 3 | Supabase şema/canlı doğrulama | N/A | Değişen dosyalarda Supabase çağrısı/migration yok |
| 4 | Lint | N/A | Proje backend için ruff/eslint tanımlamıyor (önceki görevlerle aynı gerekçe) |
| 5 | Type check | N/A | Proje backend için pyright/mypy tanımlamıyor |
| 6 | Unit testler | PASS | Bağımsız yeniden çalıştırıldı (`.venv`): `pytest backend/tests -q` → **463 passed, 5 skipped, 0 failed**, 29.67s. Hedefli alt küme → 11 passed |
| 7 | E2E testler | N/A | Bu görevde e2e altyapısı yok |
| 8 | Lighthouse (performans) | N/A | Rendered web UI dokunulmadı |
| 9 | Erişilebilirlik | N/A | Aynı gerekçe (gate 8) |
| 10 | Güvenlik taraması | PASS | `security-scan` runner, 6 değişen dosya kapsamında (yeni `python-docx` bağımlılığı dahil `requirements.txt` taranarak): `secrets: PASS`, `python_sast: PASS`, `python_deps: PASS` (pip-audit yeni bağımlılıkta bilinen açık bulmadı), `node_deps: PASS`, verdict `PASS` |
| 11 | AI code review | PENDING (red-team) | Test VE kod subagent'lar tarafından yazıldı; AYRICA bir ortam tutarsızlığı (python-docx yanlış Python kurulumuna kurulmuştu) tespit edilip düzeltildi — red-team bu düzeltmenin GERÇEKTEN `.venv`'i hedeflediğini teyit etmeli |
| 12 | Görsel regresyon | N/A | Rendered web UI dokunulmadı |
| 13 | İnsan onayı | PENDING | Kullanıcı henüz onaylamadı |

## AC -> Test Mapping
1. [Critical] AC-1 (başlıklı happy path) -> unit + orchestrator happy-path (başlıklı) testi -> PASS
2. [Critical] AC-2 (başlıksız happy path) -> unit + orchestrator happy-path (başlıksız) testi -> PASS
3. [High] AC-3 (sütun uyuşmazlığı) -> unit + orchestrator `PlanApplicationError` testi -> PASS
4. [High] AC-4 (kaynak yok/bozuk) -> unit (2 senaryo) + orchestrator `PlanApplicationError` testi -> PASS

## Coverage / Quality Notes
- Tüm Acceptance Criteria en az bir unit + bir entegrasyon testiyle kaplı.
- **Ortam tutarsızlığı bulunup düzeltildi:** test-yazım subagent'ı
  `python-docx`'i yanlışlıkla global bir Python kurulumuna eklemişti,
  proje `.venv`'i DEĞİL — bu, "testler geçti" iddiasının aslında yanlış
  ortamda doğrulanmış olması riskini taşıyordu. Fark edilip `.venv`'e de
  kurulum yapıldı, kırmızı VE yeşil durumların ikisi de `.venv` ile
  bağımsız olarak yeniden doğrulandı. Bu, subagent özetlerine körü
  körüne güvenmemenin somut bir örneği.
- python-docx API'si (implementasyon subagent'ı tarafından) gerçek
  kurulumla doğrulandı, plan.md'nin önerisi doğru çıktı.
- Bu görevde test VE kod iki ayrı subagent tarafından yazıldı — gate 11
  (red-team) özellikle önemli.
