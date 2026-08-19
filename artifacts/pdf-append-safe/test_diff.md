# Test Diff — pdf-append-safe (RED step)

_Reference: atdd.md, plan.md_

## Değiştirilmeyen dosyalar
`backend/models.py`, `backend/orchestrator.py`, `backend/plan_generation.py`, `requirements.txt` —
hiçbiri değiştirilmedi (implementasyon bu adımın kapsamı DIŞINDA).

## Eklenen dosya
Yok — sadece `backend/tests/test_orchestrator.py`'ye ekleme yapıldı.

## Eklenen testler (`backend/tests/test_orchestrator.py`, satır ~2163'ten itibaren)

Yardımcılar:
- `_append_step(order, file_name, append_text)` — `OperationType.APPEND` ve
  `appendText` alanını kullanan bir `PlanStep` üretir (henüz var olmayan API).

| Test | AC | Ne doğruluyor |
|---|---|---|
| `test_apply_plan_appends_a_new_page_with_the_given_text_and_commits` | AC-1 [Critical] | Geçerli/okunabilir kaynak PDF + `appendText` ile `apply_plan()` sonrası sonuç dosyasında orijinal sayfa sayısı + 1 sayfa var, `transaction.status == "committed"`. |
| `test_apply_plan_rejects_append_to_a_corrupt_source_and_leaves_it_untouched` | AC-2 [Critical] | Bozuk "PDF" (`b"not a real pdf"`) ile APPEND → `PlanApplicationError`, mesaj "bozuk"/"okunamıyor" ipucu içeriyor, kaynak dosyanın byte içeriği işlem öncesi/sonrası AYNI (en kritik assertion). |
| `test_apply_plan_rejects_append_to_a_missing_source_with_a_distinct_message` | AC-3 [Critical] | Var olmayan kaynak path ile APPEND → "bulunamadı" içeren, AC-2'nin mesajından FARKLI bir `PlanApplicationError` mesajı. İki mesaj birbirinden farklı olduğu doğrudan `assert missing_message != corrupt_message` ile karşılaştırılıyor. |
| `test_apply_plan_rejects_append_to_a_permission_denied_source` | AC-4 [High] | Salt-okunur (`os.chmod(path, 0o000)`) kaynakla APPEND denemesi → `PlanApplicationError`, dosya değişmemiş. `test_file_search.py`'deki mevcut desenle AYNI şekilde `@pytest.mark.skipif(os.name == "nt", ...)` ile Unix-only işaretlendi (Windows NTFS'te `chmod(0o000)` sahibi engellemiyor). |
| `test_append_text_empty_or_whitespace_only_is_rejected_by_pydantic` | AC-5 [Medium/High] | `appendText=""` ve `appendText="   "` ile `PlanStep` oluşturmak `pydantic.ValidationError` fırlatır — `apply_plan`'a hiç ulaşmadan, model seviyesinde. |
| `test_apply_plan_rejects_append_of_a_path_outside_allowed_root` | AC-6 [Medium] | Whitelist dışı hedef (`".."`) ile APPEND planı → `PathWhitelistError` — mevcut `test_apply_plan_rejects_redact_of_a_path_outside_allowed_root` testinin AYNISI, APPEND için tekrarlanmış. |

Diğer değişiklik: dosyanın import bloğuna `import os` ve `from pydantic import ValidationError` eklendi (daha önce dosyada yoktu, AC-4/AC-5 testleri için gerekli).

## Pytest sonucu

Komut: `.venv/Scripts/python.exe -m pytest backend/tests/test_orchestrator.py -v -k "append or Append"`

```
5 failed, 1 skipped, 81 deselected in 2.38s
```

- 5 test **AttributeError: APPEND** ile kırmızı — `backend.models.OperationType`'ta
  henüz `APPEND` üyesi yok (beklenen red-step göstergesi, import/collection
  hatası DEĞİL — pytest testleri sorunsuz topladı, hepsi çalışma zamanında
  `_append_step()` içinde `OperationType.APPEND`'e erişirken patladı).
- 1 test (`test_apply_plan_rejects_append_to_a_permission_denied_source`, AC-4)
  Windows'ta `skipif(os.name == "nt", ...)` ile atlandı — bu, ortamın
  beklenen (Unix-only) davranışı, test dosyasındaki mevcut desenle tutarlı.
- Import/collection seviyesinde hiçbir hata yok — tüm 6 test doğru şekilde
  toplandı ve çalıştı (biri skip, beşi assertion-öncesi AttributeError ile
  kırmızı).

## Son düzeltme — kalıntı satır temizliği (2026-08-19)

`test_apply_plan_rejects_append_of_a_path_outside_allowed_root` (AC-6,
satır ~2288) fonksiyonunun sonunda, `purge_oversized_delete_backups`
testlerinden yanlışlıkla kopyalanmış `assert len(purged_ids) == 1` satırı
vardı — `purged_ids` bu fonksiyonda tanımlı olmadığından `NameError`
veriyordu. Satır kaldırıldı; fonksiyonun asıl mantığı (whitelist ihlalinde
`PathWhitelistError` bekleniyor) değiştirilmedi.

Proje genelinde `purged_ids` için grep yapıldı: sadece `backend/orchestrator.py`
(gerçek implementasyon) ve `backend/tests/test_orchestrator.py`'deki ilgili
`purge_oversized_delete_backups` testlerinde geçiyor — başka kalıntı yok,
temizlik görevi gerekmedi.

Düzeltme sonrası tam paket:

Komut: `.venv/Scripts/python.exe -m pytest backend/tests/ -v`

```
376 passed, 5 skipped, 9 warnings in 40.97s
```

Tüm testler yeşil (5 skip Windows-only/ortam bağımlı testler, beklenen).

## Kapsanmayan / bilinmeyen noktalar (open_questions)
- `PlanApplicationError` mesajlarının TAM metni implementasyon aşamasında
  netleşecek; testler sadece "bozuk"/"okunamıyor" veya "bulunamadı" alt
  string'lerinin varlığını ve iki mesajın birbirinden FARKLI olmasını
  kontrol ediyor (plan.md'nin "AYRI except blokları, AYRI mesajlar"
  kararıyla tutarlı, ama code-copilot mesaj metnini serbestçe seçebilir).
- AC-4'ün Windows karşılığı (salt-okunur/kilitli dosya davranışı) bu red
  adımında TEST EDİLMEDİ (skip) — CI/geliştirme ortamı Windows olduğu için
  bu senaryo fiilen kapsanmıyor; bu, atdd.md'nin kendisinin de öngördüğü bir
  sınırlama (mevcut `test_file_search.py` deseniyle tutarlı bilinçli kapsam
  dışı bırakma).
