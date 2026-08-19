# Refactor — pdf-sikistirma

## Değerlendirilen adaylar

1. **`compress_pdf`'in `writer.append(reader)` + döngüyle sayfa-bazlı
   sıkıştırma çağrısı, `pdf_compress.py`'ye ÖZGÜ tek bir kullanım —
   ortak bir yardımcıya çıkarılabilir mi?** Değerlendirildi ama
   uygulanmadı: tek çağıran var, `pdf_pages.py`/`excel_sort.py`'nin
   tempfile+atomik-replace iskeleti zaten olduğu gibi (kopyalanarak)
   izlendi — bu üçüncü kopya EXCEL_FILTER'ın red-team incelemesinde
   zaten flag'lenmişti ("3. bir operasyon gelmeden önce ortak yardımcıya
   çıkar" önerisi PDF_EXTRACT_PAGES görevinde de aynı gerekçeyle
   reddedilmişti — farklı dosya tipi/API, cross-module soyutlama bu
   görevin kapsamı dışında, sadece not düşülüyor).
2. **`orchestrator.py`'deki yeni PDF_COMPRESS bloğu, `True`/`False`
   dallanmasıyla EXCEL_FILTER (kayıtlı) ve LIST (kayıtsız) desenlerini
   TEK bir blokta birleştiriyor — bu iki deseni ortak bir yardımcıya
   çıkarmak okunabilirliği artırır mı?** Değerlendirildi ama uygulanmadı:
   bu birleşim SADECE PDF_COMPRESS'e özgü (başka hiçbir operationType
   "bazen kayıtlı bazen kayıtsız" davranmıyor), bir yardımcıya çıkarmak
   tek bir kullanım için gereksiz bir soyutlama katmanı olur — mevcut
   if/else zaten kısa ve doğrudan okunabilir.
3. **`main.py`'deki yeni PDF_COMPRESS warnings bloğu, REDACT'ın statik
   listesiyle YAN YANA duruyor — ikisini ortak bir "warnings builder"
   fonksiyonuna çıkarmak?** Değerlendirildi ama uygulanmadı: REDACT
   STATİK (her zaman uyarır), PDF_COMPRESS DİNAMİK (transaction.operations'a
   bakarak koşullu uyarır) — iki farklı hesaplama şekli, ortak bir
   fonksiyona zorlamak yanlış bir soyutlama olurdu.

## Uygulanan değişiklik
Yok.

## Sonuç
Üç aday da ya kapsam dışı (cross-module), ya tek-kullanımlı gereksiz
soyutlama, ya da yanlış-eşleşen bir birleştirme olurdu. `ponytail`
varsayılanı geçerli — dokunulmadı. Test paketi yeniden koşulmadı (kod
değişmedi); mevcut verify_report.md sonucu geçerli.
