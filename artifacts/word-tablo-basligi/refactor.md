# Refactor — word-tablo-basligi

## Değerlendirilen adaylar

1. **`append_table`'ın tempfile+atomik-replace bloğu (~10 satır),
   `excel_rows.append_excel_rows`/`word_table.py` arasında (ve
   `pdf_pages.py`/`pdf_compress.py` ile) TEKRARLANIYOR.** Değerlendirildi
   ama uygulanmadı: bu, projenin ÖNCEKİ tüm görevlerinde (EXCEL_SORT,
   PDF_EXTRACT_PAGES, PDF_COMPRESS, EXCEL_CREATE/APPEND) AYNI gerekçeyle
   ertelenmiş bir cross-module karar — kapsam bu görevde değişen
   dosyalarla sınırlı, burada YAPILMAZ.
2. **Sütun sayısı doğrulama döngüsü (`for row in rows: if len(row) !=
   reference_col_count`) tek satırlık bir `all()`/generator ifadesine
   sıkıştırılabilir mi?** Değerlendirildi ama uygulanmadı: mevcut hali
   zaten okunaklı, `all()` ifadesi HANGİ satırın uyuşmadığını
   raporlamayı zorlaştırır (şu an hata mesajı genel olsa da, gelecekte
   hangi satırın hatalı olduğunu eklemek isterse mevcut döngü yapısı
   buna daha uygun) — sadeleştirme okunabilirlik kazandırmıyor.
3. **`headers is not None` kontrolü 3 farklı yerde tekrarlanıyor
   (`reference_col_count` hesabı, `total_row_count` hesabı, yazma
   döngüsü).** Değerlendirildi ama uygulanmadı: fonksiyon zaten kısa
   (~20 satır çekirdek mantık), üç kontrolü ayrı bir yardımcıya
   çıkarmak (`_headers_or_first_row_length` gibi) tek kullanımlı bir
   soyutlama katmanı ekler, okunabilirlik kazancı ölçülebilir değil.

## Uygulanan değişiklik
Yok.

## Sonuç
Üç aday da ya kapsam dışı (cross-module), ya yanlış (hata raporlamayı
zayıflatır), ya da gereksiz soyutlama olurdu. `ponytail` varsayılanı
geçerli — dokunulmadı. Test paketi yeniden koşulmadı (kod değişmedi);
mevcut verify_report.md sonucu geçerli.
