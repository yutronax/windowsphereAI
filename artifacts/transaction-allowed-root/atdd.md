---
task_slug: transaction-allowed-root
priority: low
coverage_target: "revert_transaction + revert endpoint path'leri (unit + integration)"
performance_target: "n/a — davranışsal/güvenlik değişikliği, performans etkisi yok"
test_strategy: "70/0/30 (unit/integration/e2e) — proje konvansiyonu (pytest unit + FastAPI TestClient integration), e2e/UI yok çünkü frontend değişikliği sadece bir fetch body alanının kaldırılması"
affected_modules:
  - backend/db_models.py
  - backend/file_operations.py
  - backend/orchestrator.py
  - backend/models.py
  - backend/main.py
  - backend/db.py (şema göçü şimi otomatik çalışır, kod değişikliği YOK)
  - ui/src/components/chat/ResultCard.tsx
---

# ATDD — Transaction'a allowed_root kolonu ekle (Saga #301)

## Persona
Bu değişikliğin doğrudan kullanıcısı yok (arka plan güvenlik sağlamlaştırması)
— dolaylı persona: windows-ai-files'ı kullanan, geri al (revert) özelliğini
tetikleyen tek kullanıcı; asıl fayda "istemci taraflı spoof edilmiş
`allowedRoot`'un containment kontrolünü etkisiz kılamaması".

## Amaç
Saga #295'in mimari bulgusunu (bkz. görev açıklaması) kapatmak: `POST
/api/transactions/{id}/revert` artık `allowed_root`'u istemciden değil,
transaction oluşturulurken (`apply_plan`/`create_transaction` sırasında) DB'ye
yazılan `Transaction.allowed_root` kolonundan alır.

## User Story
Bir geliştirici olarak, revert endpoint'inin path-containment kontrolünü
istemcinin gönderdiği keyfi bir `allowedRoot` değeriyle atlatılamamasını
istiyorum ki (ör. istemci `"C:\\"` gönderse bile) gerçek güvenlik sınırı
sunucu tarafında, transaction'ın KENDİ oluşturulduğu köküyle sabitlenmiş olsun.

## Kabul Kriterleri (öncelik sırasıyla)
1. **[P0]** `Transaction` modelinde `allowed_root: str` kolonu var, `apply_plan`
   çağrıldığında (create_transaction sırasında) gerçek `allowed_root`
   değeriyle dolduruluyor.
2. **[P0]** `revert_transaction` fonksiyonu artık `allowed_root`'u parametre
   olarak almıyor (ya da alıyorsa bile KULLANMIYOR) — kendi `transaction.
   allowed_root` alanından okuyor. İstemci bambaşka/geniş bir `allowedRoot`
   gönderse bile (spoofed request body), gerçek geri alma HER ZAMAN
   transaction'ın kendi kayıtlı kökünü kullanır.
3. **[P0]** `RevertTransactionRequest`'ten `allowedRoot` alanı KALDIRILDI —
   endpoint artık request body'de bu alanı beklemiyor/kabul etmiyor.
4. **[P1]** Var olan eski (bu değişiklikten önce oluşturulmuş, `allowed_root`
   kolonu NULL olan) transaction'lar için revert güvenli biçimde başarısız
   olmalı (500 patlamak yerine anlamlı bir hata) — kapsam: yeni
   oluşturulanlar için kolon her zaman dolu, ama savunma amaçlı NULL durumu
   da ele alınmalı.
5. **[P1]** Frontend: `ResultCard`'ın revert `fetch` çağrısı artık body'de
   `allowedRoot` GÖNDERMİYOR (boş body ya da alan hiç yok). `selectedFolder`
   prop'u revert axını GATE'lemek için (`canShowRevert`) hâlâ kullanılabilir
   (bu, UI-taraflı "buton ne zaman gösterilsin" kararı, backend güvenlik
   sınırı DEĞİL) — task açıklaması sadece "revert call'a artık gerekli
   değil" diyor, prop'un component'ten TAMAMEN kaldırılması İSTENMİYOR
   (geriye dönük TransactionResult tipini bozmamak için dar kapsam seçildi).
6. **[P2]** Var olan tüm revert testleri (backend + frontend) hâlâ geçiyor
   (yeşile uyarlanmış haliyle).
7. **[P2]** DB şeması: proje Alembic KULLANMIYOR (bkz. Sorular ve Cevaplar
   S5) — `backend/db.py`'deki `_add_missing_columns` shim'i (Saga #284)
   yeni nullable kolonu otomatik ekliyor, ek migration kodu YAZILMIYOR.

## Davranış Sözleşmesi (Behavior Contract)

| Senaryo | Girdi | Beklenen Çıktı |
|---|---|---|
| Normal revert | `POST /revert`, body boş/`allowedRoot` yok, transaction `committed`, `allowed_root` DB'de dolu | 200, `revert_transaction` transaction'ın kendi `allowed_root`'unu kullanır, dosyalar geri alınır |
| Spoofed allowedRoot (regresyon testi) | Eski davranışta olsaydı `allowedRoot: "C:\\"` gönderilirdi — YENİ davranışta bu alan artık şemada YOK, gönderilse bile Pydantic tarafından yok sayılır/reddedilir (extra field) | Containment kontrolü GERÇEK stored `allowed_root` ile yapılır, istemci girdisi güvenlik kararını ETKİLEMEZ |
| `allowed_root` NULL olan eski transaction | `committed` durumunda ama `allowed_root IS NULL` (migration öncesi kayıt) | `revert_transaction` (veya endpoint) `TransactionRevertError`/400 ile net biçimde reddeder, `None` ile `is_path_allowed`'a düşüp patlamaz |
| Transaction `pending` durumda | `POST /revert` | 409 (mevcut davranış korunur, değişmez) |
| Transaction bulunamadı | `POST /revert`, olmayan id | 404 (mevcut davranış korunur) |

## Sorular ve Cevaplar
S1: `revert_transaction`in imzasından `allowed_root` parametresi tamamen mi
kaldırılsın, yoksa opsiyonel savunma-derinliği çapraz kontrol mü kalsın?
C1: Tamamen kaldır (parametresiz, `transaction.allowed_root` kullan) — task
açıklaması "prefer ignoring the client value as primary source of truth"
diyor ve kodda zaten `Transaction` nesnesinin kendisi `revert_transaction`e
geçiriliyor, `allowed_root`u ayrıca parametre olarak taşımak gereksiz
duplikasyon. (saga-oto tarafından otomatik seçildi)

S2: `allowed_root` NULL olan eski kayıtlar nasıl ele alınsın?
C2: `revert_transaction` `transaction.allowed_root is None` ise
`TransactionRevertError` fırlatır (var olan hata tipini yeniden kullan) —
endpoint bunu mevcut except bloğuyla 200+`revert_failed` yerine net bir 409
"allowed_root eksik" hatasına çevirir. Dar kapsam: gerçek veri geçişi
(backfill) YOK, sadece güvenli-başarısızlık. (saga-oto tarafından otomatik
seçildi)

S3: `RevertTransactionRequest` boş body mi bekleyecek yoksa endpoint body
parametresi tamamen mi kaldırılsın?
C3: `RevertTransactionRequest` boş bir Pydantic model olarak kalsın (gelecekte
başka bir alan eklenebilir ihtimaline karşı, ve mevcut FastAPI route imzasını
minimal değiştirmek için) — `allowedRoot` alanı ve `field_validator`'ı
silinir. (saga-oto tarafından otomatik seçildi)

S4: `ResultCard`'ın `selectedFolder` prop'u component'ten tamamen mi
kaldırılsın?
C4: Hayır — sadece revert `fetch` body'sinden `allowedRoot` gönderimi
kaldırılır. `selectedFolder`, `canShowRevert` gate'inde hâlâ kullanılabilir
(task "call'a artık gerekli değil" diyor, component'in tamamen prop'u
atması istenmiyor); ama gate mantığı da sadeleştirilip sadece
`transactionId`'ye bakacak şekilde güncellenir çünkü artık backend'e hiçbir
şekilde `selectedFolder` gönderilmiyor ve "ikisi de yoksa buton gösterme"
mantığının güvenlik gerekçesi ortadan kalktı — DAR kapsam ilkesiyle: sadece
`transactionId` kontrolü yeterli hale getirilir, `selectedFolder` prop'u
TİPTE kalır ama artık zorunlu-varlık kontrolüne dahil edilmez. (saga-oto
tarafından otomatik seçildi)

S5: Proje Alembic kullanıyor mu?
C5: Hayır. `backend/db.py::_add_missing_columns` (Saga #284) adlı minimal bir
shim var — `create_all` sonrası eksik nullable/default'lu kolonları `ALTER
TABLE ADD COLUMN` ile ekliyor. Yeni `allowed_root` kolonu `nullable=True`
olarak eklenirse (eski kayıtlar için NULL, S2 ile tutarlı) bu shim ek kod
gerektirmeden otomatik halleder. (saga-oto tarafından otomatik seçildi)

## Riskler / Varsayımlar / Bilinmeyenler
- Varsayım: `apply_plan` şu an hiçbir HTTP endpoint'e bağlı değil (main.py'de
  çağrılmıyor, sadece testlerde) — bu yüzden `allowed_root` kolonu
  doldurulsa da prod'da henüz gerçek kullanıcı transaction'ı YOK, geriye
  dönük veri sorunu risk teşkil etmiyor.
- Risk: `RevertTransactionRequest`'in boş model haline gelmesi, FastAPI'nin
  POST body'sini opsiyonel/boş obje olarak kabul etmesini gerektirir —
  frontend'in hiç body göndermemesi de (`{}` veya body yok) çalışmalı;
  test bunu doğrulayacak.
- Kapsam dışı: eski transaction'lar için `allowed_root` backfill migration'ı
  YOK (S2'de net biçimde ele alınmadığı belirtildi, sadece güvenli
  başarısızlık sağlanıyor).

## Test Stratejisi
- Unit: `backend/tests/test_orchestrator.py` içine yeni testler — (a)
  `apply_plan` sonrası `transaction.allowed_root` doğru dolu, (b)
  `revert_transaction` artık `allowed_root` parametresi almıyor (imza
  testi/çağrı testi), (c) `allowed_root is None` olan transaction'da
  `TransactionRevertError`.
- Integration: `backend/tests/test_main_integration.py` içine — (a) revert
  endpoint'i artık `allowedRoot` olmadan çalışıyor, (b) eski davranışta
  spoofed geniş `allowedRoot` gönderilse bile (extra field olarak, Pydantic
  ignore/forbid davranışına göre) gerçek kısıtlama transaction'ın kendi
  kökünden geliyor.
- Frontend: `ResultCard.test.tsx` içindeki revert testi güncellenir — fetch
  body'sinde `allowedRoot` OLMADIĞI doğrulanır.

## Benchmark
n/a — performans hedefi yok, saf davranış/güvenlik değişikliği.
