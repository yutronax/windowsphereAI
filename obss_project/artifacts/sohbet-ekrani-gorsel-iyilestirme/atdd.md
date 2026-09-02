---
task_slug: sohbet-ekrani-gorsel-iyilestirme
jira_id: null
saga_task_id: 353
priority: medium
coverage_target: 90
performance_target: null
memory_target: null
test_strategy:
  unit: 55
  integration: 25
  e2e: 20
affected_modules:
  - ui/src/components/chat/ChatScreen.tsx
  - ui/src/components/chat/TransactionHistoryPanel.tsx
  - ui/src/tokens.ts
  - ui/src/components/common/Button.tsx
  - ui/src/components/common/Card.tsx
---

# ATDD — sohbet-ekrani-gorsel-iyilestirme

## Jira Kaynağı
Jira'ya bağlı değil — yerel görev. Saga Epic #38 ("Sohbet Ekranı Görsel İyileştirme") ve Saga Task #353 üzerinden takip ediliyor.

## Persona
Uygulamanın tek kullanıcı tipi: whitelisted bir klasörde doğal dilde dosya işlemi yapan masaüstü son kullanıcısı. (kullanıcı mesajından: sadece "saga epic 38 den devam" denildi, persona doğrudan belirtilmedi → Haiku alt-ajanı tarafından yanıtlandı: bağlamda tanımlı tek kullanıcı tipi bu.)

## Hedef (Neden)
Epic #36 (Tasarım Sistemi Temeli) merkezi bir `ui/src/tokens.ts` üretti ama hiçbir bileşen henüz onu kullanmıyor — ChatScreen.tsx ve TransactionHistoryPanel.tsx hâlâ kendi inline `<style>` bloklarında/inline style prop'larında aynı hex renkleri tekrar tanımlıyor. Bu görev bu tekrarlanan inline stil kod borcunu kaldırıp tasarım tutarlılığını sağlıyor. (Haiku alt-ajanı tarafından yanıtlandı: Epic #36/#38 açıklamalarından çıkarım.)

## User Story
As a masaüstü son kullanıcısı
I want ChatScreen ve sol panelin (TransactionHistoryPanel) tutarlı, merkezi token'lara dayalı bir görsel dile sahip olmasını
So that uygulama genelinde tutarlı ve profesyonel görünen bir deneyim yaşayayım (davranış/veri akışı hiç değişmeden)

## Acceptance Criteria (Given-When-Then, önceliklendirilmiş)
1. [Critical] Given ChatScreen.tsx ve TransactionHistoryPanel.tsx'in mevcut inline `<style>`/style-prop hex renkleri, When bu bileşenler `tokens.ts`'i import edecek şekilde güncellenir, Then aynı görsel çıktı (renk/boyut/radius birebir aynı) korunurken kaynak kodda ham hex renk sayısı 0'a iner.
2. [Critical] Given mevcut Button/Card kullanım noktaları (Gönder, Tekrar dene, Dosya ara, Geçmişi Temizle butonları vb.), When ortak `Button`/`Card` primitifleri (Epic #36) uygulanabilir olduğu yerlerde kullanılır, Then buton/panel görünümü tokens ile tutarlı hale gelir ve mevcut `data-testid`/aria özellikleri değişmeden kalır.
3. [Critical] Given mevcut tüm ChatScreen/TransactionHistoryPanel testleri, When bu görsel taşıma tamamlanır, Then testlerin %100'ü regresyonsuz geçer (davranış/veri akışı değişmez).
4. [High] Given TransactionHistoryPanel'in `connectionStatus === 'disconnected'` durumu, When bileşen tokens'a taşınır, Then kırmızı renk `tokens.colors.danger` üzerinden ifade edilir (aynı hex değer, farklı kaynak).
5. [High] Given `tokens.ts`'te karşılığı olmayan danger açık/koyu tonları (plan-error-indicator: #FEF2F2/#FCA5A5/#B91C1C, clear-history-error: #FEE2E2/#FECACA/#991B1B), When taşıma yapılır, Then `tokens.ts` bu tonlar için yeni alanlarla (örn. `colors.dangerLight`, `colors.dangerBorder`, `colors.dangerText`) genişletilir — mevcut hex değerler birebir korunarak.
6. [Medium] Given görsel taşıma sonrası component/lint/build adımları, When `verify` adımı çalıştırılır, Then build/lint hatasız geçer ve hiçbir `data-testid` yanlışlıkla silinmemiş olur.

## Agentic Değerlendirme Kriterleri
(tetikleyici yok — bu görev bir LLM agent/sub-agent tool-calling davranışını veya prompt'unu değiştirmiyor, saf frontend CSS/token taşıma işi)

## Davranış Sözleşmesi (hangi durumda ne döner)
| # | Durum | Dönen değer / durum kodu | Yan etki | Kullanıcı ne görür | AC |
|---|---|---|---|---|---|
| 1 | Happy path — taşıma tamamlanır | N/A (derleme/render başarılı) | Kaynak dosyalarda hex yerine `tokens.*` referansı | Aynı görsel sonuç, fark edilmez | AC-1, AC-2 |
| 2 | Build/lint hatası (yanlış import/tip hatası) | Build/lint görev başarısız (exit ≠ 0) | Kod merge edilmez | CI/verify adımında hata çıktısı | AC-6 |
| 3 | Bir `data-testid` yanlışlıkla silinirse | İlgili test(ler) FAIL döner | Mevcut test suite kırılır | `verify`/test raporunda başarısız test | AC-3, AC-6 |
| 7 | Kısmi başarı (bazı hex'ler taşınmış, bazıları kalmış) | Görev "tamamlanmadı" sayılır — Kabul Kriteri #1 karşılanmaz | Kaynak kodda hâlâ ham hex var | Code review'da kalan hex'ler görülür, AC-1 FAIL | AC-1 |
| 8 | Hiçbir şey yapılamadı ama hata da yok (örn. dosyalar zaten değişmemiş halde "başarılı" raporlanır) | YASAK — code-copilot/verify çıktısı, değişen dosya listesi boşsa görevi "başarısız/yapılmadı" olarak raporlamalı, "success" dönmemeli | Yok | Kullanıcı diff'te değişiklik görmez ve bu açıkça raporlanır | AC-1 |

Kısmi başarı: Bazı bileşenler tokens'a taşınmış bazıları kalmışsa görev tamamlanmamış sayılır; `verify` adımı ham hex sayısının 0 olduğunu doğrulamadan "done" işaretlenmez.
Hiçbir şey yapılamadı ama hata da yok: Sessiz başarı YASAK — code-copilot bir dosyada değişiklik yapamadıysa (örn. dosya bulunamadı, yazma izni yok) bunu açıkça "değişiklik yapılmadı" olarak raporlamalı, "tamamlandı" dememeli.
Boş sonuç ↔ hata ayrımı: Bu görevde "boş sonuç" kavramı geçerli değil (API/veri çağrısı yok) — silindi, çünkü CSS/token taşıma işlemi bir sorgu/liste döndürmüyor.

## Test Strategy
Unit: 55% — tokens.ts'in doğru re-export ettiği değerler, Button/Card primitiflerinin prop/stil davranışı
Integration: 25% — ChatScreen ve TransactionHistoryPanel'in mevcut render/etkileşim testleri (mesaj gönderme, plan onaylama, geçmiş temizleme, arama paneli açma) regresyonsuz geçmeli
E2E: 20% — vision-test skill'i ile öncesi/sonrası görsel karşılaştırma (verify adımında)

## Benchmark / Başarı Ölçütü
Coverage Target: 90%
Performance Target: yok (saf CSS değişikliği, performans etkisi beklenmiyor)
Memory: yok
Görsel/UI kriteri: ChatScreen.tsx ve TransactionHistoryPanel.tsx'teki ham hex renk sayısı 0'a iner; `tokens.ts` kullanım oranı %100; mevcut tüm testler %100 regresyonsuz geçer; görsel çıktı öncesiyle pixel-perfect aynı kalır (bkz. vision-test, `verify` adımında).
Diğer ölçülebilir kriterler: `tokens.ts` içine eklenen yeni danger-tonu alanları (varsa) mevcut hex değerlerle birebir eşleşir.

## Kapsam Dışı
- Yeni özellik eklemek
- PlanCard.tsx / ResultCard.tsx'e dokunmak (ayrı epic — Saga Epic #39: Plan/Sonuç Kartları Tasarımı)
- Dark mode / açık tema desteği (ayrı epic — Saga Epic #41)
- SearchPanel.tsx görsel tutarlılığı (ayrı epic — Saga Epic #40)
- Layout veya veri akışı/davranış değişikliği
- Erişilebilirlik (aria-*, role) özelliklerinin değiştirilmesi — sadece korunacak

## Etkilenen Dosyalar/Modüller (bilinen)
- ui/src/components/chat/ChatScreen.tsx
- ui/src/components/chat/TransactionHistoryPanel.tsx
- ui/src/tokens.ts (muhtemel genişletme: danger tonları)
- ui/src/components/common/Button.tsx, Card.tsx (varsa, Epic #36 primitifleri — kullanılabilir olduğu yerlerde)

## Proje Ortamı Kısıtı (arama/grep kapsamı)
Doğrulanmadı — bu makinede git reposunun kökü proje klasörüyle birebir aynı mı (windows-ai-files) net değil; sonraki adımlarda (plan/code-copilot/test-copilot/red-team) Grep/Glob/Bash araması her zaman gerçek proje klasörü (`ui/src/...`) ile sınırlanmalı, kök dizinden sınırsız arama yapılmamalı.

## Rollback Beklentisi
Görsel regresyon (bir bileşen bozuk görünürse) fark edilirse `vision-test` skill'i ile `verify` adımında yakalanmalı; yakalanırsa ilgili commit git revert ile geri alınır. (Haiku alt-ajanı tarafından yanıtlandı: vision-test + git revert kombinasyonu önerildi.)

## Risks
- tokens.ts'in mevcut inline hex değerlerle birebir eşleşmediği bir durum bulunursa (örn. `danger` tonunun ChatScreen'deki gerçek kullanımdan farklı bir hex olması) sessizce "iyileştirme" yapılıp pixel-perfect kural çiğnenebilir — bu görevde YASAK, ayrı bir görev olarak ele alınmalı.
- Button/Card primitiflerinin ChatScreen'deki tüm buton varyantlarını (disabled, danger/retry, toggle) karşılamaması riski — karşılamıyorsa o buton primitif kullanılmadan sadece tokens ile stillenir.

## Assumptions
- tokens.ts'teki renk değerleri mevcut inline hex değerlerle birebir aynı kabul edildi (pixel-perfect taşıma) — bu görev sırasında ton/spacing iyileştirmesi YAPILMAYACAK. (varsayım, Haiku alt-ajanı tarafından yanıtlandı)
- Otomatik testler (mevcut unit/integration + linter) kabul kriteri için yeterli kabul edildi; ayrıca kullanıcı screenshot incelemesi de (vision-test üzerinden) verify adımında yapılacak. (varsayım, Haiku alt-ajanı tarafından yanıtlandı)
- Performans/güvenlik kısıtı yok (saf CSS/inline-style → token taşıması). (varsayım, Haiku alt-ajanı tarafından yanıtlandı)

## Unknowns
- `ui/src/components/common/Button.tsx` ve `Card.tsx` dosyalarının gerçekten mevcut olup olmadığı ve ChatScreen'deki tüm buton varyantlarını (disabled state, danger/retry rengi, toggle) karşılayıp karşılamadığı — `plan` adımında doğrulanmalı.
- tokens.ts'in danger açık/koyu tonlarıyla genişletilip genişletilmeyeceği kesin değil; genişletilecekse alan isimlendirmesi (`dangerLight`/`dangerBorder`/`dangerText` vb.) `plan` adımında netleştirilmeli.

## Sorular ve Cevaplar (ham kayıt)
(Tüm sorular Haiku alt-ajanı tarafından yanıtlandı — claude-omni denemesi bağlamı kaçırıp alakasız bir yanıt döndürdüğü için kullanılmadı, sessizce Haiku fallback'ine düşüldü.)

1. Kullanıcı rolü/persona: Masaüstü son kullanıcısı (whitelisted klasörde doğal dilde dosya işlemi yapan) — bağlamda tanımlı olması ve başka persona bahsedilmemesi. (Haiku alt-ajanı tarafından yanıtlandı)
2. Ana hedef/neden: Tekrarlanan inline stil kod borcunu kaldırarak (hex renkleri tokens.ts'e taşıyarak) tasarım tutarlılığını sağlamak — Epic #36 tokens.ts'i zaten üretti ama hiçbir bileşen kullanmıyor. (Haiku alt-ajanı tarafından yanıtlandı)
3. Happy path senaryosu: Kullanıcı ChatScreen'i açtığında mesaj balonları, butonlar, paneller tokens.ts'teki tutarlı renkleri kullanmalı ve Button/Card primitifleri ile render edilmeli — veri/layout değişmez, sadece stil kaynağı değişir. (Haiku alt-ajanı tarafından yanıtlandı)
4. Edge case 1 (disconnected): TransactionHistoryPanel bağlantı durumu göstergesi tokens.colors.danger ile ifade edilmeli — mevcut #DC2626'nın tokens karşılığı. (Haiku alt-ajanı tarafından yanıtlandı)
5. Edge case 2 (renk varyantları): tokens.ts genişletilmeli (danger'ın açık/koyu tonları eklenmeli), mevcut hex değerler birebir korunarak. (Haiku alt-ajanı tarafından yanıtlandı)
6. Davranış sözleşmesi: Build/lint hatası = regresyon, data-testid silinmesi = test başarısızlığı → PR merge edilmez. (Haiku alt-ajanı tarafından yanıtlandı)
7. Başarı ölçütü: Ham hex renk sayısı 0, tokens.ts kullanım %100, mevcut testlerin %100'ü geçer. (Haiku alt-ajanı tarafından yanıtlandı)
8. Kapsam dışı: Yeni özellik, davranış/veri akışı değişikliği, PlanCard/ResultCard, dark mode, layout değişikliği, accessibility değişikliği. (Haiku alt-ajanı tarafından yanıtlandı)
9. Bağımlılıklar: ChatScreen.tsx, TransactionHistoryPanel.tsx, tokens.ts, Button.tsx, Card.tsx — başka dosya eklenmeyecek. (Haiku alt-ajanı tarafından yanıtlandı)
10. Performans/güvenlik kısıtı: Yok. (Haiku alt-ajanı tarafından yanıtlandı)
11. Rollback beklentisi: vision-test ile PR review'da yakalanır, gerekirse git revert. (Haiku alt-ajanı tarafından yanıtlandı)
12. Kabul kriteri sahibi: Otomatik testler yeterli, ayrıca görsel onay (screenshot review) de yapılabilir. (Haiku alt-ajanı tarafından yanıtlandı)
13. Test stratejisi oranı: unit/integration ~%80 (bu atdd.md'de 55/25 olarak ayrıştırıldı), vision-test ~%20. (Haiku alt-ajanı tarafından yanıtlandı — atdd.md'ye yazarken unit/integration ayrımı netleştirildi)
14. Bilinen riskler/varsayımlar: tokens.ts renkleri mevcut hex'lerle birebir aynı olmalı, pixel-perfect taşıma; ton iyileştirmesi bu görevde değil. (Haiku alt-ajanı tarafından yanıtlandı)
