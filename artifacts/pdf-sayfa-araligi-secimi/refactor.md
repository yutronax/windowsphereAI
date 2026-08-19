# Refactor — pdf-sayfa-araligi-secimi

## Değerlendirilen adaylar

1. **`extract_pdf_pages`/`delete_pdf_pages`'in ikisi de `PdfReader(source_path)`
   çağırıyor, sonra `_write_pages` İÇİNDE aynı dosya İKİNCİ KEZ okunuyor
   (reader nesnesi paylaşılmıyor).** Değerlendirildi ama uygulanmadı:
   `_write_pages`'e bir `reader` parametresi eklemek imzasını değiştirir,
   iki çağıranın davranışını değiştirmeden sadece I/O sayısını azaltır —
   ölçülebilir bir okunabilirlik kazancı YOK (fonksiyon zaten kısa ve
   anlaşılır), sadece performans "iyileştirmesi" — refactor skill'in
   "İzin verilmeyen" listesinde açıkça yasak ("performans iyileştirmesi
   için davranış değişimi" değilse bile, gerekçesi salt performans
   olduğu için `ponytail` varsayılanı "dokunma"yı gerektiriyor). PDF'ler
   küçük/orta boyutlu olduğu için pratik bir maliyeti yok.
2. **`_write_pages`'in kendisi (tempfile+atomik-replace+cleanup) EXCEL_SORT/
   EXCEL_FILTER'daki BİREBİR aynı boilerplate'i tekrar ediyor — 3. bir
   modülde (`pdf_pages.py`) 3. kez kopyalandı.** Değerlendirildi ama
   uygulanmadı: bu tekrar `excel_sort.py`'nin red-team incelemesinde
   ZATEN flag'lenmişti ("3. bir EXCEL_* operasyonu gelmeden önce ortak
   yardımcıya çıkarılmalı" — ama o öneri EXCEL_SORT/EXCEL_FILTER'a
   özeldi, PDF farklı bir dosya tipi/API (`pypdf` vs `openpyxl`)
   kullanıyor, ortak bir soyutlama PDF ve Excel arasında ZORLAMA bir
   soyutlama olurdu (iki farklı writer API'si, iki farklı "guard" mantığı).
   Bu refactor'ün kapsamı `pdf-sayfa-araligi-secimi`'nin değiştirdiği
   dosyalarla sınırlı — cross-module bir soyutlama ayrı bir görev/karar,
   burada dokunulmadı, sadece not düşüldü.
3. **`models.py`'deki iki yeni validator (`pdf_extract_pages_fields_only_for_pdf_extract_pages`,
   `pdf_delete_pages_fields_only_for_pdf_delete_pages`) neredeyse birebir
   aynı gövdeye sahip — tek bir parametreli yardımcıya çıkarılabilir mi?**
   Değerlendirildi ama uygulanmadı: `excel_sort_fields_only_for_excel_sort`/
   `excel_filter_fields_only_for_excel_filter`/`redact_fields_only_for_redact`
   gibi önceki TÜM operationType-özel validator'lar da aynı şekilde
   ayrı ayrı yazılmış — proje genelinde YERLEŞİK bir konvansiyon (her
   yeni operationType kendi açık validator'ını alır, ortak bir "field
   guard factory" YOK). Bu görevde tek başına bu iki validator'ı
   ortaklaştırmak, projenin geri kalanıyla TUTARSIZ bir istisna
   yaratırdı — proje-çapında bir karar olmadan burada yapılmaz.

## Uygulanan değişiklik
Yok.

## Sonuç
Üç aday da ya yanlış gerekçeli (salt performans), ya kapsam dışı
(cross-module soyutlama), ya da proje konvansiyonuyla tutarsız bir
istisna yaratacaktı. `ponytail` varsayılanı geçerli — dokunulmadı. Test
paketi yeniden koşulmadı (kod değişmedi); mevcut verify_report.md sonucu
geçerli.
