# Test Diff — word-tablo-basligi

Yazım motoru: bağımsız `efektor` subagent (Codex kotası dolu; kullanıcı
isteğiyle bu görevde test/kod yazımı alt ajanlara devredildi).

## Ortam notu (ÖNEMLİ)
Test-yazım subagent'ı `python-docx`'i proje `.venv`'i YERİNE global bir
Python 3.11 kurulumuna (`AppData\Local\Programs\Python\Python311`) kurmuştu
— bu proje her zaman `.venv/Scripts/python.exe` kullanıyor (önceki tüm
görevlerdeki bağımsız doğrulama komutları da hep bunu kullandı). Bu tutarsızlık
fark edilip düzeltildi: `python-docx` `.venv`'e de `pip install` edildi
(`.venv/Scripts/python -m pip install python-docx` → `docx 1.2.0`). Kırmızı
durum doğrulaması `.venv` ile bağımsız olarak TEKRARLANDI.

## backend/tests/test_word_table.py (yeni, 6 test)
`append_table` unit testleri (gerçek `.docx` fixture'ları python-docx'in
kendisiyle üretiliyor):
- Happy path (başlıklı) — AC-1
- Happy path (başlıksız) — AC-2
- Sütun uyuşmazlığı — AC-3
- Kaynak yok — AC-4
- Kaynak bozuk — AC-4
- Backup'ın yazmadan ÖNCE alındığı doğrulaması

## backend/tests/test_orchestrator.py (ekleme, 5 test)
`OperationType.WORD_APPEND_TABLE` orchestrator entegrasyon testleri —
happy path (başlıklı/başlıksız), sütun uyuşmazlığı, kaynak yok/bozuk,
path whitelist ihlali (EXCEL_APPEND deseni).

## Durum
Kırmızı (`.venv` ile bağımsız doğrulandı):
- `test_word_table.py` → `ModuleNotFoundError: No module named 'backend.word_table'`
- `test_orchestrator.py -k "word_table or word_append"` → 5 failed, `AttributeError: WORD_APPEND_TABLE`

## Bilinçli tasarım kararı
Testler python-docx'in API şeklini VARSAYMADAN, davranış sözleşmesine
(ATDD) göre yazıldı — implementasyon adımı hangi python-docx yaklaşımını
(add_table vs add_row) seçerse seçsin testler DEĞİŞMEMELİ.

code-copilot implementasyonu (backend/word_table.py + models.py +
orchestrator.py + requirements.txt) yazınca yeşile dönmesi bekleniyor.
