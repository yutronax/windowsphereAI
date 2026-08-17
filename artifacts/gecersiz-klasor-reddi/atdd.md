---
task_slug: gecersiz-klasor-reddi
jira_id: null
saga_task_id: 256
priority: high
coverage_target: 90
performance_target: null
memory_target: null
test_strategy:
  unit: 70
  integration: 0
  e2e: 30
affected_modules:
  - ui/src/components/onboarding/OnboardingScreen.tsx
  - ui/src/components/onboarding/OnboardingScreen.test.tsx
  - ui/e2e/onboarding.spec.ts
---

# ATDD — gecersiz-klasor-reddi

## Jira Kaynağı
Jira'ya bağlı değil — yerel görev. Saga task #256, epic #23 "MVP: Kullanıcı girişi ve ilk kayıt akışı" (proje: windows-ai-files).

## Persona
Muhasebeci/avukat segmentinden, ilk kez uygulamayı açan ve onboarding akışında çalışma klasörünü seçen kullanıcı. Seçtiği klasör silinmiş, taşınmış veya erişim izni kaldırılmış olabilir (örn. ağ sürücüsü koptu, harici disk çıkarıldı).

## Hedef (Neden)
Şu an `chooseFolder` dialogtan dönen path'i hiçbir kontrol yapmadan doğrudan state'e yazıyor. Kullanıcı erişilemez bir klasör seçerse (silinmiş/izinsiz), "Devam" aktifleşiyor ve kullanıcı ancak sonraki bir adımda (dosya işlemi sırasında) anlaşılmaz bir hatayla karşılaşabilirdi. Bu görev, Entry katmanının sorumluluğu gereği (docs/DESIGN_DECISIONS.md:117 — "Girdi reddedilir, kullanıcıya net hata döner") klasörü seçildiği anda doğrulayıp erişilemezse net bir hata gösterir, akışın ileri gitmesini engeller.

## User Story
As a onboarding ekranındaki kullanıcı
I want geçersiz veya erişilemeyen bir klasör seçtiğimde bunu hemen ve net bir şekilde öğrenmek
So that "Devam"a basıp ilerideki bir adımda anlaşılmaz bir hatayla karşılaşmayayım, hemen düzeltme fırsatım olsun

## Acceptance Criteria (Given-When-Then, önceliklendirilmiş)
1. [Critical] Given kullanıcı "Klasör Seç" dialog'undan geçerli/erişilebilir bir klasör seçer, When mock'lanan `plugin:fs|exists` invoke'u `true` döner, Then path (normalize edilmiş) gösterilir, hata yok, "Devam" aktifleşir (mevcut davranışla tutarlı).
2. [Critical] Given kullanıcı dialog'dan bir klasör seçer, When mock `plugin:fs|exists` invoke'u `false` döner, Then seçili klasör path'i görünür kalır (seçim korunur), altında `#DC2626` renkte "Seçilen klasöre erişilemiyor. Lütfen başka bir klasör seçin." mesajı gösterilir, "Devam" devre dışı kalır.
3. [High] Given hata gösteriliyor (AC-2 tetiklendi), When kullanıcı "Klasör Seç" butonuna tekrar basıp geçerli/erişilebilir bir klasör seçer, Then hata mesajı kalkar, path güncellenir, "Devam" aktifleşir.
4. [High] Given seçilen path trailing slash/backslash içeriyor (örn. `C:\Users\Yusuf\Belgeler\`), When path state'e yazılır, Then trailing slash/backslash temizlenmiş hali (`C:\Users\Yusuf\Belgeler`) gösterilir/saklanır.
5. [Medium] Given kullanıcı art arda birden fazla erişilemez klasör seçer, When her seçimden sonra `exists` `false` dönerse, Then hata her seferinde yeniden gösterilir (kontrol idempotent, tek seferlik değil).

## Davranış Sözleşmesi (hangi durumda ne döner)
| # | Durum | Dönen değer / durum kodu | Yan etki | Kullanıcı ne görür | AC |
|---|---|---|---|---|---|
| 1 | Happy path — geçerli/erişilebilir klasör seçilir | `{selectedFolder: normalizedPath, isFolderInvalid: false}` | Yok | Path gösterilir, Devam aktif | AC-1 |
| 3 | Kaynak yok / erişilemez — `exists` `false` döner (silinmiş veya izinsiz, ayrım yapılmaz — kullanıcı kararı) | `{selectedFolder: normalizedPath (korunur), isFolderInvalid: true}` | Yok (diske hiçbir yazma tetiklenmez) | Path korunur + kırmızı hata mesajı, Devam disabled | AC-2 |
| 7 | Kısmi başarı | — | — | — | Bu task'ta geçerli değil — kontrol atomik bir boolean sonucu, ara durum yok. Satır silindi. |
| 8 | Hiçbir şey yapılamadı ama hata da yok | `invoke('plugin:fs|exists', ...)` reddedilirse (Promise rejection — örn. beklenmeyen bir Tauri IPC hatası) | Yok | `isFolderInvalid: true` set edilip AC-2 ile aynı hata gösterilir — invoke reddi de "erişilemez" kapsamına dahil edilir, sessiz başarı YASAK | AC-2 (genişletilmiş varsayım, bkz. Assumptions) |

Kısmi başarı: Geçerli değil — `exists` kontrolü tek bir boolean dönen atomik bir işlem, ara durum yok.
Hiçbir şey yapılamadı ama hata da yok: `invoke` reddedilirse (network/IPC seviyesinde beklenmeyen hata) bile `isFolderInvalid: true` set edilir — asla sessizce "her şey yolunda" varsayılmaz.
Boş sonuç ↔ hata ayrımı: Bu task'ta geçerli değil — `exists` sonucu zaten boolean, "veri yok" durumu söz konusu değil.
Yetkisiz erişim satırı silindi: kullanıcı kararıyla "yok" ve "izinsiz" durumları ayrılmıyor, ikisi de satır 3'teki tek "erişilemez" durumuna dahil.
Dış bağımlılık hatası / Zaman aşımı satırları silindi: `plugin:fs|exists` local bir Tauri IPC çağrısı, ağ/DB çağrısı değil; zaman aşımı senaryosu bu task kapsamında anlamlı değil.

## Test Strategy
Unit: 70% — `OnboardingScreen.test.tsx`: mock `__TAURI_INTERNALS__.invoke` ile `plugin:fs|exists` true/false/reject senaryoları, trim/normalize mantığı, hata mesajı görünürlüğü, yeniden seçimde temizlenme (AC-1..AC-5 hepsi).
Integration: 0% — backend/API entegrasyonu bu task kapsamında yok (bkz. Kapsam Dışı).
E2E: 30% — `onboarding.spec.ts`: gerçek tarayıcıda mock Tauri invoke ile erişilemez klasör seçimi, kırmızı hata mesajının görünmesi, yeniden seçimle düzelmesi.

## Benchmark / Başarı Ölçütü
Coverage Target: 90% (önceki task ile tutarlı varsayılan, kullanıcı spesifik sayı vermedi)
Performance Target: yok
Memory: yok
Görsel/UI kriteri: Kenarlık/mesaj rengi `#DC2626`, mesaj metni tam olarak "Seçilen klasöre erişilemiyor. Lütfen başka bir klasör seçin." — `verify` adımında ekran görüntüsüyle doğrulanmalı (Codex vision-test kotası dolu olduğu için manuel/Playwright screenshot yöntemiyle, bkz. bos-istek-engelleme task'ındaki emsal).
Diğer ölçülebilir kriterler: Kabul kriteri sahibi otomatik testler (unit+e2e yeşile dönerse task tamamlanmış sayılır).

## Kapsam Dışı
- Gerçek `@tauri-apps/plugin-fs` paketinin eklenmesi ve `src-tauri/` native kabuğunun scaffold edilmesi — bu task sadece mock'lanabilir bir `invoke('plugin:fs|exists', ...)` sözleşmesi kurar, gerçek dosya sistemi entegrasyonu ayrı bir task (native paketleme, #250'de de bilinçli olarak dışarıda bırakılmıştı).
- Backend'de bir doğrulama endpoint'i eklenmesi — kullanıcı frontend/Tauri-mock yaklaşımını seçti.
- "Yok" ile "izinsiz" hata nedenlerinin ayrı mesajlarla gösterilmesi — tek bir "erişilemez" mesajı yeterli.
- Kapsamlı path normalization (case normalization, sembolik link çözümleme) — sadece trailing slash/backslash temizleniyor.
- Diske yazma başlamadığına dair ayrı bir test — bu bir invariant olarak kabul edildi (onboarding adımında zaten hiçbir yazma çağrısı yok), ayrı bir spy/test yazılmayacak.

## Etkilenen Dosyalar/Modüller (bilinen)
- `ui/src/components/onboarding/OnboardingScreen.tsx` (chooseFolder, yeni `isFolderInvalid` state, normalize + invoke mantığı)
- `ui/src/components/onboarding/OnboardingScreen.test.tsx` (yeni unit testler, `__TAURI_INTERNALS__.invoke` mock genişletmesi)
- `ui/e2e/onboarding.spec.ts` (yeni e2e senaryoları)

## Rollback Beklentisi
Geçerli değil — state'siz, yan etkisiz bir UI validasyonu; DB/dosya değişikliği yok, standart `git revert` yeterli. Ayrıca bu değişiklik zaten hiçbir disk yazma işlemi başlatmıyor (invariant korunuyor).

## Risks
- Race condition: kullanıcı hızlıca art arda birden fazla klasör seçerse, önceki bir `exists` invoke'unun geç dönen sonucu daha yeni bir seçimin state'ini geçersiz kılabilir (stale response). Implementasyon bunu (örn. en son seçilen path'i referans alarak) ele almalı, code-copilot'a not düşülecek.
- Mock/gerçek API uyuşmazlığı riski (kullanıcı onayıyla eklendi): İleride gerçek `@tauri-apps/plugin-fs` eklendiğinde, bu task'ta kurulan `invoke('plugin:fs|exists', {path})` mock sözleşmesinin gerçek plugin-fs API'sinin dönüş tipi/parametre imzasıyla birebir eşleşmesi gerekiyor — eşleşmezse mock'lanan testler yeşil kalırken gerçek entegrasyon kırılabilir. Gerçek paket eklendiğinde bu sözleşme yeniden doğrulanmalı.

## Assumptions
- `invoke('plugin:fs|exists', ...)` reddedilirse (Promise rejection) de AC-2 ile aynı "erişilemez" hatası gösterileceği varsayıldı (kullanıcıya ayrıca sorulmadı, sessiz başarı riskini önlemek için davranış sözleşmesi tablosunda 8. satır olarak eklendi — bkz. yukarıdaki tablo).
- Trailing slash/backslash temizleme için basit bir string trim (`path.replace(/[\\/]+$/, '')` benzeri) yeterli kabul edildi, ayrı bir path-parsing kütüphanesi gerekmiyor.

## Unknowns
- Gerçek `@tauri-apps/plugin-fs` entegrasyonu yapıldığında bu mock sözleşmesinin ne kadar değişeceği (bkz. Risks) — bu task'ın çözemeyeceği, ileride tekrar ele alınması gereken bir konu.

## Sorular ve Cevaplar (ham kayıt)
0. (ATDD öncesi, kod keşfi sonrası) src-tauri/plugin-fs yok, nasıl ilerlensin? → Mock'lanabilir Tauri invoke ile ilerle
1. Klasör erişilebilirlik kontrolü ne zaman tetiklenmeli? → Klasör seçildiği anda
2. Yeni mock invoke kontratı ne olmalı? → 'plugin:fs|exists' çağrılır, boolean döner
3. Geçersiz klasör seçilince mevcut path göstergesi ne olmalı? → Path görünür kalır + hata mesajı altında gösterilir
4. Yeniden seçim düğmesi için hangi yaklaşım? → Mevcut 'Klasör Seç' butonu yeterli
5. Hata mesajı metni ne olsun? → "Seçilen klasöre erişilemiyor. Lütfen başka bir klasör seçin."
6. Normalize kapsamı ne olmalı? → Sadece trailing slash/backslash temizleme
7. Erişilemez klasör nedenleri ayrı mı ele alınsın? → Hayır, tek bir "erişilemez" durumu yeterli
8. "Diske yazma başlatmamalı" kısıtı nasıl ele alınsın? → Invariant olarak not edilir, ayrı test gerekmez
9. Test stratejisi oranı (70/0/30) uygun mu? → Evet
10. Kabul kriteri sahibi kim? → Otomatik testler (unit+e2e) yeşile dönerse yeterli
11. Task-slug 'gecersiz-klasor-reddi' uygun mu? → Evet
12. Risk/varsayım eklensin mi (mock/gerçek API uyuşmazlığı)? → Evet, eklendi
