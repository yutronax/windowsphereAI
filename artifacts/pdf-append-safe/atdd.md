---
task_slug: pdf-append-safe
jira_id: null
saga_task_id: 323
priority: high
coverage_target: 85
performance_target: null
memory_target: null
test_strategy:
  unit: 75
  integration: 20
  e2e: 5
affected_modules:
  - backend/models.py
  - backend/orchestrator.py
  - backend/plan_generation.py
  - requirements.txt
threat_model: done
---

# ATDD — pdf-append-safe

## Jira Kaynağı
Jira'ya bağlı değil — yerel görev (Saga #323, epic #29 "Format Agent Sistemi")

## Persona
Muhasebeci — var olan bir PDF raporuna kısa bir not/onay metni eklemek isteyen, ve kaynak dosyanın bozuk olması durumunda TÜM İÇERİĞİNİ kaybetmemesi gereken kullanıcı.

## Hedef (Neden)
Mevcut kod tabanında PDF'e metin ekleme (APPEND) operasyonu hiç yok — sadece MERGE (çoklu PDF birleştirme) var. Eski projede (`core/agents/pdf_agent.py`) bu özellik vardı ama kritik bir veri kaybı hatası taşıyordu: kaynak PDF bozuksa, bu durum "dosya yok" ile AYNI kod yoluna düşüp bozuk-ama-var-olan dosyanın TÜM önceki içeriği sessizce silinip üzerine yeni bir PDF yazılabiliyordu. Bu task, özelliği SIFIRDAN, bu güvenlik garantisini baştan tasarımına gömerek ekliyor.

## User Story
As a muhasebeci
I want doğal dil isteğimle var olan bir PDF'in sonuna yeni bir metin sayfası ekleyebilmek
So that raporlarıma not/onay eklerken kaynak dosyanın bozuk olması durumunda içeriğimi asla kaybetmeyeyim

## Acceptance Criteria (Given-When-Then, önceliklendirilmiş)
1. [Critical] Given geçerli, okunabilir bir kaynak PDF, When kullanıcı "bu rapora 'incelendi ve onaylandı' notu ekle" der, Then LLM `appendText` alanını üretir, plan onaylandığında kaynak PDF'in SONUNA bu metni içeren yeni bir sayfa eklenir, dosya güncellenir.
2. [Critical] Given BOZUK bir kaynak PDF (pypdf açamıyor — örn. geçersiz PDF header'ı), When APPEND planı uygulanır, Then işlem AÇIK bir hata ile reddedilir (`PlanApplicationError`), kaynak dosyaya HİÇ dokunulmaz, orijinal (bozuk) içerik olduğu gibi kalır.
3. [Critical] Given kaynak dosya HİÇ YOK (path mevcut değil), When APPEND planı uygulanır, Then AÇIK bir "dosya bulunamadı" hatası döner — bu, AC-2'deki "bozuk dosya" hatasından AYRI bir mesajla ayırt edilir (ikisi aynı koda düşmez, kod yolları farklı).
4. [High] Given kaynak dosya salt-okunur/kilitli (izin hatası), When APPEND planı uygulanır, Then AÇIK bir izin hatası döner, dosyaya dokunulmaz.
5. [High] Given `appendText` boş/whitespace-only, When plan üretilir, Then LLM bu alanı boş bırakmamalı — ama eğer bir şekilde boş gelirse orchestrator seviyesinde reddedilmeli (422/PlanApplicationError), boş bir sayfa asla eklenmemeli.
6. [Medium] Given whitelist dışı bir hedef path (mevcut security.py kuralları), When APPEND planı uygulanır, Then mevcut whitelist ihlali davranışı (403, Saga #271/#272 deseniyle tutarlı) uygulanır.

## Davranış Sözleşmesi (hangi durumda ne döner)
| # | Durum | Dönen değer / durum kodu | Yan etki | Kullanıcı ne görür | AC |
|---|---|---|---|---|---|
| 1 | Happy path (geçerli PDF'e sayfa eklenir) | 200 + TransactionApplyResponse{status: "committed"} | Kaynak PDF'in sonuna yeni sayfa eklenir, transaction kaydı oluşur | "İşlem tamamlandı" | AC-1 |
| 2 | Girdi geçersiz (appendText boş) | 422 veya PlanApplicationError (mevcut desene göre) | Yok, dosyaya dokunulmaz | Hata mesajı | AC-5 |
| 3 | Kaynak yok (path mevcut değil) | PlanApplicationError, "kaynak dosya bulunamadı" | Yok | Net hata mesajı, AC-2'den AYRI metin | AC-3 |
| 4 | Yetkisiz erişim (whitelist ihlali VEYA dosya izin hatası) | 403 (whitelist) veya PlanApplicationError (izin), mevcut desenler | Yok | Net hata mesajı | AC-4, AC-6 |
| 5 | Dış bağımlılık hatası | Uygulanmıyor — ReportLab yerel bir kütüphane, dış API çağrısı yok. Silindi. | | | |
| 6 | Zaman aşımı | Uygulanmıyor — tek sayfa metin render + pypdf append, milisaniyeler mertebesinde, ayrı bir timeout senaryosu gerekmiyor. Silindi. | | | |
| 7 | **Kısmi başarı** (sayfa render edildi ama pypdf append sırasında hata) | Transaction rollback edilir (mevcut atomik rollback deseni, Saga #276/#286), kaynak dosya ORİJİNAL haliyle kalır — "yarım" bir append (örn. sayfa eklenmiş ama dosya bozulmuş) ASLA kalıcı olmaz | Rollback | Hata mesajı, dosya değişmemiş | — (mevcut orchestrator garantisi) |
| 8 | **Hiçbir şey yapılamadı ama hata da yok** — Uygulanmıyor: bu operasyonda "sessiz no-op" imkansız çünkü ya sayfa gerçekten eklenir (committed) ya da açık bir hata döner (rollback) — ara bir "başarılı ama hiçbir şey olmadı" durumu YOK. Bu task'ın TÜM amacı zaten bu satırın (eski projedeki "bozuk kaynak → dosya yok gibi davran → içeriği sil" hatası) İMKANSIZ hale getirilmesi. | | | | |

Kısmi başarı: Satır 7 — atomik rollback garantisi (mevcut orchestrator mimarisi) sayesinde "yarım append" durumu asla kalıcı olmaz.
Hiçbir şey yapılamadı ama hata da yok: BİLİNÇLİ OLARAK YOK EDİLDİ — bu task'ın tüm amacı eski projedeki tam olarak bu sınıf hatayı (kaynak bozuksa "dosya yok" gibi davranıp içeriği sessizce silme) imkansız kılmak.
Boş sonuç ↔ hata ayrımı: "Kaynak yok" (AC-3) ile "kaynak bozuk" (AC-2) FARKLI mesajlarla ayrılır — ikisi de eski projede AYNI koda düşüyordu, bu task'ın çözdüğü asıl kusur budur.

## Threat-Model Notu
STRIDE-lite geçişi: Kullanıcı girdisi (doğal dil isteği) LLM üzerinden bir
metin alanına (`appendText`) dönüşüp PDF'e basılıyor — Tampering/Injection
kategorisi değerlendirildi. ReportLab metin render'ı HTML/script
yorumlamıyor (düz metin çizim API'si), bu yüzden XSS/injection riski yok.
DoS: `appendText` uzunluğu sınırsız olursa çok büyük bir tek sayfa/render
maliyeti oluşabilir — bu KABUL EDİLEN bir risk değil, ucuz bir mitigasyon
var: LLM prompt'u zaten kısa bir not/metin üretmeye yönlendiriliyor, ama
yine de bir üst sınır (makul bir karakter sayısı) `PlanSkeleton` şemasında
uygulanmalı — bu plan aşamasında netleştirilecek.

## Test Strategy
Unit: 75% — metin→PDF sayfa render fonksiyonu (ReportLab), bozuk-kaynak tespiti ve AÇIK hata fırlatma, kaynak-yok ile kaynak-bozuk ayrımı
Integration: 20% — orchestrator.py'nin APPEND operationType'ını uçtan uca (gerçek dosya sistemi, tmp_path) işlemesi, rollback garantisi
E2E: 5% — mevcut e2e altyapısı yok, component/entegrasyon testine kayar

## Benchmark / Başarı Ölçütü
Coverage Target: 85%
Performance Target: Yok
Memory: Yok
Görsel/UI kriteri: Yok — backend-only, PlanCard zaten operationType gösteriyor (mevcut altyapı, ek iş gerekmez)
Diğer ölçülebilir kriterler: Bozuk kaynak PDF ile denendiğinde orijinal dosyanın byte-byte DEĞİŞMEDİĞİ doğrulanabilir (en kritik test).

## Kapsam Dışı
- Zengin format (font/boyut/renk seçimi, resim/tablo ekleme) — sadece düz metin, tek sayfa, varsayılan font.
- Frontend'de APPEND'e özel bir UI elemanı — PlanCard zaten operationType'ı genel olarak gösteriyor, ek iş gerekmiyor.
- Birden fazla sayfa eklenmesi — MVP kapsamı tek sayfa.

## Etkilenen Dosyalar/Modüller (bilinen)
- `backend/models.py` — `OperationType` enum'una `APPEND` eklenir, `PlanStep`'e `appendText: str | None` alanı eklenir.
- `backend/orchestrator.py` — APPEND operationType için execute mantığı (kaynak PDF oku, bozuksa/yoksa AÇIK hata, ReportLab ile yeni sayfa render et, pypdf ile mevcut PDF'e ekle).
- `backend/plan_generation.py` — sistem promptuna APPEND operationType + appendText alan açıklaması eklenir.
- `requirements.txt` — `reportlab` yeni bağımlılık.

## Rollback Beklentisi
Mevcut atomik rollback mimarisi (Saga #276/#286) — hata durumunda tamamlanan adımlar geri alınır, kaynak dosya orijinal haliyle kalır. APPEND'e özel: kaynak dosya HİÇ değiştirilmeden önce (render+append başarılı olana kadar) orijinal path'e yazılmamalı — geçici bir dosyaya yazılıp, TAMAMEN başarılıysa atomic rename ile orijinalin yerine geçmeli (bu, "yarım yazılmış dosya" riskini de önler, plan aşamasında netleştirilecek).

## Risks
- ReportLab yeni bir bağımlılık — `requirements.txt`'e eklenmesi güvenlik taramasından (pip-audit) geçmeli, bilinen açığı olmayan bir sürüm seçilmeli (plan aşamasında kontrol edilecek).
- `appendText` uzunluk sınırı (Threat-Model Notu) plan aşamasında netleştirilecek.
- Dosyanın YERİNDE (in-place) değil geçici-dosya+atomic-rename ile güncellenmesi gerekiyor (yukarıdaki Rollback Beklentisi) — bu, mevcut MOVE/COPY operasyonlarından farklı bir yazma deseni, code-copilot'a açıkça talimat olarak geçirilmeli.

## Assumptions
- `appendText` alanı `PlanStep`'e eklenir (MERGE'ün `mergedFileName`'i gibi, sadece APPEND operationType'ta geçerli, diğerlerinde şemadan tamamen atlanır — mevcut LLM prompt konvansiyonu).

## Unknowns
- ReportLab'ın hangi sürümünün güvenlik taramasından geçeceği — plan aşamasında `pip index versions reportlab` veya benzeri ile netleştirilecek.
- appendText uzunluk sınırı — plan aşamasında makul bir sayı (örn. 5000 karakter, birkaç paragraf) önerilecek.

## Sorular ve Cevaplar (ham kayıt)
1. Append ne anlama gelsin? → Var olan PDF'e YENİ SAYFA olarak metin eklemek (LLM üretir)
2. Kaynak bozuksa ne dönmeli? → Açık HTTP hatası, PlanApplicationError deseniyle tutarlı
3. İçerik nereden gelsin? → LLM doğal dil isteğinden üretir (appendText alanı)
4. PDF render aracı ne olsun? → ReportLab (yeni bağımlılık)
5. Test stratejisi oranı? → 75/20/5
6. Kapsam dışı ne var? → Zengin format yok, sadece düz metin/tek sayfa/varsayılan font
</content>
