# Plan — `_db_session_factory` test izolasyonu (Saga #318 red-team takibi)

## Dosya Değişiklikleri

### backend/tests/conftest.py (yeni)
- `autouse=True` fixture: her testten önce (ve sonra) `backend.main._db_session_factory`'i
  `None`'a resetler. `get_db_session`'ı override etmeyen testler artık her zaman
  kendi `monkeypatch`'lediği `APPDATA` altında taze bir engine kullanır.

### backend/tests/test_main_integration.py
- İki regresyon testi eklendi:
  1. `test_db_session_factory_cache_is_reset_before_this_test_runs` — cache'in
     testten önce `None` olduğunu doğrudan doğrular.
  2. `test_db_session_factory_cache_does_not_leak_across_tests_with_different_appdata` —
     override'sız bir `clear-history` çağrısının kendi `tmp_path`'ine yazdığını doğrular.

## Doğrulama
- Fixture olmadan (conftest.py geçici kaldırılarak) her iki yeni test KIRMIZI
  (`AssertionError: ... is None`) — devlogdaki riskin gerçek olduğu doğrulandı.
- Fixture eklenince ikisi de YEŞİL.
- Tam suite: 555 passed, 41 failed — baseline (conftest.py'siz) ile BİREBİR AYNI
  41 başarısız test kümesi (hepsi ortama bağlı: Windows-only path testleri,
  Tesseract/Poppler eksikliği vb.) — regresyon yok.

## Bağımlılık
Yok.
