---
task_slug: dosya-arama-recursive
jira_id: null
saga_task_id: 336
priority: low
coverage_target: 85
performance_target: "3 derinlik + 1000 dosyalık ağaçta 10sn içinde tamamlanır/partial döner"
memory_target: null
test_strategy:
  unit: 80
  integration: 15
  e2e: 5
affected_modules:
  - backend/file_search.py
threat_model: done
---

# ATDD — dosya-arama-recursive

## Jira Kaynağı
Jira'ya bağlı değil — yerel görev (Saga #336, epic #27 "Dosya Arama", Saga #315'ten bölündü)

## Persona
Muhasebeci — yıllık arşiv gibi çok seviyeli klasör yapılarında (örn. `2024/Q1/Ocak/faturalar/`) dosya arayan, mevcut non-recursive aramanın alt klasörlerdeki dosyaları kaçırdığını fark eden kullanıcı.

## Hedef (Neden)
Saga #313/#314'teki arama bilinçli olarak non-recursive'ti (sadece `allowed_root`'un doğrudan altı). Bu, çok seviyeli klasör yapılarında kullanışsız — kullanıcı alt klasörlerdeki dosyaları hiç bulamıyor. Bu task recursive taramayı ekliyor, ama sınırsız derinlik/döngüsel symlink riskini (DoS, sonsuz döngü) baştan engelleyerek.

## User Story
As a muhasebeci
I want /api/search'ün alt klasörlere de inmesini
So that çok seviyeli arşiv yapımda dosya ararken hiçbir şeyi kaçırmayayım

## Acceptance Criteria (Given-When-Then, önceliklendirilmiş)
1. [Critical] Given `allowed_root/a/b/dosya.pdf` gibi 2 seviye derinlikte bir dosya, When `/api/search` çağrılır (herhangi bir filtreyle), Then dosya sonuç listesinde görünür (mevcut non-recursive davranışın aksine).
2. [Critical] Given `allowed_root`'tan itibaren 4. seviyede bir dosya (derinlik sınırı 3ü aşıyor), When arama çalıştırılır, Then o dosya sonuçta GÖRÜNMEZ (derinlik sınırı uygulanır), hata fırlatılmaz.
3. [Critical] Given `A` klasörü altında `A`'ya geri dönen bir döngüsel symlink (`A/link → A`), When arama çalıştırılır, Then sonsuz döngüye girilmez — ziyaret edilen gerçek (resolved) path'ler bir set'te tutulur, tekrar görülen dizin atlanır, arama normal şekilde tamamlanır.
4. [High] Given `content_contains` filtresiyle birlikte çok seviyeli bir klasör yapısı, When arama çalıştırılır, Then içerik araması da recursive çalışır (AC-1 ile aynı derinlik/döngü kurallarına tabi).
5. [High] Given 3 derinlik + 1000 dosyalık bir ağaç, When arama 10 saniyeyi aşarsa, Then o ana kadar bulunan sonuçlarla `partial: true` döner (Saga #314'teki timeout deseniyle tutarlı, recursive tarama da bu timeout'a tabi).
6. [Medium] Given `allowed_root` dışına işaret eden bir symlink (Saga #314 AC-8), When recursive tarama alt klasörlerde böyle bir symlink'e rastlar, Then o symlink (ve altındaki hiçbir şey) taranmaz — mevcut dışlama kuralı recursive bağlamda da geçerli.
7. [Medium] Given gizli (nokta ile başlayan) bir alt klasör (örn. `.git/`), When recursive tarama çalışır, Then o klasörün altına hiç inilmez (mevcut gizli-dosya-atlama kuralının klasörlere de genişletilmesi).

## Davranış Sözleşmesi (hangi durumda ne döner)
| # | Durum | Dönen değer / durum kodu | Yan etki | Kullanıcı ne görür | AC |
|---|---|---|---|---|---|
| 1 | Happy path (çok seviyeli ağaçta dosya bulunur) | 200 + SearchResponse{results: [...]} | Yok (salt-okunur) | Alt klasörlerdeki dosyalar dahil tam sonuç listesi | AC-1 |
| 2 | Girdi geçersiz | Değişmiyor — Saga #313/#314'teki mevcut 422 davranışı (filtre validasyonu) bu task'ta değişmedi. Silindi (bu task'ın kapsamı dışı). | | | |
| 3 | Kaynak yok (allowed_root artık mevcut değil) | 410 Gone (mevcut davranış, değişmiyor) | Yok | "Seçili klasör artık mevcut değil" | — (313'ten miras) |
| 4 | Derinlik sınırı aşıldı | 200 + SearchResponse (sınırı aşan dosyalar HARİÇ) | Yok, sessizce dışlanır | Sonuç listesinde 4.+ seviye dosyalar hiç görünmez | AC-2 |
| 5 | Döngüsel symlink | 200 + SearchResponse (döngü tespit edilip atlanır, tarama tamamlanır) | Yok, sonsuz döngü/timeout yaşanmaz | Normal sonuç listesi, hata yok | AC-3 |
| 6 | Zaman aşımı (10sn aşıldı, recursive tarama uzun sürdü) | 200 + SearchResponse{results: [...], partial: true} | Tarama o an kesilir | "Kısmi sonuç" göstergesi (partial flag, #314'ten miras) | AC-5 |
| 7 | Kısmi başarı (bazı alt klasörler taranmış, bazıları timeout'ta kalmış) | 200 + SearchResponse{results: [o ana kadar bulunanlar], partial: true} | Yok | Kısmi sonuç listesi + partial:true | AC-5 |
| 8 | Hiçbir şey yapılamadı ama hata da yok (0 sonuç) | 200 + SearchResponse{results: []} | Yok | Boş liste — "hata" değil "sonuç yok" | AC-1 (negatif durum) |

Kısmi başarı: Satır 7 — recursive tarama derinlemesine ilerlerken 10sn dolarsa, o ana kadar keşfedilen TÜM eşleşmelerle (hangi derinlikte olursa olsun) `partial:true` döner; "yarım kalan" bir alt ağaç sessizce tam sayılmaz.
Hiçbir şey yapılamadı ama hata da yok: Filtrelere uyan dosya olmazsa (derinlik sınırı içinde arandı ama eşleşme yok) `results: []` ile 200 döner — normal "sonuç yok" durumu.
Boş sonuç ↔ hata ayrımı: Boş sonuç (`200 + []`) = eşleşme yok. Klasör yok (`410`) = allowed_root artık mevcut değil. Derinlik sınırı/döngü/symlink-dışlama HİÇBİRİ hata döndürmez — sessizce filtrelenip normal 200 akışına devam eder (bu, DoS/veri-sızıntısı önleme mekanizmalarının kullanıcıya "hata" gibi görünmemesi gerektiği anlamına gelir, sadece sonuç listesi daha dar olur).

## Test Strategy
Unit: 80% — derinlik sınırı sayımı, döngüsel symlink tespiti (ziyaret edilen path seti), gizli klasör dışlama, allowed_root dışı symlink dışlamanın recursive bağlamda çalışması, content_contains'in recursive'e uyumu
Integration: 15% — `/api/search` endpoint'inin çok seviyeli gerçek dosya sistemi fixture'ıyla uçtan uca çağrısı
E2E: 5% — mevcut e2e altyapısı yok, bu oran component/entegrasyon testine kayar (Saga #313/#314'teki gibi)

## Benchmark / Başarı Ölçütü
Coverage Target: 85%
Performance Target: 3 derinlik + 1000 dosyalık ağaçta arama 10sn içinde tamamlanır veya partial:true ile kesilir
Memory: Belirtilmedi (ziyaret edilen path seti klasör sayısıyla sınırlı, dosya sayısıyla değil — makul kabul edilir)
Görsel/UI kriteri: Yok — backend-only, frontend (#334) değişmiyor
Diğer ölçülebilir kriterler: Döngüsel symlink senaryosu sonsuz döngüye GİRMEMELİ (test timeout'suz tamamlanmalı) — bu tek başına en kritik ölçüt.

## Threat-Model Notu
Bu görevin ana tehdit kategorisi DoS'tur (sınırsız derinlik gezinmesi, döngüsel
symlink ile sonsuz döngü) — STRIDE-lite geçişinde bu ikisi dışında yeni bir
tehdit yüzeyi bulunmadı (Spoofing/Tampering/Repudiation/Elevation bu task'a
uygulanmıyor; Info Disclosure zaten gizli-klasör-atlama ve allowed_root-dışı
symlink dışlamayla #314'ten miras alınıyor). DoS riski ayrı bir AC-S
gerektirmedi çünkü ATDD'nin kendi soruları sırasında zaten somut kabul
kriterlerine (AC-2 derinlik sınırı, AC-3 döngü koruması, AC-5 timeout)
dönüştürüldü — bu üçü olmadan bu task onaylanmazdı, o yüzden ayrı bir
güvenlik eki yerine ana AC listesinin parçası olarak kaldılar.

## Kapsam Dışı
- İlerleme göstergesi / scan_id / polling mekanizması — Saga #337'de, bu task'ta YOK.
- Frontend (SearchPanel, Saga #334) değişikliği — backend zaten aynı `/api/search` sözleşmesini koruyor, UI tarafında bir değişiklik gerekmiyor.
- Recursive/non-recursive'i seçilebilir bir parametre yapmak — kullanıcı kararı: davranış koşulsuz recursive'e geçiyor, opt-in/opt-out yok.

## Etkilenen Dosyalar/Modüller (bilinen)
- `backend/file_search.py` — `search_files()`'ın dosya toplama mantığı (`folder.iterdir()`) recursive bir gezinmeye (`os.walk` benzeri, derinlik sayacı + ziyaret edilen path seti ile) dönüştürülecek.

## Rollback Beklentisi
Salt-okunur bir özellik (dosya sistemi üzerinde yazma/silme yapmıyor) — rollback kavramı uygulanmıyor.

## Risks
- (Kullanıcı onayladı) Bu değişiklik davranışsal bir breaking change — mevcut non-recursive sonuçlara güvenen biri varsa artık daha fazla dosya görecek. Kabul edilen risk: tek tüketici SearchPanel (#334), dış API tüketicisi yok.
- Derinlik sınırı (3) `backend/security.py::MAX_PATH_DEPTH` ile aynı sayı ama BAĞIMSIZ bir sabit olarak `file_search.py` içinde tanımlanacak (security.py'ye dokunulmuyor, plan.md'de netleştirilecek) — iki sabitin gelecekte birbirinden sapması riski var, ayrı bir yorum satırıyla bu bağlantı belgelenmeli.

## Assumptions
- Derinlik sayımı `allowed_root`'un DOĞRUDAN altını derinlik 1 olarak sayar (yani mevcut #313/#314 davranışı = derinlik 1 ile aynı sonuçları üretir, geriye dönük bir "derinlik 1 = eski davranış" tutarlılığı sağlanır) — kullanıcıya sorulmadı, security.py'deki MAX_PATH_DEPTH yorumundan (satır 17-18) çıkarılan varsayım.

## Unknowns
- Yok.

## Sorular ve Cevaplar (ham kayıt)
1. Derinlik sınırı kaç olsun? → security.py'deki MAX_PATH_DEPTH ile aynı (gerçek değer: 3 — plan aşamasında doğrulandı, soru sırasında yanlışlıkla 5 denmişti)
2. İçerik araması da recursive olsun mu? → Evet, hepsi recursive
3. Recursive tarama için de 10sn timeout uygulansın mı? → Evet, aynı timeout
4. Döngüsel symlink tespit edilirse ne olsun? → Ziyaret edilen resolved path'leri set'te tut, tekrarı atla
5. Bu breaking change kabul edilebilir mi? → Evet, tek tüketici SearchPanel zaten yeni davranışa göre çalışır
6. Benchmark ne olsun? → 3 derinlik + 1000 dosyada 10sn içinde tamamlanır/partial, döngü sonsuza girmez
7. Test stratejisi oranı? → 80/15/5
8. Kapsam dışı ne var? → İlerleme göstergesi (#337'de), frontend değişikliği yok
</content>
