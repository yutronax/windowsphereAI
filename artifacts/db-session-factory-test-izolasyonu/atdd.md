# ATDD — `backend.main._db_session_factory` process-global cache test izolasyonu

## Persona
Backend geliştirici / test suite'i bakımı yapan mühendis.

## Goal
Saga #318 red-team bulgusu: `backend/main.py::_get_db_session_factory` süreç
başına bir kez (lazy) oluşturulup modül seviyesinde önbelleğe alınıyor.
`get_db_session`'ı `app.dependency_overrides` ile override ETMEYEN testler
(ör. `test_clear_history_endpoint_sets_cleared_at_timestamp_and_returns_it`,
`test_clear_history_is_idempotent_updating_timestamp`) bu cache'i kullanıyor.
Cache, testler arasında SIFIRLANMADIĞI için: pytest sürecindeki İLK testin
`APPDATA`'sıyla (tmp_path) kurulan engine, sonraki testlerin FARKLI
`monkeypatch.setenv("APPDATA", ...)` değerlerini görmeden aynı (artık silinmiş
olabilecek) eski tmp_path veritabanı dosyasına bağlı kalır — test çalıştırma
SIRASINA bağlı sessiz veri/izolasyon hatası riski.

## User Story
Bir geliştirici olarak, `get_db_session`'ı override etmeyen herhangi bir test
her zaman KENDİ `monkeypatch`'lediği `APPDATA` altında taze bir DB engine
kullanmalı — başka bir testin daha önce oluşturduğu eski engine'e sessizce
bağlı kalmamalı.

## Acceptance Criteria
- AC1 (P0): Her test fonksiyonundan ÖNCE `backend.main._db_session_factory`
  `None`'a resetlenir (autouse fixture, `backend/tests/conftest.py`).
- AC2 (P0): İki test — biri `get_db_session`'ı override ETMEDEN farklı bir
  `APPDATA` (`tmp_path`) ile çalışır, sırasıyla art arda çalıştırıldığında
  — her biri KENDİ `tmp_path`'indeki DB dosyasını kullanır (birbirini
  etkilemez). Regresyon testi olarak eklenir.
- AC3 (P0): Var olan tüm testler (`get_db_session`'ı override edenler dahil)
  kırılmaz — fixture sadece cache'i sıfırlıyor, override mekanizmasına
  dokunmuyor.
- AC4 (P1): Fixture, `backend/tests/` altındaki TÜM test dosyalarına otomatik
  uygulanır (autouse, dosya-bazlı import gerektirmez).

## Test Strategy
Unit/entegrasyon — `conftest.py` fixture'ının kendisi dolaylı olarak yeni bir
regresyon testiyle (AC2) doğrulanır: override'sız iki ardışık test, farklı
`APPDATA` ile, ayrı DB dosyaları üretir mi diye kontrol edilir.

## Risks / Assumptions
- Assumption: Fixture'ı `function`-scope autouse yapmak yeterli; `session`
  başına bir engine daha performanslı olurdu ama izolasyon garantisini
  bozar (devlog'un tam istediği şey buydu) — performans burada bilinçli
  olarak izolasyona feda edilir (testler zaten `sqlite`+`tmp_path`, ucuz).
