# Görev
## Amaç
backend/tests/test_orchestrator.py dosyasına, backend/orchestrator.py'de HENÜZ
YAZILMAMIŞ bir `_retry_on_transient_io_error(func, *args, **kwargs)` yardımcı
fonksiyonunu test eden yeni testler ekle (bu fonksiyon orchestrator.py'de
tanımlı OLMAYACAK, testler şimdilik KIRMIZI kalmalı — bu bilinçli).

## Kabul kriterleri (test edilmesi gereken davranış)
1. `_retry_on_transient_io_error`, verdiği `func`'ı çağırır; `func` ilk
   denemede başarılı olursa direkt onu döner, hiç retry olmaz.
2. `func`, `OSError` fırlatır ve bu hatanın `winerror` attribute'u 32 ise:
   fonksiyon `func`'ı tekrar dener (monkeypatch ile `time.sleep`'i sahte
   yapıp gerçek bekleme olmadan test et). 2. denemede `func` başarılı
   olursa sonuç normal döner, hata dışarı sızmaz.
3. Aynısı `winerror=5` için de geçerli olmalı.
4. `func` TÜM 3 denemede de aynı `winerror=32` OSError'ını fırlatırsa,
   3. denemeden sonra bu orijinal `OSError` DIŞARI fırlatılır (retry
   tükenir, hata yutulmaz).
5. `func`, `winerror` attribute'u OLMAYAN veya 32/5 DIŞINDA bir değere
   sahip bir `OSError` (örn. `FileNotFoundError`) fırlatırsa, HİÇ retry
   yapılmadan hemen fırlatılır (`func`'ın sadece 1 kez çağrıldığını bir
   sayaç ile doğrula).

## Dosya sınırı
SADECE backend/tests/test_orchestrator.py değiştirilebilir. Başka hiçbir
dosyaya dokunma — backend/orchestrator.py'yi DEĞİŞTİRME (implementasyon
ayrı bir adımda yazılacak).

## Notlar
- Testler `from backend.orchestrator import _retry_on_transient_io_error`
  import edecek — bu fonksiyon henüz yok, import hatası/AttributeError
  vermesi BEKLENEN ve DOĞRU bir durum (red adımı).
- Mevcut test dosyasındaki import/fixture stiline uy (dosyanın başındaki
  import bloğuna bak).
- Sahte OSError üretmek için: `err = OSError("mesaj"); err.winerror = 32; raise err`.
- Basit, minimal testler yaz — gereksiz yardımcı sınıf/fixture icat etme.
