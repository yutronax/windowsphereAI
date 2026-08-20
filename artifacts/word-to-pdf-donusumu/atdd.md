---
task_slug: word-to-pdf-donusumu
jira_id: null
saga_task_id: 339
priority: low
coverage_target: 90
performance_target: "<60s (timeout)"
memory_target: null
test_strategy:
  unit: 70
  integration: 30
  e2e: 0
affected_modules:
  - backend/models.py
  - backend/orchestrator.py
  - backend/security.py
  - backend/tests/test_orchestrator.py
  - backend/tests/test_security.py
---

# ATDD — word-to-pdf-donusumu

## Jira Kaynağı
Jira'ya bağlı değil — yerel görev (Saga #339, epic #29 altında).

## Persona
Format Agent Sistemi'ni kullanan son kullanıcı — "Bu Word dosyasını PDF
yap" gibi bir istek gönderen kişi.

## Hedef (Neden)
Saga #327'nin kapsam dışı bıraktığı "Word→PDF dönüştür" işlevi, LibreOffice
(`soffice`) bu geliştirme ortamında kurulu olmadığı için ertelenmişti.
2026-08-20'de LibreOffice kuruldu (winget ile, kullanıcı onayıyla) ve
gerçek bir `--headless --convert-to pdf` dönüşümü doğrulandı — bu görev
artık aktif olarak ele alınabilir. İki bilinen risk var: (1) kullanıcının
açık bir LibreOffice örneği profil kilidini tutuyorsa `soffice` hiçbir
şey üretmeyebilir ama önceki çalıştırmadan kalan ESKİ PDF sessizce başarı
sayılabilir — dönüşüm öncesi/sonrası mtime+boyut karşılaştırılıp "tazelik"
doğrulanmalı; (2) istenen çıktı adı her zaman `source.stem+".pdf"` değil,
kullanıcının istediği ad olmalı.

## User Story
As a Format Agent Sistemi kullanıcısı
I want bir .docx dosyasını istediğim isimle .pdf'e dönüştürmek
So that Word belgemi PDF olarak paylaşabileyim/arşivleyebileyim

## Acceptance Criteria (Given-When-Then, önceliklendirilmiş)
1. [Critical] Given geçerli bir .docx dosyası ve `WORD_TO_PDF` operasyonu
   (hedef dosya adı kullanıcının istediği isim, `source.stem+".pdf"` DEĞİL
   zorunlu olarak), When plan uygulanır, Then LibreOffice `--headless
   --convert-to pdf` ile dönüştürme çalıştırılır, dönüşüm ÖNCESİ hedef
   dosyanın mtime/varlığı, dönüşüm SONRASI hedef dosyanın mtime+boyutuyla
   karşılaştırılarak "tazelik" doğrulanır, ve dosya kullanıcının istediği
   isimle kaydedilir (LibreOffice'in varsayılan `source.stem+".pdf"`
   davranışına güvenilmez — gerekirse dönüşüm sonrası yeniden adlandırılır).
2. [Critical] Given `soffice` süreci 60 saniye içinde tamamlanmazsa, When
   dönüşüm çalıştırılır, Then süreç sonlandırılır ve `PlanApplicationError`
   fırlatılır — kaynak .docx'e dokunulmaz.
3. [Critical] Given `soffice` çalışır ama hedef PDF dönüşüm ÖNCESİ mtime'ıyla
   AYNI kalır (profil kilidi/başarısız dönüşüm senaryosu — "tazelik"
   doğrulaması başarısız), When bu durum tespit edilir, Then
   `PlanApplicationError` "LibreOffice meşgul olabilir, tekrar deneyin"
   benzeri özel bir mesajla fırlatılır — eski/bayat PDF ASLA başarılı
   sayılmaz.
4. [High] Given kaynak .docx bozuk/açılamaz durumda, When dönüşüm denenir,
   Then `soffice` sıfır/eksik çıktı üretir, bu AC-3'ün tazelik kontrolü
   tarafından zaten yakalanır (ayrı bir "bozuk kaynak" hata dalı YOK —
   kullanıcı onayı, aynı `PlanApplicationError` mesajı gösterilir).
5. [High] Given hedef .pdf adı `allowed_root` içinde planın bilmediği,
   zaten var olan bir dosyayla çakışıyor, When plan doğrulanır, Then
   Saga #338'de kurulan merkezi `validate_destination_collisions`
   mekanizmasıyla TUTARLI şekilde `PathWhitelistError` fırlatılır —
   sessizce üzerine yazma YOK.
6. [Medium] Given hedef .pdf adı `allowed_root` dışına çıkıyor, When plan
   doğrulanır, Then `PathWhitelistError` fırlatılır (Saga #338'in dict-driven
   whitelist mekanizmasına yeni operasyon eklenir).

## Davranış Sözleşmesi (hangi durumda ne döner)
| # | Durum | Dönen değer / durum kodu | Yan etki | Kullanıcı ne görür | AC |
|---|---|---|---|---|---|
| 1 | Happy path: geçerli .docx, LibreOffice başarıyla dönüştürür | `apply_plan` transaction'ı `committed` döner | Hedef .pdf, kullanıcının istediği isimle oluşur; kaynak .docx dokunulmaz | Dönüşüm başarılı, PDF dosyası görünür | AC-1 |
| 2 | Girdi geçersiz: hedef dosya adı boş/eksik | Pydantic `ValidationError` (mevcut model_validator deseniyle tutarlı) | Yok | Plan hiç oluşturulamaz | — (Pydantic seviyesi, ayrı AC gerekmiyor) |
| 3 | Kaynak yok: .docx bulunamıyor/bozuk | `PlanApplicationError` ("dönüşüm başarısız/tazelik doğrulanamadı" mesajı) | Yok, hiçbir dosya değişmez | Genel dönüşüm hatası mesajı | AC-3, AC-4 |
| 4 | Yetkisiz erişim | Uygulanmıyor — tek kullanıcılı masaüstü uygulaması, dosya izinleri OS seviyesinde `soffice`'in kendi hata koduna düşer, AC-3'ün genel hata dalına dahil. | — | — | — |
| 5 | Dış bağımlılık hatası: LibreOffice hiç kurulu değil/`soffice` PATH'te yok | `PlanApplicationError` ("LibreOffice bulunamadı" ayrı, açık mesajla — kullanıcı onayı: bu AYRI bir mesaj olmalı, tazelik hatasıyla karıştırılmamalı) | Yok | "LibreOffice kurulu değil" mesajı | AC-1'in ön-koşulu (implementasyon detayı) |
| 6 | Zaman aşımı: `soffice` 60 saniyede bitmiyor | Süreç sonlandırılır, `PlanApplicationError` | Yok, kaynak dokunulmaz | "Dönüşüm zaman aşımına uğradı" mesajı | AC-2 |
| 7 | **Kısmi başarı**: `soffice` çalıştı ama hedef dosya YENİLENMEDİ (profil kilidi vb.) | `PlanApplicationError` (özel tazelik mesajı) — "kısmi" bir başarı YOK, ya tam tazelik doğrulanır ya reddedilir | Yok — eski/bayat PDF varsa DOKUNULMAZ, yeni dosya asla "başarılı" işaretlenmez | "LibreOffice meşgul olabilir, tekrar deneyin" | AC-3 |
| 8 | **Hiçbir şey yapılamadı ama hata da yok** | Olanaksız — tazelik kontrolü (AC-3) tam olarak bu senaryoyu (soffice sessizce hiçbir şey yapmadı) yakalayıp hata olarak işaretlemek için var; bu kontrol olmadan bu, tam olarak "sessiz başarı" olurdu. | — | — | AC-3 |

Kısmi başarı: 7. satırda tanımlı — tazelik doğrulaması PASS/FAIL ikili bir
kapıdır, "kısmen tazelendi" gibi bir ara durum yok.
Hiçbir şey yapılamadı ama hata da yok: AC-3 tam olarak bunu önlemek için
var — mtime+boyut karşılaştırması olmadan `soffice`'in "exit 0 ama hiçbir
şey değişmedi" davranışı sessiz başarı olarak yanlış yorumlanırdı (bu
görevin varoluş nedeni budur).
Boş sonuç ↔ hata ayrımı: Uygulanmıyor — bu bir dosya dönüştürme
operasyonu, "boş sonuç" kavramı yok (ya PDF üretilir ya hata döner).

## Test Strategy
Unit: 70% — path/whitelist/tazelik-mantığı (mtime+boyut karşılaştırması,
timeout mantığı) `subprocess.run`/`Path.stat` mock'lanarak test edilir.
Integration: 30% — GERÇEK `soffice` ile gerçek bir .docx→.pdf dönüşümü
(LibreOffice artık kurulu, gerçek ikili bağımlılık testi). E2E: 0% —
backend-only operasyon, yeni bir UI eklenmiyor (mevcut plan/onay akışı
kullanılıyor), manuel/tarayıcı e2e gerekmiyor.

## Benchmark / Başarı Ölçütü
Coverage Target: 90% (backend/orchestrator.py'nin yeni WORD_TO_PDF kod
yoluna göre).
Performance Target: dönüşüm 60 saniye içinde tamamlanmalı (timeout).
Diğer ölçülebilir kriterler:
- Gerçek bir .docx dosyası gerçek `soffice` ile dönüştürülüp geçerli bir
  PDF (pypdf ile açılabilir) üretildiği test edilir.
- Tazelik doğrulaması: dönüşüm öncesi/sonrası mtime FARKLI olmalı testi.

## Kapsam Dışı
- Excel/PowerPoint→PDF dönüşümü — bu görev SADECE Word (.docx→.pdf)
  kapsıyor (kullanıcı onayı: `WORD_TO_PDF`, genel `OFFICE_TO_PDF` değil).
- `.exe`/installer paketlemesinin LibreOffice'i bundle etmesi/otomatik
  kurması — bu görev sadece geliştirme ortamında LibreOffice kurulu
  OLDUĞUNU varsayıyor, dağıtım stratejisi ayrı bir konu.
- Kullanıcının manuel/UI üzerinden gerçek bir .docx ile uçtan uca
  denemesi — kabul kriteri sahibi olarak otomatik testler yeterli kabul
  edildi (kullanıcı onayı), backend-only operasyon.
- Retry mekanizması (tazelik başarısız olursa otomatik yeniden deneme) —
  kullanıcı onayı: tek seferde hata dönülür, otomatik retry yok.

## Etkilenen Dosyalar/Modüller (bilinen)
- `backend/models.py` (yeni `OperationType.WORD_TO_PDF`, hedef alan adı
  `pdfFileName` önerisi — plan aşamasında kesinleştirilecek)
- `backend/orchestrator.py` (yeni dönüştürme fonksiyonu + `apply_plan`
  entegrasyonu)
- `backend/security.py` (Saga #338'in `_DESTINATION_FIELD_BY_OPERATION`
  dict'ine yeni giriş — whitelist+çakışma kontrolü otomatik kapsanır)
- `backend/tests/test_orchestrator.py`, `backend/tests/test_security.py`

## Rollback Beklentisi
Hata durumunda (timeout, tazelik başarısız, kaynak bozuk) hiçbir dosya
değişmez — kaynak .docx dokunulmaz, hedef .pdf ya hiç oluşmaz ya da (eski
bir dosya varsa) olduğu gibi kalır. Ayrı bir "rollback" adımı gerekmiyor
çünkü başarısız durumda zaten hiçbir kalıcı değişiklik yapılmamış olur —
bu, mevcut PDF_COMPRESS/EXCEL_CREATE gibi "yaz, sonra doğrula" desenleriyle
tutarlı.

## Risks
- LibreOffice'in `--convert-to pdf` davranışı, çıktı dosya adını HER ZAMAN
  `source.stem+".pdf"` olarak üretir (komut satırından çıktı adı doğrudan
  belirtilemez, sadece `--outdir` belirtilebilir) — implementasyon,
  dönüşümü geçici bir dizine yapıp sonra kullanıcının istediği isme
  `Path.rename` ile taşımalı. Bu, plan aşamasında netleştirilecek bir
  teknik detay.
- İlk `soffice --version` denemesi bu oturumda ~30 saniye takılıp kaldı
  (muhtemelen ilk-çalıştırma profil oluşturma gecikmesi) — `--headless
  --norestore` bayraklarıyla ikinci deneme sorunsuz çalıştı. İmplementasyon
  bu bayrakları kullanmalı, ayrıca timeout (AC-2) tam olarak bu tür
  gecikmeleri güvenli şekilde ele almak için var.

## Assumptions
- Hedef alan adı `pdfFileName` olarak varsayıldı (WORD_APPEND_TABLE'ın
  kullanmadığı, PDF_COMPRESS'in `compressedFileName` desenine benzer) —
  plan aşamasında modelin gerçek alan isimlendirme konvansiyonu okunarak
  kesinleştirilecek.
- `soffice.exe`'nin tam yolu (`C:\Program Files\LibreOffice\program\soffice.exe`)
  bu makinede doğrulandı; implementasyon PATH'te `soffice` aranmalı,
  bulunamazsa AC'deki "LibreOffice bulunamadı" hatası dönmeli (sabit
  Windows yoluna hardcode edilmemeli).

## Unknowns
- Gerçek alan adı/parametre isimlendirmesi (plan aşamasında modeldeki
  mevcut konvansiyona bakılarak netleştirilecek).

## Sorular ve Cevaplar (ham kayıt)
1. Operasyon adı? → `WORD_TO_PDF` (OFFICE_TO_PDF değil, YAGNI).
2. Tazelik hatası davranışı? → `PlanApplicationError`, özel tazelik
   mesajıyla, retry yok.
3. Timeout süresi? → 60 saniye.
4. Test stratejisi? → unit %70 / integration %30 (gerçek soffice) / e2e %0.
5. Bozuk kaynak davranışı? → Ayrı bir dal yok, AC-3'ün tazelik hatasına
   dahil.
6. Hedef çakışması? → PathWhitelistError (Saga #338 ile tutarlı).
7. Kabul kriteri sahibi? → Otomatik testler yeterli, manuel UI testi yok.
8. Persona/Hedef/Happy path/Bağımlılıklar → Saga #339 görev açıklamasından
   (kullanıcı mesajından, tekrar sorulmadı).
