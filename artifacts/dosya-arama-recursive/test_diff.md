# Test Diff — dosya-arama-recursive (RED STEP)

Referans: `artifacts/dosya-arama-recursive/atdd.md`, `artifacts/dosya-arama-recursive/plan.md`
Dosya: `backend/tests/test_file_search.py`
İmplementasyon: **YOK** — `backend/file_search.py` değiştirilmedi (sadece test dosyası).

## Güncellenen mevcut test (eski beklenti artık YANLIŞ)

- `TestSearchFilesContentContainsNonRecursive` → `TestSearchFilesContentContainsNowRecursive`
  - `test_subfolder_file_content_is_not_matched` → `test_subfolder_file_content_is_matched`
  - Eski beklenti: `nested.txt` sonuca GİRMEZ (non-recursive). Yeni beklenti (AC-4 ile
    tutarlı): `nested.txt` de girer. Şimdi KIRMIZI (implementasyon henüz recursive değil).

## Eklenen yeni testler (AC → sınıf/test eşlemesi)

| AC | Sınıf | Test | Durum |
|----|-------|------|-------|
| AC-1 [Critical] | `TestSearchFilesRecursiveDiscovery` | `test_file_two_levels_deep_is_found` | KIRMIZI |
| AC-1 [Critical] | `TestSearchFilesRecursiveDiscovery` | `test_file_two_levels_deep_is_found_with_name_filter` | KIRMIZI |
| AC-2 [Critical] | `TestSearchFilesDepthLimit` | `test_file_beyond_max_depth_is_excluded_without_error` | KIRMIZI |
| AC-3 [Critical] (a) | `TestSearchFilesCycleProtection` | `test_visited_path_tracking_prevents_infinite_loop_without_real_symlink` — plan.md'nin önerdiği gibi, GERÇEK symlink yerine `Path.resolve()` monkeypatch'lenerek sahte bir döngü (`A/loop_back` → `A`) üretilir; çekirdek "ziyaret edilen path seti" mantığı Windows'ta da doğrulanır | KIRMIZI |
| AC-3 [Critical] (b) | `TestSearchFilesCycleProtection` | `test_real_cyclic_symlink_completes_without_hanging` — gerçek `A/link → A` symlink'i, `pytest.mark.skipif(os.name == "nt", ...)` ile Windows'ta skip (mevcut dosyadaki desenle aynı) | KIRMIZI (Unix) / SKIP (Windows) |
| AC-4 [High] | `TestSearchFilesContentContainsRecursive` | `test_content_search_finds_match_in_nested_folder` | KIRMIZI |
| AC-5 [High] | `TestSearchFilesRecursiveTimeout` | `test_recursive_search_times_out_and_returns_partial_flag` — mevcut #314 timeout monkeypatch deseniyle tutarlı | KIRMIZI |
| AC-6 [Medium] | `TestSearchFilesRecursiveSymlinkEscape` | `test_nested_symlink_pointing_outside_allowed_root_is_excluded` — `skipif(os.name == "nt", ...)` | SKIP (Windows) / beklenen YEŞİL olurdu Unix'te bile şu an (mevcut non-recursive kod zaten hiç alt klasöre inmiyor, dolayısıyla symlink de sonuçta yok) |
| AC-7 [Medium] | `TestSearchFilesHiddenFolderNotDescended` | `test_files_under_hidden_subfolder_are_never_scanned` | Şu an zaten YEŞİL (mevcut non-recursive kod hiçbir alt klasöre inmediği için `.git/` altına da inmiyor) — recursive implementasyon bu davranışı KORUMAK zorunda, regresyon-koruma testi olarak kalıyor |

## pytest sonuç özeti

Komut: `.venv/Scripts/python.exe -m pytest backend/tests/test_file_search.py backend/tests/test_main_integration.py -v`

```
7 failed, 113 passed, 4 skipped, 5 warnings in 5.72s
```

KIRMIZI (beklenen) 7 test:
- `TestSearchFilesContentContainsNowRecursive::test_subfolder_file_content_is_matched`
- `TestSearchFilesRecursiveDiscovery::test_file_two_levels_deep_is_found`
- `TestSearchFilesRecursiveDiscovery::test_file_two_levels_deep_is_found_with_name_filter`
- `TestSearchFilesDepthLimit::test_file_beyond_max_depth_is_excluded_without_error`
- `TestSearchFilesCycleProtection::test_visited_path_tracking_prevents_infinite_loop_without_real_symlink`
- `TestSearchFilesContentContainsRecursive::test_content_search_finds_match_in_nested_folder`
- `TestSearchFilesRecursiveTimeout::test_recursive_search_times_out_and_returns_partial_flag`

4 SKIP: Windows'ta `os.symlink()` admin/developer-mode gerektiren testler (AC-3b, AC-6, ve
mevcut dosyadaki #314'ten miras iki symlink testi) — mevcut dosyadaki aynı `skipif` deseni.

113 PASS: değişmeyen mevcut testler + AC-7 regresyon-koruma testi (şu anki non-recursive
davranışla zaten doğru, recursive implementasyon bunu bozmamalı).

## Notlar / Temizlik

Bu görev bir şey KALDIRMIYOR (implementasyon yok, sadece test ekleme/güncelleme) —
test.md'nin "temizlik kontrolü" (kalıntı grep taraması) bu red step için uygulanmadı,
kapsam dışı. `search_files` içindeki mevcut "non-recursive" docstring/yorum satırları
implementasyon (green) adımında güncellenecek, bu red step'te dokunulmadı.

## Open Questions

Yok.
