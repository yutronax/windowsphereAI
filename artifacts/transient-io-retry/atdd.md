# ATDD — Dosya I/O için geçici hata (kilitli dosya/antivirüs) toleransı (Saga #310)

## Persona
Mali müşavir/muhasebeci kullanıcı, MOVE/COPY/DELETE/RENAME işlemi yaparken
hedef dosya Excel/Outlook'ta açık olabilir (WinError 32) veya antivirüs
geçici olarak bloklayabilir (WinError 5, tipik 2-5 saniye).

## Goal
`backend/orchestrator.py`'nin `_forward_move`/`_forward_copy`/`_forward_delete`
fonksiyonları bu iki geçici hata sınıfında tek denemede başarısız
olmasın — sınırlı sayıda, backoff'lu retry denesin. Kalıcı bir hata
(yetkisizlik, dosya yok, vb.) davranışı DEĞİŞMEMELİ.

## Acceptance Criteria (öncelik sırasıyla)
1. **P0** — `shutil.move`/`shutil.copy2`/`os.unlink` (DELETE'in `source_path.unlink()`'i
   dahil) bir `OSError` fırlatırsa VE bu hatanın `winerror` özniteliği 32
   (kilitli dosya) veya 5 (erişim reddedildi) ise, işlem sınırlı sayıda
   (3 deneme) backoff'lu (artan bekleme) olarak TEKRAR denenir.
2. **P0** — Retry'ler tükenirse (3. deneme de aynı geçici hatayla
   başarısız olursa) orijinal `OSError` OLDUĞU GİBİ fırlatılır — mevcut
   `apply_plan`'ın hata/rollback akışı DEĞİŞMEZ.
3. **P0** — `winerror` 32/5 DIŞINDA bir `OSError` (örn. `FileNotFoundError`,
   izin hatası winerror farklıysa) HİÇ retry edilmeden derhal fırlatılır —
   kalıcı hatalarda gecikme eklenmemeli.
4. **P1** — Retry başarılı olursa (örn. 2. denemede kilit açılırsa) işlem
   normal şekilde tamamlanmış sayılır, çağıran kod (apply_plan) hiçbir
   fark görmez (fonksiyon sadece normal dönüş yapar).
5. **P1** — MOVE/COPY/DELETE'in ÜÇÜ de aynı retry sarmalayıcısını
   kullanır (kod tekrarı yok, tek bir yardımcı fonksiyon).

## Behavior-Contract Table
| Senaryo | Beklenen davranış |
|---|---|
| İlk denemede başarı | Retry hiç tetiklenmez, normal dönüş |
| winerror=32, 1-2 kez, sonra başarı | Backoff'lu retry, sonunda başarı, hata dışarı sızmaz |
| winerror=5, 1-2 kez, sonra başarı | Aynı, winerror=5 için de |
| winerror=32, TÜM denemeler başarısız | 3 denemeden sonra orijinal OSError fırlatılır |
| winerror=None veya 32/5 dışı bir değer | Retry YOK, hemen fırlatılır |

## Test Strategy
Unit test (backend/tests/test_orchestrator.py) — `monkeypatch` ile
`shutil.move`/`shutil.copy2`/`os.unlink`'i sahte bir `OSError(winerror=X)`
fırlatacak şekilde N kez başarısız, sonra başarılı yapan bir sayaç
fonksiyonuyla değiştir. `time.sleep`'i de monkeypatch'le (testler
gerçekten saniyelerce beklemesin).

## Risks/Assumptions
- Retry sayısı ve backoff süreleri (3 deneme, üstel backoff) bu görevde
  YENİDEN tasarlandı — referans projedeki (`safe_io_call`) sabit sayılar
  BİREBİR kopyalanmadı.
- 20+ dosyalık toplu işlemler için ayrı bir onay eşiği (Saga #311) bu
  görevin kapsamı dışında.
