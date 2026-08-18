---
task_slug: pdf-redact
saga_task_id: 320
epic_id: 29
priority: high
coverage_target: "yeni modul + orchestrator wiring icin >=90% satir kapsama"
performance_target: "tek sayfalik rasterize+karart islemi, tipik A4 sayfa icin < 5s (poppler render dahil)"
test_strategy: "pytest, backend/tests/ icinde gercek pypdf ile uretilmis gercek PDF'ler (mock DEGIL) - metnin gercekten cikarilamadigini dogrulamak icin pypdf.PdfReader.extract_text() kullanilir"
affected_modules:
  - backend/models.py
  - backend/orchestrator.py
  - backend/pdf_redact.py (yeni)
  - backend/tests/test_pdf_redact.py (yeni)
  - backend/tests/test_orchestrator.py
---

# PDF Gercek Redaksiyon (KVKK) — ATDD

## Persona

Türkiye'de serbest çalışan bir mali müşavir/muhasebeci veya avukat. Müşteri
sözleşmeleri, banka dekontları, vergi belgeleri gibi PDF'lerde TC kimlik no,
hesap no, vergi no gibi KVKK kapsamındaki kişisel verileri içeren belgeleri
üçüncü bir tarafla (başka bir müşteri, denetim şirketi, mahkeme) paylaşmadan
önce bu alanları GERÇEKTEN kaldırmak istiyor — sadece görsel olarak
gizlemek değil.

## Goal

Kullanıcının (veya LLM planlayıcının) bir PDF üzerinde, sayfa numarası ve
dikdörtgen koordinatlarıyla belirttiği bölge(ler)i, o sayfayı rasterize
edip üzerine opak bir kutu çizerek GERÇEKTEN karartan; orijinal metin
katmanının o sayfada tamamen yok olduğu (kopyalanamaz/aranamaz) yeni bir
çıktı PDF'i üreten bir REDACT operasyonu eklemek.

## User Story

Bir mali müşavir olarak, PDF'imdeki hangi sayfada hangi bölgenin (ör. TC
kimlik no'nun yazılı olduğu alan) karartılacağını belirtebilmek istiyorum,
öyle ki çıktı dosyasını paylaştığımda o bilginin metin olarak
kopyalanamayacağından/arama ile bulunamayacağından emin olayım — sahte bir
"siyah kutu çizip metni öylece bırakan" bir çözüm KVKK açısından beni
riske atar.

## Prioritized Acceptance Criteria

1. (P0) `OperationType.REDACT` yeni bir plan operasyonu olarak eklenir,
   `PlanStep` bunun için bölge listesi (`redactionRegions`) ve çıktı dosya
   adı (`redactedFileName`) alanlarını taşır.
2. (P0) Redaksiyon sonrası çıktı PDF'inde, karartılan sayfanın metninden
   (pypdf `extract_text()`) orijinal metin ÇIKARILAMAZ — görsel olarak
   kapatmak YETMEZ, metin katmanı o sayfada FİZİKSEL OLARAK YOK olmalı
   (sayfa rasterize edilip resim olarak gömülür).
3. (P0) Karartılmayan diğer sayfalar DOKUNULMAMIŞ, vektör ve
   arama/kopyalanabilir kalır (sadece belirtilen sayfa(lar) rasterize
   edilir).
4. (P0) Kaynak dosyaya HİÇ dokunulmaz (merge/split ile aynı ilke) — çıktı
   ayrı bir `redactedFileName` dosyasına yazılır.
5. (P0) Path validasyonu MERGE/SPLIT/OCR ile AYNI merkezi mekanizma
   (`backend/security.py`'nin `validate_plan_paths`/`is_path_allowed`)
   üzerinden `orchestrator.py` içinde yapılır — `pdf_redact.py` modülünün
   KENDİSİ hiçbir path/whitelist mantığı içermez.
6. (P1) Sonuç kullanıcıya, çıktı dosyasının büyüdüğü VE karartılan
   sayfa(lar)ın artık aranamaz/kopyalanamaz olduğu konusunda bir uyarı
   alanıyla (`warning`) açıkça bildirilir — bu davranış GİZLENMEZ,
   dokümante edilir.
7. (P2) Bölge sınırları sayfa sınırlarını aşarsa (x1>sayfa genişliği vb.)
   veya negatifse şema/validasyon seviyesinde reddedilir.
8. (P2) Sayfa numarası PDF'in gerçek sayfa sayısını aşarsa çalışma
   zamanında `PlanApplicationError` fırlatılır.
9. (P2) Hiç bölge belirtilmemişse (`redactionRegions` boş liste) şema
   seviyesinde reddedilir — "redaksiyon" adı altında hiçbir şey
   yapmayan sessiz bir no-op'a izin verilmez.

## Behavior Contract Table

| Girdi / Durum | Beklenen Sonuç |
|---|---|
| Geçerli 1+ bölge, geçerli sayfa numarası, `allowed_root` içinde kaynak | REDACT başarılı; çıktı dosyası oluşur, boyutu kaynaktan BÜYÜK (rasterize edilen sayfa nedeniyle); yanıt `warning` alanında "bu sayfa artık aranamaz/kopyalanamaz" uyarısı taşır |
| `redactionRegions` boş liste | Şema/model_validator seviyesinde `ValidationError` — plan hiç oluşturulmaz |
| Bölge `page` PDF'in gerçek sayfa sayısını aşıyor (ör. 5 sayfalık PDF'te page=10) | `PlanApplicationError`, hiçbir dosya yazılmaz/değiştirilmez |
| Bölge koordinatları sayfa sınırları dışında (negatif veya x1<=x0/y1<=y0 veya sayfa boyutunu aşan) | Model seviyesinde (negatif/x1<=x0) veya çalışma zamanında (sayfa boyutu bilinmeden önce) reddedilir; hiçbir dosya yazılmaz |
| Kaynak dosya `allowed_root` dışında (ör. `..`) | `PathWhitelistError`, redaksiyon fonksiyonu HİÇ çağrılmaz (MERGE/SPLIT/OCR ile aynı davranış) |
| `redactedFileName` bir kaynak `fileNames` girdisiyle çakışıyor | Model seviyesinde reddedilir (MERGE'in `mergedFileName` çakışma kontrolüyle aynı desen) |
| `redactedFileName` planın bilmediği, diskte zaten var olan bir dosyayla çakışıyor | `PathWhitelistError` (MERGE'in `validate_merge_destinations` desenine benzer bir `validate_redact_destinations`) |
| Redaksiyon sonrası karartılan sayfa | `PdfReader.pages[i].extract_text()` orijinal hassas metni İÇERMEZ; diğer sayfalar İÇERİR (değişmemiş) |
| Yazma sırasında hata (disk dolu vb.) | Geçici dosya + atomik `Path.replace` deseni (merge/split ile aynı) — `redactedFileName` hedefinde YARIM/BOZUK dosya kalmaz |

## Risks / Assumptions / Unknowns

- (saga-oto tarafından otomatik seçildi) Bu görev OTOMATİK PII tespiti
  (ör. TC kimlik no'yu OCR/regex ile kendiliğinden bulup önerme) YAPMAZ —
  kullanıcı veya LLM planlayıcı, karartılacak bölgeyi (sayfa + koordinat)
  AÇIKÇA belirtmelidir. Otomatik tespit kapsam dışıdır, ayrı bir gelecek
  görev olarak (depends_on: [320]) önerilecektir.
- (saga-oto tarafından otomatik seçildi) Koordinat sistemi: PDF nokta
  birimi (pypdf/mediabox ile aynı, sol-alt orijin) yerine rasterize
  edilmiş görüntü piksel koordinatı kullanılacak mı sorusu — PIL/pdf2image
  görüntü piksel koordinatı (sol-üst orijin) seçildi, çünkü redaksiyon
  fiilen rasterize edilmiş görüntü ÜZERİNDE çizilir (ImageDraw), bu da
  DPI'a bağlı bir piksel-alanı olduğu için en doğrudan ve az hataya açık
  yoldur. DPI sabit 200 olarak seçildi (pdf2image varsayılanı 200'e
  yakın, poppler render kalitesi/performans dengesi).
- (saga-oto tarafından otomatik seçildi) `redactedFileName`, MERGE'in
  `mergedFileName` alanıyla AYNI validasyon deseni (path ayracı yok, boş
  değil, kaynaklarla çakışmıyor) kullanır.
- (saga-oto tarafından otomatik seçildi) REDACT tek kaynak dosya kabul
  eder (`fileNames` tam olarak 1 girdi) — birden fazla dosyayı aynı
  step'te karartmak, her dosyanın kendi sayfa sayısı/bölgesi farklı
  olacağı için OCR/SPLIT ile aynı "tek kaynak" kısıtına tabidir.
- Bilinen sınırlama: rasterize edilen sayfa artık bir görüntüdür — PDF
  formu alanları, iç linkler, yer imleri gibi o sayfaya özgü etkileşimli
  öğeler de kaybolur (sadece görsel içerik korunur). Bu KASITLIDIR ve
  metnin kaybolmasıyla aynı "tradeoff" kategorisindedir.
