# ATDD — Format Agent Parametre Güvenlik Katmanı (Saga #319)

## Bağlam
`referans/windows-ai-files-eski` projesinde tekrarlayan bir bug sınıfı
gözlendi: şema bir parametre adı bildiriyordu (örn. kırpma için "box"),
ama gerçek `execute` fonksiyonu FARKLI bir isim okuyordu (left/top/right/
bottom) — alan sessizce yok sayılıyor, işlem YANLIŞ şeyi yapıyordu
(sabit varsayılan kırpma, yanlış döndürme açısı, yanlış zip klasörü) ama
`success: True` raporluyordu.

Bu görev YENİ bir format-agent operasyonu EKLEMİYOR — gelecekte (Saga
#320-#329) Word/Excel/Image/Zip operasyonları `backend/models.py`'nin
`PlanStep`/`OperationType`'ına ve `backend/orchestrator.py`'nin execute
mantığına eklenirken bu bug sınıfını otomatik olarak yakalayacak yapısal
bir güvenlik ağı kurmayı hedefliyor.

## Persona
Bu projeye gelecekte yeni bir operasyon-özel alan (örn. Image için
`cropBox`, Zip için `extractToFolder`) ekleyecek bir katkıcı (insan veya
subagent) — "alanı şemaya ekledim, validator'lar geçti, test yazdım" ama
orchestrator'ın o alanı GERÇEKTEN okuyup kullandığını unutabilir.

## Hedef
Her operasyon-özel `PlanStep` alanının (sadece belirli `operationType`
değerleri için anlamlı olan) orchestrator tarafında GERÇEKTEN okunduğunu
ve çıktıyı etkilediğini kanıtlayan, dökümante edilmiş bir konvansiyon +
somut örnek testler.

## Keşif bulguları (mevcut kod durumu)

### PlanStep operasyon-özel alanları (backend/models.py)
- `newFileNames: list[str] | None` — SADECE `RENAME` için zorunlu
  (`new_file_names_only_for_rename` model_validator, satır 134-170).
- `mergedFileName: str | None` — SADECE `MERGE` için zorunlu
  (`merged_file_name_only_for_merge` model_validator, satır 172-204).

Her ikisi de "sadece X operationType'ında dolu olabilir, diğerlerinde
None kalmalı" desenini validator seviyesinde ZATEN uyguluyor — şema
tarafı sağlam.

### orchestrator.py'de gerçek kullanım
- `newFileNames`: satır 503-506'da `dict(zip(step.fileNames,
  step.newFileNames))` ile RENAME hedef path'i hesaplanıyor
  (`destination_path`, satır 514 civarı) — GERÇEKTEN okunuyor.
- `mergedFileName`: satır 429'da `destination_path = allowed_root /
  step.mergedFileName` — GERÇEKTEN okunuyor (MERGE'in çıktı dosya adı
  doğrudan bu alandan geliyor).

**Sonuç: iki mevcut operasyon-özel alan da (newFileNames, mergedFileName)
gerçekten wire edilmiş durumda — eskiden bahsedilen "şema alanı var ama
kod okumuyor" bug sınıfının bir örneği BU PROJEDE şu an YOK.**

### Mevcut testlerin "alan değişince çıktı değişir" özelliğini kapsayıp kapsamadığı
`backend/tests/test_orchestrator.py`:
- `test_apply_plan_renames_a_file_in_place` (satır 477): `newFileNames=
  ["yeni.pdf"]` verilip `(tmp_path / "yeni.pdf").exists()` assert
  ediliyor. Bu DOLAYLI olarak alanın wiring'ini kanıtlıyor (kod bu alanı
  yoksayıp sabit bir isim kullansaydı test kırılırdı) ama İKİ FARKLI
  değerle karşılaştırma yapmıyor.
- `test_apply_plan_merges_real_pdfs_into_one_file_with_the_correct_total_page_count`
  (satır 572): `mergedFileName="birlesik.pdf"` verilip
  `(tmp_path / "birlesik.pdf").exists()` assert ediliyor — aynı desen.

**Bulgu: mevcut testler alanın wiring'ini isim bazında zaten kanıtlıyor
(field value → literally o isimde dosya oluşuyor), ama konvansiyonu
netleştirecek AÇIK bir "değeri değiştir, çıktının da değiştiğini gör"
testi (iki farklı değerle iki farklı sonuç, aynı testte) YOK.** Bu, bu
görevin dolduracağı somut boşluk.

## Soru ve Cevaplar (saga-oto tarafından otomatik seçildi)

**S1: Statik-analiz / AST tabanlı bir "her PlanStep alanı orchestrator'da
okunuyor mu" kontrolü mü kurulmalı, yoksa dökümante edilmiş konvansiyon +
örnek testler mi?**
Cevap: Dökümante edilmiş konvansiyon + örnek testler. AST/statik analiz
disproportionate karmaşıklık getirir (task kapsamı "orantılı kal" diyor)
ve yanlış pozitif/negatif riski yüksektir (örn. bir alan helper
fonksiyon üzerinden dolaylı okunabilir, AST bunu kaçırabilir).
(saga-oto tarafından otomatik seçildi)

**S2: Yeni test dosyası mı, mevcut `test_orchestrator.py`'ye eklenen
testler mi?**
Cevap: Mevcut `test_orchestrator.py`'ye eklenen 2 yeni test (RENAME ve
MERGE için, "alanı değiştir → farklı somut çıktı" deseninde) —
projede zaten operasyon bazlı test grupları bu dosyada, yeni bir dosya
gereksiz parçalanma yaratır. (saga-oto tarafından otomatik seçildi)

**S3: Konvansiyon dokümanı nereye yazılmalı?**
Cevap: `docs/DESIGN_DECISIONS.md`'ye yeni bir bölüm ("Operasyon-özel
PlanStep alanları için test konvansiyonu") — proje zaten mimari
kararları bu dosyada topluyor, yeni bir CONTRIBUTING.md dosyası
gereksiz. (saga-oto tarafından otomatik seçildi)

**S4: Gerçek bir kod boşluğu (şemada var ama okunmuyor) bulunursa ne
yapılacaktı?**
Cevap: Keşif sonucu böyle bir boşluk BULUNMADI (hem newFileNames hem
mergedFileName gerçekten okunuyor) — bu yüzden kod/orchestrator
değişikliği gerekmiyor, sadece test+doküman eklemesi yapılacak.
(saga-oto tarafından otomatik seçildi)

## Kabul Kriterleri
1. `docs/DESIGN_DECISIONS.md`'de yeni bir bölüm, gelecekte eklenecek her
   operasyon-özel `PlanStep` alanı için ZORUNLU test konvansiyonunu
   tanımlar: "alanın iki farklı değeriyle iki farklı somut fiziksel
   çıktı (dosya adı/yolu/sayfa sayısı/içerik) gözlenmeli" + "None/eksik
   olduğunda hangi operationType'larda reddedilmesi gerektiği model
   seviyesinde test edilmeli".
2. `backend/tests/test_orchestrator.py`'ye RENAME için `newFileNames`
   değerini değiştirdiğinde (örn. iki farklı plan, iki farklı hedef
   dosya adı) çıktının GERÇEKTEN değiştiğini kanıtlayan bir test eklenir.
3. Aynı desen `mergedFileName` için MERGE'e eklenir.
4. Testler gerçek pytest ile YEŞİL olmalı; yeni bir orchestrator/model
   değişikliği gerekmiyor (mevcut wiring zaten doğru).
5. Konvansiyon dokümanı, gelecekteki Saga #320-#329 (Word/Excel/Image/
   Zip) task'larının atdd.md'lerine referans verebileceği kısa, tekrar
   kullanılabilir bir kontrol listesi içerir.

## Davranış Sözleşmesi (behaviour-contract)
| Senaryo | Beklenen |
|---|---|
| `newFileNames=["a2.pdf"]` vs `newFileNames=["a3.pdf"]` (aynı fileNames, farklı plan) | Farklı hedef dosya adı diskte oluşur |
| `mergedFileName="x.pdf"` vs `mergedFileName="y.pdf"` (aynı kaynaklar, farklı plan) | Farklı hedef dosya adı diskte oluşur |
| `newFileNames=None` + `operationType=RENAME` | Pydantic `ValidationError` (mevcut davranış, değişmiyor) |
| `mergedFileName=None` + `operationType=MERGE` | Pydantic `ValidationError` (mevcut davranış, değişmiyor) |

## Riskler / Varsayımlar
- Varsayım: Gelecekteki format-agent alanları da bu projede PlanStep
  şemasına eklenecek (referans projedeki gibi ayrı bir sınıf hiyerarşisi
  değil) — bu yüzden konvansiyon PlanStep'e özel yazıldı.
- Risk: Statik-analiz olmadığı için, bir katkıcı konvansiyonu
  UYGULAMAZSA (yeni testi yazmazsa) hiçbir otomatik gate bunu
  yakalamaz — bu bilinçli bir trade-off (görev kapsamı "orantılı kal,
  elaborate static-analysis kurma" diyor). Gelecekte code-review/
  red-team adımı bu konvansiyona uyumu kontrol etmeli (red-team
  checklist'ine not düşülecek).

## Test Stratejisi
100% unit (orchestrator seviyesinde, gerçek dosya sistemi + gerçek PDF,
mock yok) — mevcut test dosyasının deseniyle aynı.
