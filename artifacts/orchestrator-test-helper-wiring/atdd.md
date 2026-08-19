---
task_slug: orchestrator-test-helper-wiring
jira_id: null
saga_task_id: 332
priority: low
coverage_target: null
performance_target: null
memory_target: null
test_strategy:
  unit: 100
  integration: 0
  e2e: 0
affected_modules:
  - backend/tests/test_orchestrator.py
---

# ATDD — orchestrator-test-helper-wiring

## Jira Kaynağı
Jira'ya bağlı değil — yerel görev (Saga #332, epic #29 altında).

## Persona
Bu deponun geliştiricileri ve red-team incelemesi yapan kişi/subagent — yeni bir
operation-specific field-wiring testi ekleyecek veya var olan bir testi
inceleyecek kişi.

## Hedef (Neden)
Saga #319'da eklenen "apply_plan'ı 2 kez farklı field değerleriyle çağır, 2
farklı dosya çıktısını doğrula" kalıbı (docs/DESIGN_DECISIONS.md §6'da
tanımlı) `test_apply_plan_rename_output_filename_changes_when_new_file_names_changes`
(satır 504) ve `test_apply_plan_merge_output_filename_changes_when_merged_file_name_changes`
(satır 634) testlerinde kopyala-yapıştır 25-30 satır olarak tekrarlanmış
durumda. Ortak bir pytest helper'ı bu kopyalamayı ortadan kaldırır ve
red-team incelemesinin her yeni testin §6 tarifini doğru uyguladığını
görsel olarak (helper çağrısına bakarak) doğrulamasını kolaylaştırır.

## User Story
As a bu depoda test yazan/inceleyen geliştirici
I want field-wiring testlerini tek bir paylaşılan helper üzerinden yazmak
So that kopyala-yapıştır test kodu azalsın ve §6 tarifine uygunluk tek bakışta görülsün

## Acceptance Criteria (Given-When-Then, önceliklendirilmiş)
1. [Critical] Given `test_orchestrator.py` içinde tanımlı yeni bir yardımcı
   fonksiyon (örn. `assert_apply_plan_wiring(session, tmp_path, build_plan_fn,
   pairs)`), When bu fonksiyona `apply_plan` argümanları + `(field_value,
   expected_output_check)` çiftlerinden oluşan bir liste verilir, Then
   fonksiyon her çift için `apply_plan`'ı bir kez çağırır ve ilgili
   `expected_output_check` callable'ını sonuca uygular.
2. [Critical] Given mevcut `test_apply_plan_rename_output_filename_changes_when_new_file_names_changes`
   ve `test_apply_plan_merge_output_filename_changes_when_merged_file_name_changes`
   testleri, When bu iki test yeni helper'ı kullanacak şekilde yeniden
   yazılır, Then testler önceki ile aynı senaryoları doğrular ve
   `pytest backend/tests/test_orchestrator.py` tüm suite yeşil kalır.
3. [High] Given helper 2'den fazla `(field_value, expected_output_check)`
   çifti alabilecek şekilde tasarlanmış, When gelecekte 3. bir field-wiring
   testi eklenmek istenirse, Then geliştirici mevcut helper'ı doğrudan
   çağırabilir, testi sıfırdan yazmaz.
4. [Medium] Given helper içinde bir çiftin `expected_output_check`'i
   başarısız olur, When test çalıştırılır, Then pytest'in doğal
   `AssertionError`'ı (ekstra sarmalama olmadan) fırlatılır ve traceback
   hangi assert satırında başarısız olduğunu gösterir.

## Davranış Sözleşmesi (hangi durumda ne döner)
| # | Durum | Dönen değer / durum kodu | Yan etki | Kullanıcı ne görür | AC |
|---|---|---|---|---|---|
| 1 | Happy path: 2 geçerli çift, ikisi de assert'i geçer | Helper `None` döner (pytest fonksiyonu, return değeri yok) | `apply_plan` her çift için bir kez çağrılır, dosya sistemi her seferinde ilgili operation'ın çıktısını üretir | Test yeşil geçer | AC-1, AC-2 |
| 2 | Girdi geçersiz: `pairs` boş liste | Helper hiçbir `apply_plan` çağrısı yapmaz, sessizce döner (assert edilecek bir şey yok) | Yok | Test "hiçbir şey doğrulanmadı" anlamına gelir — çağıran bunu fark etmez, bu yüzden çağıran taraf en az 1 çift geçirmekle yükümlü (helper'ın sorumluluğu değil) | — |
| 3 | Kaynak yok: `build_plan_fn` geçersiz bir dosya adına referans veren plan üretir | `apply_plan` kendi var olan hatasını (örn. dosya bulunamadı) fırlatır | Yok (transaction rollback zaten `apply_plan`'ın kendi sorumluluğu) | pytest, `apply_plan`'dan gelen orijinal exception'ı gösterir | — (bu, helper'ın değil `apply_plan`'ın mevcut davranışı) |
| 4 | Kısmi başarı: çiftlerden 1.'si assert'i geçer, 2.'si başarısız olur | 2. çiftteki `AssertionError` yükselir, 1. çift zaten doğrulanmış olarak kalır | 1. çift için dosya sistemi değişikliği zaten gerçekleşmiş durumda kalır (test fixture temizliği pytest'in `tmp_path` izolasyonuna bırakılır) | pytest, hangi çiftte (kaçıncı index) başarısız olduğunu traceback satırından gösterir — özel mesaj eklenmez | AC-4 |
| 5 | Hiçbir şey yapılamadı ama hata da yok | Bu durum tanımsız/olanaksız: helper her çift için `apply_plan`'ı senkron çağırır, çağrı ya başarılı assert ile ya da exception ile sonuçlanır — sessiz "başarı" görünümü üretecek bir dal yoktur | — | — | — |

Kısmi başarı: 4. satırda tanımlı — ilk N-1 çift geçer, N. çift assert
hatası verirse pytest o testi FAIL olarak işaretler, önceki çiftlerin
geçmiş olması testi PASS yapmaz (pytest tek bir test fonksiyonu içinde
tüm assert'lerin geçmesini şart koşar).
Hiçbir şey yapılamadı ama hata da yok: Olanaksız — helper senkron ve
exception-şeffaf, "sessiz başarı" üretecek try/except yutma kodu
içermeyecek (AC-4 ile garanti altına alınır, kod incelemesinde
kontrol edilir).
Boş sonuç ↔ hata ayrımı: Uygulanmıyor — bu bir test yardımcı fonksiyonu,
API/servis katmanı değil; "boş sonuç" kavramı yok. Silinme nedeni: helper
hiçbir zaman kısmi/boş bir sonuç döndürmez, sadece assert eder veya
exception fırlatır.
Yetkisiz erişim / Dış bağımlılık hatası (ağ/DB/API) / Zaman aşımı satırları
silindi — bu tabloda uygulanmıyor: helper salt yerel dosya sistemi ve
mevcut `apply_plan` fonksiyonunu çağıran senkron bir test yardımcısıdır,
ağ/DB/auth katmanı yok.

## Test Strategy
Unit: 100% — `test_orchestrator.py` içindeki mevcut 2 test (rename, merge)
helper'ı kullanacak şekilde yeniden yazılır ve suite'in geri kalanıyla
birlikte `pytest` ile çalıştırılır. Integration/E2E: 0% — bu saf bir
test-suite iç refactor'ü, ayrı bir entegrasyon/e2e senaryosu gerektirmez.

## Benchmark / Başarı Ölçütü
Coverage Target: Belirtilmedi (yeni production kodu yok, coverage hedefi
uygulanmıyor).
Diğer ölçülebilir kriterler:
- `pytest backend/tests/test_orchestrator.py` tüm testler PASS.
- Refactor sonrası `test_apply_plan_rename_output_filename_changes_when_new_file_names_changes`
  ve `test_apply_plan_merge_output_filename_changes_when_merged_file_name_changes`
  testlerinin gövdesi helper çağrısı + plan/dosya kurulumuna indirgenir
  (orijinal 25-30 satırlık tekrar kalmaz).

## Kapsam Dışı
- `backend/tests/test_orchestrator.py` dışındaki hiçbir dosya değişmez;
  `orchestrator.py` (production kod) dokunulmaz.
- `test_apply_plan_excel_sort_output_differs_when_sort_column_changes`
  (satır 1708) bu görevin kapsamına DAHIL DEĞİL — kullanıcı sadece
  rename+merge testlerinin taşınmasını onayladı, excel_sort ayrı bırakıldı.
- Yeni bir conftest.py fixture'ı eklenmeyecek; helper `test_orchestrator.py`
  içinde local kalacak (kullanıcı onayı: başka dosya bu pattern'i
  kullanmıyor, paylaşılan fixture YAGNI).
- Helper'a özel hata mesajı/sarmalama eklenmeyecek (kullanıcı onayı: doğal
  pytest AssertionError yeterli).

## Etkilenen Dosyalar/Modüller (bilinen)
- backend/tests/test_orchestrator.py (satır ~504 ve ~634 civarındaki 2 test
  + yeni helper fonksiyonu)

## Rollback Beklentisi
Uygulanmıyor — production davranışında değişiklik yok, sadece test kodu
refactor'ü. Helper suite'i bozarsa geri alma standart `git revert` ile
yapılır, runtime rollback mekanizması gerektirmez.

## Risks
- Helper'ın imzası ileride 3. bir field-wiring testi (örn. excel_sort)
  eklenmek istendiğinde yetersiz kalabilir; kullanıcı bu görevi bilinçli
  olarak sadece rename+merge ile sınırladı, excel_sort ayrı bir görevde
  ele alınmalı.

## Assumptions
- `expected_output_check`, `(session, tmp_path, dosya_yolu)` gibi test
  bağlamını alan bir callable olarak tasarlanacak — kullanıcı bu detayı
  belirtmedi, mevcut 2 testin assert mantığından (dosya var mı, içerik ne)
  türetilecek.

## Unknowns
- Helper'ın kesin parametre isimleri ve tipi (implementasyon sırasında
  `plan` skill'i tarafından netleştirilecek).

## Sorular ve Cevaplar (ham kayıt)
1. Hangi mevcut testler helper'a taşınsın? → Sadece rename+merge
   (excel_sort dahil değil, farklı imza + kullanıcı onayı).
2. Helper nerede tanımlansın? → test_orchestrator.py içinde local helper
   (conftest.py fixture'ı değil).
3. Kabul kriteri / test stratejisi? → Sadece mevcut testler geçsin yeterli
   (coverage hedefi yok, bu bir test-suite refactor'ü).
4. Helper kaç (field_value, expected_output_check) çifti kabul etmeli? →
   Liste/iterable, 2 veya daha fazla çift.
5. Bir çift assert başarısız olursa ne olur? → pytest'in doğal
   AssertionError'ı yükselir, özel mesaj sarmalaması yok.
6. Persona/Hedef/Happy path/Bağımlılıklar → Saga #332 görev açıklamasından
   (kullanıcı mesajından, tekrar sorulmadı).
