# Refactor — image-kirpma-thumbnail

## Değerlendirilen adaylar

1. **`crop_image`/`create_thumbnail`'ın tempfile+atomik-replace bloğu
   (~10 satır) İKİ kez tekrarlanıyor (aynı dosyada).** Değerlendirildi
   ama uygulanmadı: bu oturumda kurulan eşik (zip-temel-operasyonlar
   görevinde) "3. tekrardan sonra çıkar" idi — `excel_rows.py`'de de
   AYNI 2-tekrar durumu vardı ve BİLEREK dokunulmamıştı (o görevin
   refactor.md'sinde gerekçelendirildi: "cross-module bir karar,
   burada yapılmaz" + sadece 2 kullanım). Burada da tutarlılık için
   AYNI karar — 2 tekrar, ölçülebilir bir soyutlama eşiğini
   GEÇMİYOR (zip_ops.py'nin 3'ü aştığı durumdan farklı).
2. **`crop_image`'in geometri kontrolü (`x1<=x0`/`y1<=y0`) ile sınır
   kontrolü (`x0<0 or ... or y1>height`) tek bir kontrole
   birleştirilebilir mi?** Değerlendirildi ama uygulanmadı: iki kontrol
   FARKLI hata sınıflarını temsil ediyor (biri "geometri anlamsız", diğeri
   "kaynağa sığmıyor") — ayrı kalmaları, gelecekte AYRI hata mesajları
   gerekirse (şu an ikisi de aynı `ValueError` ama farklı metin) kolaylık
   sağlıyor, birleştirmek bu ayrımı gizler.

## Uygulanan değişiklik
Yok.

## Sonuç
Tek aday (tempfile tekrarı) bu oturumda kurulan "3+ tekrar" eşiğini
geçmiyor, `excel_rows.py`'deki AYNI durumla tutarlı şekilde dokunulmadı.
İkinci aday yanlış bir birleştirme olurdu. `ponytail` varsayılanı geçerli.
Test paketi yeniden koşulmadı (kod değişmedi); mevcut verify_report.md
sonucu geçerli.
