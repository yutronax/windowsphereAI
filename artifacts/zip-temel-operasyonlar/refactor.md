# Refactor — zip-temel-operasyonlar

## Uygulanan değişiklik

**`_write_zip_atomically` yardımcı fonksiyonu çıkarıldı** (`backend/zip_ops.py`).

**Neden şimdi:** `create_zip`, `add_to_zip`, `merge_zips` — ÜÇÜ DE AYNI
DOSYADA, AYNI tempfile+atomik-replace bloğunu (mkstemp, os.close, try/
`zf` yazma/`temp_path.replace`, except/unlink) BİREBİR tekrarlıyordu.
Önceki görevlerde (EXCEL_SORT, PDF_EXTRACT_PAGES, PDF_COMPRESS,
EXCEL_CREATE/APPEND) bu tekrar CROSS-MODULE olduğu için (farklı dosyalar,
farklı API'ler) ertelenmişti — ama red-team ısrarla "3. bir operasyon
gelmeden önce ortak yardımcıya çıkarılmalı" diyordu. Bu görevde tam olarak
o eşik aşıldı: 3 tekrar, TEK dosyada, AYNI API (`zipfile.ZipFile`) — artık
cross-module bir karar değil, bu görevin kapsamı İÇİNDE, ölçülebilir bir
tekrar (3x ~13 satır → 1 paylaşılan fonksiyon + 3 ince sarmalayıcı).

**Ölçülebilir okunabilirlik iddiası:** 3 tekrarın her biri ~13 satır
boilerplate taşıyordu (39 satır toplam); refactor sonrası 1 yardımcı (15
satır) + 3 çağıran (her biri sadece "içeriği nasıl doldur" mantığını,
~3-5 satır, taşıyor). Bir sonraki hata düzeltmesi (ör. tempfile
izinlerinde bir sorun) artık TEK yerde yapılır, üç yerde değil.

**Test sonucu:** Her adımda testler koştu — hedefli alt küme (32/32,
önceki 37'den zip-slip'e özel olmayan bazı testler dahil edilmedi çünkü
`-k zip` filtresi biraz farklı eşleşti, tüm ZIP testleri kapsandı) ve tam
suite (500/500) yeşil kaldı, regresyon yok.

## Değerlendirilen ama uygulanmayan adaylar

1. **`extract_zip`'in zip-slip tarama döngüsü ile gerçek `extractall`
   çağrısı ayrı fonksiyonlara bölünebilir mi?** Değerlendirildi ama
   uygulanmadı: fonksiyon zaten kısa (~10 satır), iki adımı (tara,
   sonra çıkar) ayırmak "tüm-ya-da-hiç" garantisinin TEK fonksiyonda
   görünür olma avantajını kaybettirir — okuyan kişi "tarama gerçekten
   çıkarmadan önce mi bitiyor" sorusunu iki fonksiyona bakmadan
   cevaplayamaz hale gelir.
2. **`list_zip_entries`'in dict-comprehension'ı bir dataclass'a
   çevrilebilir mi?** Değerlendirildi ama uygulanmadı: fonksiyon zaten
   API sözleşmesi gereği `dict` döndürüyor (main.py'nin `ZipListResponse`
   şeması dict listesi bekliyor), bir dataclass eklemek gereksiz bir
   dönüşüm katmanı olurdu.

## Sonuç
Bir gerçek, ölçülebilir refactor uygulandı ve testle doğrulandı. İki
ek aday değerlendirilip reddedildi (yanlış soyutlama/gereksiz katman).
