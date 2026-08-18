# Verify Report — PDF Birleştirme (MERGE) Operasyonu (Saga #304)

## Test Sonuçları
Subagent'ın red→green raporu: red fazında 14 yeni test `AttributeError:
MERGE` ile başarısız (enum üyesi henüz yoktu), 159 mevcut test
etkilenmeden geçti. Green fazında: `173 passed`.

**Ana akış tarafından BAĞIMSIZ doğrulama:**
`pytest backend/tests -q` → **173/173 PASSED** (kendi çalıştırmam,
subagent'ın raporuna güvenmedim).

## Kabul Kriterleri Durumu
- AC-1 (kritik): ✅ `apply_plan`, MERGE step'ini işleyip gerçek pypdf
  dosyalarıyla doğru sayfa sayısına sahip bir birleşik dosya üretiyor.
- AC-2 (kritik): ✅ Rollback sadece birleşik dosyayı siliyor (COPY
  semantiği), kaynaklara dokunmuyor.
- AC-3 (yüksek): ✅ `validate_plan_paths` MERGE hedefini whitelist +
  çakışma/zincir kurallarıyla doğruluyor.
- AC-4 (yüksek): ✅ Şema `mergedFileName`i sadece MERGE için zorunlu
  kılıyor, `fileNames` < 2 reddediliyor.
- AC-5 (orta): ✅ `PLAN_SYSTEM_PROMPT` "Birleştir" eşlemesini içeriyor.
- AC-6 (orta): ✅ Mevcut 159 test değişmeden geçiyor.

## Red-Team Bulgusu ve Düzeltmesi
`obss-red-team` GERÇEK bir HIGH bulgu buldu: `mergedFileName`, AYNI
step'teki bir `fileNames` girdisiyle çakışabiliyordu (ör.
`fileNames=["a.pdf","b.pdf"], mergedFileName="a.pdf"`) — RENAME'in
zaten test edilmiş self-overlap koruması MERGE'e HİÇ taşınmamıştı.
`_forward_merge` kaynak dosyayı hem okuyup hem AYNI path'e yazmak
zorunda kalırdı, kaynak içeriğini bozabilirdi — "kaynaklara asla
dokunulmaz" garantisini ihlal ederdi. HEMEN düzeltildi: `models.py`ye
RENAME'in AYNI deseninde (case-insensitive, `os.path.normcase`) bir
çakışma reddi eklendi.

İlişkili düşük-önem bir bulgu da (yazma yarıda kesilirse
`destination_path`'te yarım/bozuk dosya kalması) AYNI turda düzeltildi:
`_forward_merge` artık AYNI klasörde bir geçici dosyaya yazıp
`Path.replace` ile atomik olarak yayınlıyor — başarısız bir yazmadan
sonra gerçek hedefte hiçbir artık dosya kalmıyor.

4 yeni regresyon testi (2 model validasyonu, 2 orchestrator — biri
`PdfWriter.write`i monkeypatch ile başarısız kılıp artık dosya
kalmadığını doğruluyor). 177/177 test yeşil, ana akış tarafından
bağımsız olarak tekrar doğrulandı.

## Sonuç
`ready_to_commit: evet`
