# Plan — zip-temel-operasyonlar
_Reference: atdd.md_

## Unknowns'ın Çözümü (kod incelemesiyle netleşti)

**`destinationFolder`/`targetFolder` ilişkisi:** `targetFolder` YYYY-MM
regex'ine kilitli (`TARGET_FOLDER_PATTERN`, models.py) ve DELETE/RENAME/
MERGE'de zaten "şema gereği zorunlu ama kullanılmıyor" bilinen bir sınırlama
(orchestrator.py satır ~856-861 yorumu). ZIP_EXTRACT de AYNI deseni izler:
`targetFolder` yine zorunlu ama KULLANILMAZ, YENİ ve AYRI bir
`destinationFolder: str` alanı serbest-formatlı hedef klasör adını taşır
(path-separator validator'ı OLACAK ama YYYY-MM kısıtı OLMAYACAK).

**ZIP_EXTRACT rollback modeli:** `_rollback_copy`, `destination_path.unlink()`
çağırıyor — bu bir DOSYA için çalışır, ZIP_EXTRACT'in hedefi bir KLASÖR
(potansiyel olarak çok sayıda dosya) olduğu için DOĞRUDAN kullanılamaz.
Çözüm: DELETE'in "bazı işlemler gerçek anlamda tam geri alınamaz" ilkesi
izlenir — `destinationFolder`'ın işlem ÖNCESİNDE var olup olmadığı
kaydedilir (`record_file_operation`'ın `backup_path` alanına "existed"/
"created" gibi bir işaret KONULMAZ, bunun yerine YENİ bir `_rollback_zip_extract`
fonksiyonu yazılır): klasör orchestrator TARAFINDAN oluşturulduysa
(`mkdir` öncesi `exists()` kontrolüyle tespit edilir) rollback TÜM klasörü
(`shutil.rmtree`) siler; klasör ÖNCEDEN VARDIYSA (AC-8'in üzerine-yazma
senaryosu) rollback NO-OP'tur (var olan içerik geri alınamaz, DELETE'in
"gerçek anlamda geri dönüşsüz" sınıfıyla AYNI, kullanıcıya AÇIKÇA
belgelenmeli).

**`filesToAdd` tekil/çoğul kapsamı:** ÇOĞUL — `list[str]` (mevcut
`fileNames` deseniyle aynı tip), tek çağrıda birden fazla dosya eklenebilir.
Bu, projenin GENELİNDE "dosya listesi" için tek bir tip kullanma
konvansiyonuyla (fileNames, newFileNames) tutarlı.

**Zip-slip koruması mimarisi (BULUNDU, atdd.md'de "code-copilot'a talimat"
olarak bırakılmıştı):** `backend/security.py`'deki `_validate_single_path`
(zaten `resolve()`+`is_relative_to()` yapıyor) DOĞRUDAN yeniden
kullanılabilir — ZIP_EXTRACT'in zip-slip taramasında, HER `zipinfo.filename`
için `destinationFolder / entry_name` hesaplanıp `_validate_single_path`'e
geçirilir. Yeni bir güvenlik algoritması YAZILMAYACAK, mevcut whitelist
mekanizması yeniden kullanılacak.

## Files to Modify
| File | Why | Risk |
|------|-----|------|
| backend/models.py | 4 yeni `OperationType` (ZIP_CREATE/ZIP_ADD/ZIP_EXTRACT/ZIP_MERGE); `PlanStep`e `zippedFileName`, `destinationFolder`, `filesToAdd: list[str]`, `addedFileName`, `mergedZipFileName`; ilgili validator'lar (MERGE'in ">=2" deseni ZIP_MERGE için, EXCEL_FILTER'ın "==1" deseni ZIP_ADD/ZIP_EXTRACT için, MERGE'in kendisi ZIP_CREATE için — fileNames>=1, ZIP_CREATE'de MERGE'in ">=2" ZORUNLULUĞU YOK, tek dosyayı zip'lemek de geçerli); YENİ `ZipListRequest`/`ZipListResponse` şemaları | medium — 4 yeni operationType, en büyük tek-görev şema genişlemesi |
| backend/orchestrator.py | `from backend import zip_ops` import; `_SUPPORTED_OPERATION_TYPES`, `_ROLLBACK_OPERATIONS` (`ZIP_CREATE/ZIP_ADD/ZIP_MERGE: _rollback_copy`, `ZIP_EXTRACT: _rollback_zip_extract` — YENİ fonksiyon), hedef-klasör-oluşturma hariç-tutma listesi (ZIP_EXTRACT KENDİ `destinationFolder`'ını kullanacağı için `targetFolder`'dan oluşturulan klasöre GİRMEMELİ); 4 yeni step-uygulama bloğu | medium — ZIP_EXTRACT'in "klasör önceden var mıydı" izleme mantığı yeni bir desen |
| backend/main.py | YENİ `POST /api/zip/list` endpoint'i, `search_endpoint`/`/api/excel/read` deseniyle AYNI | low |
| backend/security.py | DEĞİŞİKLİK GEREKMİYOR — `_validate_single_path` zaten var, zip-slip taramasında import edilip DOĞRUDAN kullanılacak | low |

## New Files
| File | Purpose |
|------|---------|
| backend/zip_ops.py | `create_zip(source_paths: list[Path], destination_path: Path) -> None` (MERGE'in N->1 deseni), `add_to_zip(source_path: Path, files_to_add: list[Path], destination_path: Path) -> None` (kaynak zip + yeni dosyalar -> YENİ zip), `extract_zip(source_path: Path, destination_folder: Path, allowed_root: Path) -> None` (zip-slip taraması için `allowed_root` parametresi ALIR — `_validate_single_path` çağrısı için gerekli, `security.py`'den import), `merge_zips(source_paths: list[Path], destination_path: Path) -> None` (N zip -> 1 zip, TÜM girişler), `list_zip_entries(source_path: Path) -> list[dict]` (salt okunur) |
| backend/tests/test_zip_ops.py | Her 5 fonksiyon için unit testler — ÖZELLİKLE zip-slip taraması için 3 farklı kaçış tekniği (`../`, mutlak Windows path, sürücü harfi değişimi) |

## Dependencies
- `zipfile` (Python stdlib) — yeni pip bağımlılığı YOK.
- `_validate_single_path`/`is_path_allowed` (backend/security.py) — zip-slip
  taraması için DOĞRUDAN yeniden kullanılacak.
- `_rollback_copy` — ZIP_CREATE/ZIP_ADD/ZIP_MERGE için değişiklik gerekmiyor.
- `record_file_operation` — mevcut imzayla çağrılacak.

## Migration Required?
No — DB şeması dokunulmuyor.

## Risks
- (atdd.md'den taşındı, ÇÖZÜLDÜ) `destinationFolder`/`targetFolder`
  ilişkisi netleşti.
- (atdd.md'den taşındı, ÇÖZÜLDÜ) ZIP_EXTRACT rollback modeli netleşti —
  "klasör orchestrator tarafından mı oluşturuldu" izlemesi code-copilot'ta
  dikkatli implemente edilmeli (`destination_folder.exists()` kontrolü
  `mkdir`'DAN ÖNCE yapılmalı, sırası kritik).
- Zip-slip taramasının `zipfile.ZipInfo.filename`'in TÜM olası kaçış
  biçimlerini (POSIX `../`, Windows mutlak path `C:\...`, UNC path
  `\\server\...`) kapsadığından code-copilot'ta EMİN OLUNMALI — testler
  bu üç senaryoyu da AÇIKÇA hedeflemeli.
- En büyük tek-görev kapsamı bu oturumda (4 Plan operasyonu + 1 endpoint)
  — code-copilot'a görevi TEK bir dev subagent çağrısında mı yoksa
  operasyon-başına mı böleceği konusunda esneklik bırakılmalı (CAVEMAN
  ilkesiyle çelişmez, sadece pratik bir uygulama detayı).

## Open Questions
Yok — atdd.md'nin üç Unknown'ı da bu planla kod incelemesiyle çözüldü.
