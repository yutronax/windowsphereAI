---
task_slug: plan-result-kartlari-tasarim
jira_id: null
saga_task_id: 355
priority: medium
coverage_target: 90
performance_target: null
memory_target: null
test_strategy:
  unit: 80
  integration: 20
  e2e: 0
affected_modules:
  - ui/src/components/chat/PlanCard.tsx
  - ui/src/components/chat/ResultCard.tsx
  - ui/src/components/chat/PlanCard.test.tsx
  - ui/src/components/chat/ResultCard.test.tsx
  - ui/src/components/primitives/Button.tsx
  - ui/src/components/primitives/Card.tsx
  - ui/src/tokens.ts
---

# ATDD — plan-result-kartlari-tasarim

## Jira Kaynağı
Jira'ya bağlı değil — yerel görev. Saga Epic #39 "Plan/Sonuç Kartları Tasarımı" (proje: windows-ai-files, id 2), Saga Task #355.

## Persona
Teknik/ileri düzey kullanıcı — dosya operasyon planlarını (taşı/kopyala/sil/yeniden adlandır) onaylayan, fail-closed güvenlik kültürüne alışkın kişi. (Haiku alt-ajanı tarafından yanıtlandı: uygulamanın "onaylanmamış plan asla çalışmaz" güvenlik modeli ileri-düzey/teknik kullanıcı varsayımını destekliyor.)

## Hedef (Neden)
Epic #36'da kurulan merkezi design token (`tokens.ts`) ve primitif katmanı (`Button`, `Card`) ChatScreen'e taşındı ama PlanCard.tsx ve ResultCard.tsx hâlâ kendi inline `<style>` bloklarında ham hex renkler kullanıyor — tasarım sistemi tutarsız. Bu görev bu iki bileşeni primitiflere taşıyarak tutarlılığı tamamlar. (Haiku alt-ajanı tarafından yanıtlandı: proje bağlamından — epic açıklaması + tamamlanmış #36 epic'in kapsamı.)

## User Story
As a teknik kullanıcı
I want Plan ve Sonuç kartlarının buton/kart görünümünün ChatScreen ile tutarlı olmasını
So that arayüz tüm ekranlarda aynı tasarım dilini kullansın ve bakım tek noktadan (tokens.ts) yapılabilsin

## Acceptance Criteria (Given-When-Then, önceliklendirilmiş)
1. [Critical] Given PlanCard render edildiğinde, When mevcut testler (`PlanCard.test.tsx`) çalıştırıldığında, Then tüm testid'ler ve davranışlar (fail-closed onay, bulk-confirm eşiği) değişmeden yeşil kalır.
2. [Critical] Given ResultCard render edildiğinde, When mevcut testler (`ResultCard.test.tsx`) çalıştırıldığında, Then tüm testid'ler ve davranışlar (revert akışı, preview yükleme) değişmeden yeşil kalır.
3. [Critical] Given PlanCard/ResultCard kaynak kodu, When inline `<style>` blokları incelendiğinde, Then hardcoded hex renk kalmaz — tüm renkler `tokens.ts`'den gelir (doğrudan veya `Button`/`Card` primitifleri üzerinden).
4. [High] Given PlanCard'ın "Planı onayla" ve "Planı değiştir" butonları, When primitiflere taşındığında, Then `<Button variant="primary">` / uygun variant kullanılır, `disabled`/`canApprove` mantığı satır satır aynı kalır.
5. [High] Given bulk-confirm akışı (`plan-bulk-confirm-button`, `plan-bulk-confirm-cancel-button`), When primitife taşındığında, Then `BULK_CONFIRM_THRESHOLD` mantığı ve iki-adımlı onay akışı değişmeden korunur.
6. [High] Given ResultCard'daki dolu-kırmızı (`result-card-revert-confirm-btn`) ve outline-kırmızı (`result-card-revert-btn`) butonlar, When Button primitifi (şu an sadece dolu `danger` variant destekliyor) kullanılmaya çalışıldığında, Then outline stil için ya yeni bir `danger-outline` variant eklenir ya da bu buton bilinçli olarak component-local stilde bırakılır (bkz. Assumptions).
7. [Medium] Given PlanCard/ResultCard sarmalayıcı `<section>` elemanları, When primitife taşındığında, Then `<Card>` bileşeni kullanılır, `data-testid`/`aria-label` korunur.

## Davranış Sözleşmesi (hangi durumda ne döner)
| # | Durum | Dönen değer / durum kodu | Yan etki | Kullanıcı ne görür | AC |
|---|---|---|---|---|---|
| 1 | Happy path — securityStatus="approved" | `plan-approve-button` enabled, onClick → `onApprove` | `hasApproved=true` | Tıklanabilir onay butonu | AC-1, AC-4 |
| 2 | securityStatus henüz gelmemiş (pending) | `plan-approve-button` disabled (`canApprove=false`) | yok | "Güvenlik kontrolü bekleniyor…" metni | AC-1, AC-4 |
| 3 | securityStatus="rejected" | `plan-approve-button` disabled, `plan-rejection-reason` testid'li metin render | yok | Ret nedeni (kırmızı metin) | AC-1, AC-4 |
| 4 | stale=true | Tüm onay/değiştir butonları disabled | yok | "Bu plan artık geçerli değil…" metni | AC-1, AC-4 |
| 5 | Bulk (>20 dosya) — 1. tık | `isConfirmingBulk=true`, ikinci onay UI'ı açılır | yok | `plan-bulk-confirm-button`/`-cancel-button` + uyarı metni | AC-1, AC-5 |
| 6 | Bulk — 2. tık (onayla) | `hasApproved=true`, `onApprove` çağrılır | yok | Onay tamamlanır | AC-1, AC-5 |
| 7 | isGeneratingPlan=true | `plan-approve-button` VE `plan-change-button` disabled | yok | Her iki buton kilitli | AC-1, AC-4 |
| 8 | ResultCard revert: idle→confirming | `result-revert-confirm-button`/`-cancel-button` render | yok | "Evet, geri al" / "Vazgeç" | AC-2 |
| 9 | ResultCard revert: reverting | Buton disabled, "Geri alınıyor…" metni | POST `/api/transactions/{id}/revert` | Buton kilitli, bekleme metni | AC-2 |
| 10 | ResultCard revert: reverted | `result-revert-status-text` = "İşlem geri alındı." | yok | Başarı metni, buton kaybolur | AC-2 |
| 11 | ResultCard revert: revert_failed | `result-revert-status-text.is-failed` | yok | "…bazı dosyalar geri taşınamadı." | AC-2 |
| 12 | ResultCard revert: error (network) | `result-revert-status-text.is-failed` + `result-revert-retry-button` | yok | Hata metni + "Tekrar dene" butonu | AC-2 |
| 13 | Preview hover-lazy yüklenirken | `result-preview-loading` testid'li metin | GET `/api/transactions` (bir kez) | "Önizleme yükleniyor…" | AC-2 |
| 14 | Preview hata | `result-preview-error` testid'li metin | yok | "Önizleme yüklenemedi." | AC-2 |

Kısmi başarı: Uygulanmaz — bu görev saf CSS/primitif taşıma, kısmi taşıma "bir kısım primitif kullanıyor bir kısım hâlâ inline style" durumunda AC-3 (hardcoded hex kalmaması) FAIL sayılır, PR tamamlanmış sayılmaz.

Hiçbir şey yapılamadı ama hata da yok: Uygulanmaz — bu görev deterministik bir kod taşıma işi, "sessiz başarı" riski yok; başarı/başarısızlık doğrudan test sonucuyla (yeşil/kırmızı) ve statik hex-tarama sonucuyla ölçülür.

Boş sonuç ↔ hata ayrımı: Uygulanmaz — bu görevde "boş sonuç" kavramı yok (UI bileşen refactor'ı, veri sorgusu değil).

## Test Strategy
Unit: 80% — PlanCard.test.tsx, ResultCard.test.tsx, Button.test.tsx, Card.test.tsx (mevcut testler + gerekirse yeni variant testleri)
Integration: 20% — Button/Card primitiflerinin PlanCard/ResultCard içinde doğru prop'larla (variant, disabled, onClick, data-testid) render edildiğinin doğrulanması
E2E: 0% — CSS/primitif taşıma saf refactor, e2e ek değer katmıyor (Haiku alt-ajanı gerekçesi, proje tipine göre makul varsayım — kullanıcı onayı bekleniyor)

## Benchmark / Başarı Ölçütü
Coverage Target: 90%
Performance Target: yok
Memory: yok
Görsel/UI kriteri: Buton/kart görünümü ChatScreen ile tutarlı (aynı token'lar); fail-closed onay ve bulk-confirm akışının görsel/etkileşim davranışı pixel-seviyesinde olmasa da davranışsal olarak birebir korunmalı — `verify` adımında `vision-test` skill'iyle ChatScreen ile görsel tutarlılık kontrol edilebilir.
Diğer ölçülebilir kriterler: PlanCard.tsx/ResultCard.tsx içinde `grep -E "#[0-9A-Fa-f]{3,6}"` taraması 0 sonuç döner (tüm renkler tokens.ts'den).

## Kapsam Dışı
- Buton/onay/bulk-confirm/revert **davranış mantığının** değişmesi (sadece görsel/primitif taşıma).
- Yeni özellik eklenmesi (örn. yeni bir buton, yeni bir durum).
- Dark mode desteği (ayrı epic #41, bağımlı).
- Backend/API değişikliği.
- Performans optimizasyonu.

## Etkilenen Dosyalar/Modüller (bilinen)
- ui/src/components/chat/PlanCard.tsx
- ui/src/components/chat/ResultCard.tsx
- ui/src/components/chat/PlanCard.test.tsx
- ui/src/components/chat/ResultCard.test.tsx
- ui/src/components/primitives/Button.tsx (muhtemelen yeni variant gerekebilir)
- ui/src/components/primitives/Card.tsx
- ui/src/tokens.ts (okuma amaçlı, muhtemelen değişmez)

## Proje Ortamı Kısıtı (arama/grep kapsamı)
Doğrulanmadı — proje kökü `C:\Users\YUSUF ÇİNAR\OneDrive\Belgeler\Masaüstü\projelerim\Yazılım_müh\windows-ai-files` olarak Saga proje description'ından biliniyor, ama bu dizinin git reposunun tam kökü olup olmadığı ve daha geniş/harici bir dizini kapsayıp kapsamadığı bu oturumda ayrıca doğrulanmadı. Sonraki adımlarda (plan/code-copilot/test-copilot/red-team) arama bu proje klasörüyle sınırlı tutulmalı.

## Rollback Beklentisi
Görsel taşıma bir testi kırarsa: (a) hangi testid/prop kaybolduğu veya `Button`/`Card` prop sözleşmesinin (disabled, onClick, className, data-testid) tam karşılanmadığı tespit edilir, (b) düzeltme yapılamıyorsa değişiklik geri alınır (git revert / stash), kırık test asla "beklenen" olarak işaretlenip görmezden gelinmez.

## Risks
- Button primitifi şu an sadece dolu (solid) `primary`/`danger` variant destekliyor; ResultCard'ın outline-kırmızı revert butonu için primitif genişletme gerekebilir — bu, planlama adımında netleştirilmesi gereken bir mimari karar.
- Mevcut testler class-name'e değil `data-testid`'e bağlı olduğu için taşıma riski düşük, ama `aria-describedby`/`aria-live` gibi erişilebilirlik davranışlarının primitife taşınırken kaybolmaması ayrıca doğrulanmalı.

## Assumptions
- (Varsayım, Haiku alt-ajanı önerisi) ResultCard'ın outline-danger butonu için Button primitifine yeni bir `danger-outline` variant eklenmesi tercih edilir; bu, `plan` adımında kullanıcıyla/mimari kararla netleştirilmeli — kesin karar bu ATDD'de verilmedi.
- (Varsayım) Kabul kriteri sahibi: otomatik testlerin (PlanCard.test.tsx + ResultCard.test.tsx) yeşil kalması temel kabul kriteri; kullanıcı görsel onayı ek/tercih edilir ama pazarlıksız değil.

## Unknowns
- Button primitifine yeni variant eklenip eklenmeyeceği (plan adımında netleştirilmeli).
- `verify` adımında `vision-test` ile görsel tutarlılık kontrolünün zorunlu mu opsiyonel mi olacağı.

## Sorular ve Cevaplar (ham kayıt)
1. Kullanıcı rolü/persona → (Haiku alt-ajanı tarafından yanıtlandı) Teknik kullanıcı, fail-closed onay kültürüne alışkın.
2. Ana hedef → (Haiku alt-ajanı tarafından yanıtlandı) Tasarım sistemi tutarlılığını PlanCard/ResultCard'a tamamlamak.
3. Happy path → (Haiku alt-ajanı tarafından yanıtlandı) Card/Button primitiflerine adım adım taşıma, testid'ler korunur.
4. Edge case 1 (bulk-confirm) → (Haiku alt-ajanı tarafından yanıtlandı) `<Button variant="primary">` + cancel için secondary/mevcut stil, davranış değişmez.
5. Edge case 2 (outline vs solid danger) → (Haiku alt-ajanı tarafından yanıtlandı) Yeni `danger-outline` variant önerisi veya component-local override; kesinleşmedi → Unknowns'a taşındı.
6. Davranış sözleşmesi tablosu → (Haiku alt-ajanı tarafından yanıtlandı, yukarıdaki tabloya işlendi).
7. Başarı ölçütü → (Haiku alt-ajanı tarafından yanıtlandı) Testler yeşil + hardcoded hex 0.
8. Kapsam dışı → (Haiku alt-ajanı tarafından yanıtlandı) Davranış değişikliği, yeni özellik, dark mode.
9. Bağımlılıklar → (Haiku alt-ajanı tarafından yanıtlandı) PlanCard/ResultCard + primitifler + tokens.ts + testler.
10. Test stratejisi oranı → (Haiku alt-ajanı tarafından yanıtlandı) 80/20/0 önerisi — kullanıcı onayı bekleniyor.
11. Rollback → (Haiku alt-ajanı tarafından yanıtlandı) Test kırılırsa kök neden bulunur, düzeltilemezse geri alınır.
12. Kabul kriteri sahibi → (Haiku alt-ajanı tarafından yanıtlandı) Otomatik test yeşili temel, kullanıcı görsel onayı tercih edilir.
