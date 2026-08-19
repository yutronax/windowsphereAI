# Refactor — excel-create-read-append

## Değerlendirilen adaylar

1. **`create_excel_file`/`append_excel_rows`'un tempfile+atomik-replace
   blokları (~6 satır) birebir tekrarlanıyor.** Değerlendirildi ama
   uygulanmadı: `excel_sort.py` (EXCEL_SORT/EXCEL_FILTER),
   `pdf_pages.py` (extract/delete), `pdf_compress.py` — hepsi AYNI
   tekrarı taşıyor ve önceki görevlerin red-team incelemelerinde bu
   ZATEN değerlendirilip "3. bir operasyon gelmeden önce ortak yardımcıya
   çıkarılmalı" (ama HER SEFERİNDE tek bir görevin kapsamı için değil,
   cross-module bir karar olarak) ertelendi. Bu görev de aynı kararı
   sürdürüyor — kapsam bu görevde değişen dosyalarla sınırlı, cross-module
   bir soyutlama burada YAPILMAZ.
2. **`read_excel_range`'in tek-hücre/tek-satır/çok-satır normalizasyon
   dallanması (3 ayrı `if`/`isinstance` kontrolü) sadeleştirilebilir mi?**
   Değerlendirildi ama uygulanmadı: openpyxl'in `ws[range]` GERÇEKTEN üç
   farklı şekil döndürüyor (tek Cell, Cell-tuple, tuple-of-Cell-tuple) —
   bu, kodun keyfi karmaşıklığı değil, openpyxl'in API'sinin doğal
   sonucu. Testler (`test_excel_rows.py`) bu üç şekli AYRI AYRI
   doğruluyor, birleştirmek okunabilirliği artırmaz.
3. **`append_excel_rows`'un generic `except Exception` bloğu daha
   spesifik bir exception türüne (`InvalidFileException` gibi)
   daraltılabilir mi?** Değerlendirildi ama uygulanmadı: openpyxl'in
   `load_workbook`'unun bozuk dosyalarda fırlattığı exception türü
   dosyanın bozulma şekline göre DEĞİŞEBİLİR (zip hatası, XML parse
   hatası, vb.) — geniş `except Exception` burada BİLİNÇLİ bir tercih
   (AC-7'nin "kaynak bozuk = hata" gereksinimi için TÜM bozukluk
   türlerini yakalamak gerekiyor), daraltmak yeni bir kör nokta açabilir.

## Uygulanan değişiklik
Yok.

## Sonuç
Üç aday da ya kapsam dışı (cross-module), ya yanlış (API'nin doğal
karmaşıklığını gizler), ya da riskli (hata yakalamayı daraltır) olurdu.
`ponytail` varsayılanı geçerli — dokunulmadı. Test paketi yeniden
koşulmadı (kod değişmedi); mevcut verify_report.md sonucu geçerli.
