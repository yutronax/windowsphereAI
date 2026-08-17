# Verify Report — Geçmiş Transaction Listesi Endpoint'i (Saga #294)

## Test Sonuçları
`pytest backend/tests -q` → **150/150 PASSED** (3 yeni test:
boş liste senaryosu, en-yeni-önce sıralama + alan doğrulama, tam
path'in asla sızdırılmadığı — sadece klasör adlarının döndüğü).

## Kabul Kriterleri Durumu
- AC-1 (kritik): ✅ `GET /api/transactions` id/createdAt/status/fileCount/
  targetFolders içeren, en yeniden en eskiye sıralı bir liste döndürüyor
  (created_at + id ikincil anahtar ile deterministik sıralama).
- AC-2 (yüksek): ✅ Hiç transaction yoksa `[]` dönüyor (404 değil).
- AC-3 (orta): ✅ `targetFolders` sadece klasör adı, tam mutlak path
  yanıtın hiçbir yerinde geçmiyor (ayrı testle doğrulandı).

## Red-Team Bulgusu ve Düzeltmesi
`obss-red-team` bloklayıcı bir bulgu bulmadı (path sızıntısı yok,
authn/session-scoping eksikliği bilinçli/dar-kapsam kararı olarak
onaylandı — repo'da hiçbir `uvicorn.run`/host binding kodu bulunmadığı
da ayrıca doğrulandı, şu an gerçek bir ağ maruziyeti yok). Tek somut
öneri: `get_db_session`in her istekte `create_db_engine()` çağırması
(`Base.metadata.create_all` + `_add_missing_columns` şema taraması
içeriyor) sık poll'lanabilecek bir "geçmiş" endpoint'i için gereksiz
I/O maliyeti. Öneri HEMEN uygulandı: engine/session-factory artık
süreç başına BİR KEZ (lazy, modül seviyesinde) oluşturuluyor —
`get_db_session` sadece `factory()`/`yield`/`close()` yapıyor. Testler
`get_db_session`'ı `dependency_overrides` ile atladığı için bu cache
test izolasyonunu etkilemedi. 150/150 test yeşil kaldı.

## Sonuç
`ready_to_commit: evet`
