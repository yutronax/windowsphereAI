# Refactor — excel-satir-filtreleme

## Değerlendirilen adaylar (uygulanmadı)

1. **`sort_excel_sheet`/`filter_excel_sheet` ortak tempfile+atomik-replace
   iskeletini ortak bir yardımcıya çıkar.** Reddedildi: sadece 2 çağıran var,
   ikisi arasında gerçek davranış farkı var (biri satır sırasını değiştirir,
   diğeri satır alt kümesi üretir — ortak bir `_write_via_tempfile(fn)`
   sarmalayıcısı ekstra bir dolaylılık katmanı ekler ama tekrar sadece
   ~10 satır boilerplate, `ponytail` ölçütüyle "daha temiz olur" iddiasından
   öteye geçmiyor). Bu zaten plan.md/code_diff.md'de bilinçli bir tercih
   olarak not edilmişti.
2. **`resolve_sort_column`'ı `resolve_column` olarak yeniden adlandır.**
   Reddedildi: plan.md'de zaten (a) seçeneği olarak kararlaştırılmıştı —
   isim "sort" içeriyor olsa da yanıltıcılığı düşük (fonksiyon hâlâ "sıralama
   sütununu çöz" anlamında kullanılıyor, filtrede de aynı anlam geçerli) ve
   yeniden adlandırma `test_excel_sort.py`'nin import satırına dokunma
   riski taşıyor — davranışı korumak için gereksiz risk.
3. **`filter_excel_sheet`'teki `str(cell_value) == target_value`
   karşılaştırmasını `_sort_key` ile paylaşılan bir yardımcıya çıkar.**
   Reddedildi: `_sort_key` None-güvenli SIRALAMA anahtarı üretiyor (tip
   karşılaştırmasını atlatmak için), filtredeki ihtiyaç basit eşitlik —
   ikisini ortaklaştırmak yanlış bir soyutlama (iki farklı amaç aynı
   fonksiyona zorlanmış olur).

## Uygulanan değişiklik
Yok.

## Sonuç
Kod zaten EXCEL_SORT'un kanıtlanmış mimari desenini birebir izliyor
(bilinçli tercih, code_diff.md CAVEMAN Review bölümünde gerekçelendirildi).
Üç aday da ya risk/fayda dengesi negatif ya da yanlış soyutlamaya yol
açıyor — `ponytail` varsayılanı ("dokunma") burada geçerli. Test paketi
yeniden koşulmadı (kod değişmedi); mevcut verify_report.md sonucu geçerli.
