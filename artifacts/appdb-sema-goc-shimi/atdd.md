---
task_slug: appdb-sema-goc-shimi
priority: medium
coverage_target: "70/0/30"
performance_target: "yok"
test_strategy: "unit (pytest, gerçek sqlite dosyası + eski şema simülasyonu)"
affected_modules:
  - backend/db.py
saga_task_id: 284
epic_id: 25
---

# ATDD — app.db Şema Göçü Shim'i (Saga #284)

## Goal
`create_db_engine`'in `Base.metadata.create_all` çağrısı yeni tablo
eklemede idempotent ama VAR OLAN bir tabloya yeni kolon eklemede
sessizce hiçbir şey yapmıyor. Gerçek kullanıcı makinelerinde `app.db`
oluşmaya başladıktan sonra (Saga #274/#276 ship edildi) şema
değişikliği yapmak bu olmadan geri dönüşü zor bir sorun haline gelir.

## Sorular ve Cevaplar (saga-oto tarafından otomatik seçildi)

**S1: alembic mi, manuel shim mi?** Cevap: Manuel shim. Gerekçe: alembic
yeni bir bağımlılık + migration dosyaları/versioning altyapısı
gerektirir — proje henüz hiç Python bağımlılık dosyasına (requirements.
txt) sahip değil (task_0ab06e5e olarak flaglendi), bu noktada alembic
eklemek "dar kapsamı seç" ilkesiyle çelişir. Basit bir "eksik kolon
varsa ALTER TABLE ADD COLUMN" shim'i, tarif edilen riski (sessiz kolon
kaybı) kapatmak için yeterli — SQLite `ADD COLUMN`'ı zaten destekliyor,
kolon SİLME/tip DEĞİŞTİRME gibi karmaşık göçler bu MVP aşamasında
gerekmiyor. (saga-oto tarafından otomatik seçildi)

**S2: Shim ne zaman çalışmalı?** Cevap: `create_db_engine` içinde,
`Base.metadata.create_all`den HEMEN SONRA — her engine oluşturmada
(uygulama başlangıcında) otomatik çalışsın, ayrı bir CLI komutu/manuel
adım GEREKMESİN (kullanıcı bunu bilmeyecek/çalıştırmayacak). (saga-oto
tarafından otomatik seçildi — kullanıcı deneyimi: sessiz/otomatik olmalı)

## Kabul Kriterleri
1. **AC-1 (kritik):** Yeni bir `app.db` (tablo yok) için `create_db_engine`
   önceki davranışla aynı şekilde çalışır (tüm tabloları sıfırdan oluşturur).
2. **AC-2 (kritik):** Var olan bir tabloda (ör. `file_operations`) eksik
   bir kolon varsa (model'de var, DB'de yok), shim bunu `ALTER TABLE ...
   ADD COLUMN` ile ekler — veri kaybı olmadan.
3. **AC-3 (yüksek):** Zaten güncel bir şemada shim hiçbir şey yapmaz
   (idempotent, tekrar tekrar çağrılabilir).
4. **AC-4 (yüksek):** Var olan satırlardaki veri (ör. mevcut bir
   `Transaction` kaydı) shim çalıştıktan sonra bozulmadan kalır.

## Riskler / Varsayımlar / Bilinmeyenler
- **Kapsam dışı (bilinçli):** Kolon SİLME, tip DEĞİŞTİRME, index
  değişiklikleri — SQLite'ta bunlar tablo yeniden oluşturmayı
  gerektirir, çok daha riskli bir işlem; bu MVP aşamasında hiç ihtiyaç
  yok, gerçek bir gereksinim çıkarsa alembic'e geçiş o zaman
  değerlendirilmeli.
- **Varsayım:** SQLite'a özgü (proje zaten SQLite-only, `db.py`'de
  başka bir DB motoru desteklenmiyor).

## Test Stratejisi
Gerçek sqlite dosyası (`tmp_path`) üzerinde: (1) eski bir şemayı elle
(SQLAlchemy Core ile, `Base.metadata` kullanmadan) oluşturup eksik kolon
senaryosunu simüle et, (2) `create_db_engine` çağır, (3) PRAGMA
table_info ile kolonun eklendiğini doğrula.
