---
task_slug: plani-degistir-duzenleme-baglami
priority: high
coverage_target: "AC'lerin tamamı unit test ile kapsanır"
performance_target: "yok (UI katmanı, ölçülebilir performans hedefi yok)"
test_strategy: "70/0/30 (unit/integration/e2e) — proje zaten vitest+RTL unit altyapısına sahip"
affected_modules: ["ui/src/components/chat/PlanCard.tsx", "ui/src/components/chat/ChatScreen.tsx"]
---

# Planı değiştir düğmesinin sohbet girişine düzenleme bağlamı eklemesini sağla (Saga #264)

## Persona
Bir plan öneren asistan mesajını inceleyen, planı olduğu gibi onaylamak istemeyen kullanıcı.

## Goal
"Planı değiştir" seçildiğinde onay verilmez; yazma alanı odaklanır ve kullanıcı
talebini düzenlemeye yönlendiren kısa bir ipucu gösterilir. Yeni mesaj önceki
planı geçersiz kılar ve yeni plan üretim akışını başlatır.

## User Story
Bir kullanıcı olarak, önerilen bir planı beğenmediğimde "Planı değiştir" diyebilmek
ve doğrudan yazma alanına yönlendirilip isteğimi netleştirebilmek istiyorum, böylece
yanlış bir planı yanlışlıkla onaylamam ve düzeltme isteğimi kolayca iletebilirim.

## Acceptance Criteria (öncelik sırasına göre)
1. PlanCard'da bir "Planı değiştir" düğmesi bulunur; tıklanınca `onApprove`
   ÇAĞRILMAZ (onay verilmez).
2. "Planı değiştir" tıklanınca sohbet yazma alanı (textarea) odaklanır.
3. "Planı değiştir" tıklanınca kullanıcıyı düzenlemeye yönlendiren kısa bir ipucu
   metni (ör. "Planı değiştirmek için ne yapmak istediğinizi yazın.") görünür olur.
4. Kullanıcı yeni bir mesaj gönderdiğinde, değiştirilmesi istenen plan geçersiz
   (stale) olarak işaretlenir — o planın onay düğmesi kalıcı olarak devre dışı
   kalır ve "Bu plan artık geçerli değil, yeni plan bekleniyor." metni görünür.
5. Yeni mesaj normal `onSendMessage` akışıyla gönderilir (yeni plan üretim akışını
   tetikleyen taraf backend/LLM entegrasyonudur — bu task'ın kapsamı DIŞINDA,
   sadece istemci tarafı geçersiz kılma + normal gönderim garanti edilir).

## Behaviour-contract tablosu
| Durum | Beklenen davranış |
|---|---|
| "Planı değiştir" tıklanır | `onApprove` çağrılmaz, textarea focus alır, ipucu metni görünür |
| İpucu görünürken kullanıcı boş mesaj gönderir | Mesaj gönderilmez (mevcut boş-mesaj engeli korunur), plan stale OLMAZ |
| İpucu görünürken kullanıcı geçerli mesaj gönderir | Mesaj gönderilir, ilgili plan stale işaretlenir, ipucu kaybolur |
| Stale plan | Onay düğmesi kalıcı disabled, "Bu plan artık geçerli değil…" metni gösterilir (rejection/pending metninin yerini alır) |
| Plan zaten onaylanmış (hasApproved) iken "Planı değiştir" | Düğme yine çalışır (onaylanmış bir planı da değiştirmek isteyebilir) — kapsam: davranış aynı, onApprove yine çağrılmaz |

## Risks/Assumptions/Unknowns
- Assumption: "Yeni plan üretim akışını başlatır" ifadesi bu task'ta sadece
  `onSendMessage` callback'inin normal şekilde çağrılması olarak yorumlandı;
  gerçek LLM/backend yeniden-plan-üretme entegrasyonu henüz yok (265/266/267
  civarında gelecek). Dar kapsam ilkesi. (saga-oto tarafından otomatik seçildi)
- Assumption: Stale işaretleme sadece "değiştir" tıklanan spesifik mesaja
  uygulanır, aynı anda birden fazla plan "değiştir" bekleyebilir mi sorusu için
  tek seferde tek bir `editingPlanMessageId` yeterli kabul edildi (aynı anda
  tek bir yazma alanı olduğu için kullanıcı zaten sırayla işlem yapar).
  (saga-oto tarafından otomatik seçildi)
- Risk: Stale işaretleme sadece görsel/erişilebilirlik seviyesinde — gerçek
  bir "plan artık backend'de geçersiz" garantisi yok (backend entegrasyonu
  kapsam dışı, ayrı task'larda gelecek).

## Test Strategy
70/0/30 unit/integration/e2e. `PlanCard.test.tsx`'e yeni testler + `ChatScreen.test.tsx`'e
entegrasyon testleri (RTL, vitest).

## Benchmark
Kabul kriteri: `npx vitest run` içinde tüm testler yeşil.

## Sorular ve Cevaplar (saga-oto otomatik)
- S: "Yeni plan üretim akışı" bu task'ta gerçekten backend'e istek mi atar?
  C: Hayır, dar kapsam — mevcut `onSendMessage` callback'i zaten bu işi
  temsil ediyor, yeni bir mekanizma icat edilmedi. (saga-oto tarafından
  otomatik seçildi)
- S: İpucu metni nerede gösterilir? C: Yazma alanının hemen üstünde, aria-live
  polite bölgede — düşük maliyetli erişilebilirlik. (saga-oto tarafından
  otomatik seçildi)
