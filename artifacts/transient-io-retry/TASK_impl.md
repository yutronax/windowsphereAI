# Görev
## Amaç
backend/orchestrator.py'ye yeni bir `_retry_on_transient_io_error(func, *args, **kwargs)`
yardımcı fonksiyonu ekle — backend/tests/test_orchestrator.py'deki
`test_retry_on_transient_io_error_*` testlerini (5 adet) YEŞİLE çevirecek
minimal implementasyon.

## Kabul kriterleri (testlerden türetilmiş, bunları YAPMA emin ol)
1. `func()`'ı çağırır, başarılı olursa sonucu direkt döner (retry yok).
2. `func()`, `OSError` fırlatır ve bu hatanın `winerror` attribute'u 32
   VEYA 5 ise: `time.sleep(...)` ile backoff bekleyip TEKRAR dener.
   Toplamda EN FAZLA 3 deneme yapar.
3. 3 denemenin hepsi de aynı geçici (winerror 32/5) hatayla başarısız
   olursa, son denemenin `OSError`'ı OLDUĞU GİBİ (yutulmadan) dışarı
   fırlatılır.
4. `func()`, `winerror` attribute'u OLMAYAN veya 32/5 DIŞINDA bir
   değere sahip bir `OSError` fırlatırsa, HİÇ retry yapılmadan (time.sleep
   HİÇ çağrılmadan) hemen fırlatılır.
5. Retry başarılı olursa (örn. 2. denemede başarılı), `time.sleep` en az
   1 kez çağrılmış olmalı (backoff gerçekten uygulandığını kanıtlamak
   için).

## İkinci adım: fonksiyonu gerçek yerlere KABLOLA
`_retry_on_transient_io_error`'ı yazdıktan sonra, backend/orchestrator.py
içindeki şu üç fonksiyonun İÇİNDEKİ dosya-sistemi çağrılarını bu
sarmalayıcıdan geçir (fonksiyonların KENDİ imzası/davranışı DEĞİŞMEMELİ,
sadece içindeki shutil/os çağrıları sarmalanmalı):
- `_forward_move`: `shutil.move(str(source_path), str(destination_path))`
  → `_retry_on_transient_io_error(shutil.move, str(source_path), str(destination_path))`
- `_forward_copy`: `shutil.copy2(...)` aynı şekilde sarmalanır.
- `_forward_delete`: içindeki `shutil.copy2(...)` VE `source_path.unlink()`
  çağrılarının İKİSİ DE ayrı ayrı sarmalanır (ikisi de dosya-sistemi I/O'su).

## Dosya sınırı
SADECE backend/orchestrator.py değiştirilebilir. Testlere DOKUNMA
(backend/tests/test_orchestrator.py zaten doğru, sadece implementasyonu
onlara uydur).

## Kısıtlar
- Minimal implementasyon — gereksiz sınıf/config/parametre icat etme.
- `time` modülü zaten dosyanın başında import edilmiş olabilir, kontrol et.
- Mevcut kod stiline (docstring, yorum dili Türkçe) uy.
