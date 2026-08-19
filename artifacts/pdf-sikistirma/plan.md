# Plan — pdf-sikistirma
_Reference: atdd.md_

## Unknowns'ın Çözümü (kod incelemesiyle netleşti)

**"Büyüme koruması" durumunun kullanıcıya iletilme mekanizması:**
`OperationType.LIST` zaten bir örnek: bazı operasyon tipleri
`FileOperation` kaydı OLUŞTURMADAN `apply_plan` içinde `continue` ile
atlanabiliyor (orchestrator.py:605-606). PDF_COMPRESS'in "sıkışma
sağlanamadı" durumu bu deseni AYNEN kullanacak — **yeni bir status
string/DB alanı İCAT EDİLMEYECEK**:
- `compress_pdf()` `True`/`False` döner (sıkıştı/sıkışmadı).
- `True` ise: normal `record_file_operation` + `status="completed"` +
  `applied.append(...)` (diğer tüm operasyonlarla AYNI desen).
- `False` ise: HİÇBİR `FileOperation` kaydı oluşturulmaz, sadece
  `continue` (LIST'in izlediği desen) — rollback mantığına (satır 492,
  884) hiç dokunmaz çünkü ortada geri alınacak bir şey yok.
- `backend/main.py`'nin `apply_plan_endpoint`'i (satır 462-467), REDACT
  için ZATEN statik bir `warnings` listesi üretiyor
  (`payload.plan.steps` üzerinden). PDF_COMPRESS için AYNI listeye,
  ama DİNAMİK bir kontrolle (`transaction.operations` içinde bu step'in
  `compressedFileName`'ine karşılık gelen bir `completed` kaydı VAR MI)
  yeni bir branch eklenir — kayıt YOKSA büyüme koruması tetiklenmiş
  demektir, uyarı eklenir.

**Yeni modül gerekip gerekmediği:** Evet — `backend/pdf_compress.py`,
`pdf_pages.py`/`pdf_redact.py` ile aynı ayrım deseni (PDF-özel iş mantığı
orchestrator'dan ayrı, test edilebilir bir modülde).

## Files to Modify
| File | Why | Risk |
|------|-----|------|
| backend/models.py | `OperationType.PDF_COMPRESS` enum değeri (EXCEL_FILTER/PDF_DELETE_PAGES'in hemen ardına); `PlanStep`e `compressedFileName: str \| None` alanı + path-separator validator + `pdf_compress_fields_only_for_pdf_compress` model_validator (EXCEL_FILTER'daki `filteredFileName` deseninin BİREBİR kopyası, fileNames==1, kaynakla çakışmaz) | low — mevcut desenin kopyası |
| backend/orchestrator.py | `from backend import pdf_compress` import; `_SUPPORTED_OPERATION_TYPES`e ekle; `_ROLLBACK_OPERATIONS`e `PDF_COMPRESS: _rollback_copy` (SADECE dosya yazıldığında devreye girer, `False` durumunda zaten `FileOperation` kaydı yok, rollback haritasına hiç bakılmaz — bu güvenli); hedef-klasör-oluşturma hariç-tutma listesine ekle; yeni step-uygulama bloğu — `compress_pdf()` `True` dönerse EXCEL_FILTER bloğunun (record+completed+append) kopyası, `False` dönerse `continue` (LIST deseni) | medium — LIST'in "kayıtsız continue" deseni ile EXCEL_FILTER'ın "kayıtlı completed" deseni TEK bir operationType içinde koşullu birleştiriliyor, ilk kez |
| backend/main.py | `apply_plan_endpoint`'teki `warnings` listesi oluşturma bloğuna (satır 462-467) PDF_COMPRESS için ikinci bir list comprehension eklenir: `payload.plan.steps`'te PDF_COMPRESS olan her step için, `transaction.operations` içinde `destination_path == str(allowed_root / step.compressedFileName)` olan bir `completed` kayıt YOKSA uyarı metni eklenir | low — mevcut REDACT deseninin yanına ikinci bir branch |

## New Files
| File | Purpose |
|------|---------|
| backend/pdf_compress.py | `compress_pdf(source_path: Path, destination_path: Path) -> bool` — **API doğrulandı (plan aşamasında gerçek pypdf 6.15.0 kurulumuyla test edildi):** `compress_content_streams()` bir `PdfWriter` metodu DEĞİL, her `PageObject`'in kendi metodu (`page.compress_content_streams(level=-1)`, sayfa sayfa çağrılır); ayrıca `PdfWriter.compress_identical_objects(remove_duplicates=True, remove_unreferenced=True)` writer-genelinde yinelenen nesneleri kaldırır. `compress_pdf`, tüm sayfalarda `compress_content_streams()` + writer'da `compress_identical_objects()` çağırıp geçici bir dosyaya yazar, boyutunu kaynakla karşılaştırır: sonuç boyutu >= kaynak boyutu ise `destination_path`'e HİÇBİR ŞEY YAZMADAN (geçici dosya silinir) `False` döner (büyüme koruması), küçültme sağlanırsa geçici dosya `destination_path`'e atomik `replace` ile taşınıp `True` döner. Kaynak açılamıyorsa (`PdfReadError`/vb.) exception fırlatır (yakalanmaz, orchestrator `PlanApplicationError`'a çevirir). |
| backend/tests/test_pdf_compress.py | `compress_pdf` unit testleri — test_pdf_pages.py ile aynı desen |

## Dependencies
- `pypdf.PdfReader`/`PdfWriter` + `PageObject.compress_content_streams()` (sayfa-bazlı) + `PdfWriter.compress_identical_objects()` (writer-bazlı) — ikisi de gerçek pypdf 6.15.0 kurulumunda `dir()`/`inspect.signature()` ile DOĞRULANDI (plan aşamasında, bkz. yukarıdaki Files to Modify notu).
- `_rollback_copy` (orchestrator.py:305) — değişiklik gerekmiyor.
- `os.path.getsize` veya `Path.stat().st_size` — boyut karşılaştırması için (yeni bağımlılık değil, stdlib).
- `record_file_operation(...)` — sadece `True` dönüşünde çağrılır.

## Migration Required?
No — DB şeması dokunulmuyor (operationType string olarak tutuluyor, önceki
görevlerle aynı gerekçe). Yeni bir `FileOperation.status` değeri de
İCAT EDİLMEDİĞİ için (LIST'in "kayıtsız" deseni kullanıldığı için) DB
şemasında hiçbir değişiklik yok.

## Risks
- (atdd.md'den taşındı) pypdf-native sıkıştırmanın gerçek oranı düşük
  olabilir — AC-2/AC-5 (büyüme koruması) beklenenden sık tetiklenebilir,
  bu bir bug değil bilinçli kapsam sınırlamasının sonucu.
- (ÇÖZÜLDÜ) pypdf API'sinin tam şekli plan aşamasında doğrulandı — artık
  bir risk değil.
- main.py'deki warnings-oluşturma değişikliği, PDF_COMPRESS için
  `transaction.operations` listesini `destination_path` string
  karşılaştırmasıyla taraması gerektiriyor — `allowed_root` normalizasyonu
  (ör. `str(Path(...))` platform-bağımlı ayraç farkı) code-copilot'ta
  dikkatli ele alınmalı, aksi halde uyarı YANLIŞLIKLA her zaman tetiklenir
  (gerçek eşleşme olsa bile string karşılaştırması başarısız olursa).

## Open Questions
Yok — atdd.md'nin iki Unknown'ı da (mekanizma + yeni modül) bu planla
kod incelemesiyle somut bir tasarıma bağlandı.
