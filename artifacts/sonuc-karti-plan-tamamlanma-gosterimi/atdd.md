---
task_slug: sonuc-karti-plan-tamamlanma-gosterimi
priority: high
coverage_target: "70/0/30 (unit/integration/e2e)"
performance_target: "yok (native/backend performans kısıtı için kod tabanında aksini gösteren kanıt yok)"
test_strategy: "unit (React Testing Library, component-seviyesinde props ile izole)"
affected_modules:
  - ui/src/components/chat/ResultCard.tsx (yeni)
  - ui/src/components/chat/ChatScreen.tsx
saga_task_id: 277
epic_id: 25
---

# ATDD — Sonuç Kartı: Plan Tamamlanma Gösterimi (Saga #277)

## Persona
Klasörünü seçip PDF'lerini tarihe göre sıralatan, sonucu sohbet
akışında görmek isteyen son kullanıcı.

## Goal
Onaylanmış bir planın Orchestrator tarafından uygulanmasının ardından,
kaç dosyanın işlendiğini, hangi tarih klasörlerinin oluşturulduğunu ve
işlemin tamamlanma durumunu sohbet içinde açık bir kartla göstermek;
kullanıcının hemen ardından yeni bir istek yazabilmesini sağlamak.

## User Story
Kullanıcı olarak, onayladığım planın gerçekten uygulandığını ve kaç
PDF'in hangi klasörlere taşındığını görmek istiyorum ki işlemin
başarıyla bittiğinden emin olayım ve gerekirse hemen yeni bir istek
yazabileyim.

## Sorular ve Cevaplar (saga-oto tarafından otomatik seçildi)

**S1: Sonuç, `Plan` tipinin bir uzantısı mı (`securityStatus` gibi yeni
bir durum) yoksa ayrı bir tip mi olmalı?**
Cevap: Ayrı bir tip (`ChatMessage.result?: TransactionResult`).
Gerekçe: `Plan`/`PlanCard` zaten fail-closed ONAY sorumluluğuyla dolu
(securityStatus, canApprove, stale); sonuç göstermek anlamsal olarak
farklı bir sorumluluk (Recommended — tek sorumluluk ilkesi, mevcut
PlanCard karmaşıklığını artırmamak). (saga-oto tarafından otomatik
seçildi)

**S2: Backend'e bir response şeması/endpoint eklenmeli mi?**
Cevap: Hayır. Saga #274/#276'da `apply_plan()` bilinçli olarak
endpoint'siz bırakıldı (frontend'in gerçek `pdfFiles` kaynağı yok, Saga
#285). Bu task da aynı önkoşula takılıyor — `ResultCard` component
seviyesinde, mock/örnek `TransactionResult` props'uyla izole test
edilecek; gerçek HTTP wiring #285'in kapsamına bırakılıyor. Dar kapsam
ilkesi (Recommended). (saga-oto tarafından otomatik seçildi)

**S3: "Takip eden isteği yazabileceği etkin giriş alanı" için yeni bir
state (`isApplyingPlan` gibi) gerekiyor mu?**
Cevap: Hayır, bu task'ın kapsamında değil. Mevcut `isGeneratingPlan`
sadece plan ÜRETİMİNİ kilitliyor; `apply_plan` çalışırken ayrı bir
"uygulanıyor" göstergesi istenip istenmediği backend wiring'e (Saga
#285) bağlı, bugün test edilemez. `ResultCard` göründüğünde textarea
zaten `isGeneratingPlan=false` olduğu için açık kalır — bu, ek bir
state olmadan zaten sağlanan bir davranış. (saga-oto tarafından otomatik
seçildi, düşük riskli varsayım)

**S4: Kısmi/başarısız sonuç (rollback olmuş bir transaction) da bu
kartta mı gösterilmeli, yoksa bu task sadece "başarılı" senaryoyu mu
kapsıyor?**
Cevap: Task başlığı açıkça "Başarılı işlem sonucunu... göstermelidir"
diyor — kapsam SADECE başarılı/tamamlanmış sonuç. `status` alanı yine
de `'completed'|'partial'|'failed'` olarak genel tutulacak (backend
`Transaction.status` ile hizalı: committed/rolled_back), ama
`rejected`/`failed` durumunun kullanıcıya nasıl gösterileceği net hata
mesajı Saga #276'nın kapsamındaydı (backend tarafı hazır) — UI'da hata
kartı ayrı bir görselleştirme gerektirebilir, bu task'a dahil değil.
Dar kapsam (Recommended). (saga-oto tarafından otomatik seçildi)

## Kabul Kriterleri (öncelik sırasıyla)

1. **AC-1 (kritik):** Bir `ChatMessage.result` alanı varsa, mesajın
   yanında bir `ResultCard` render edilir; yoksa render edilmez.
2. **AC-2 (kritik):** `ResultCard`, işlenen dosya sayısını (`fileCount`)
   ve oluşturulan hedef klasörleri (`destinationFolders: string[]`)
   açıkça gösterir.
3. **AC-3 (yüksek):** `ResultCard`, tamamlanma durumunu (`status`)
   görsel/metinsel olarak ayırt edilebilir şekilde gösterir.
4. **AC-4 (yüksek):** `ResultCard`'ın durum metni bir
   `aria-live="polite"` bölgesinde duyurulur (PlanCard ile tutarlı
   erişilebilirlik deseni).
5. **AC-5 (orta):** `ResultCard` göründüğünde chat input alanı
   (textarea/Gönder butonu) devre dışı bırakılmaz — kullanıcı hemen
   yeni bir istek yazabilir (regresyon testi: mevcut `isGeneratingPlan`
   mantığı `ResultCard` varlığından etkilenmemeli).
6. **AC-6 (düşük):** `destinationFolders` listesi boşsa (ör. 0 dosya
   işlendiyse) kart çökmeden "hiçbir klasör oluşturulmadı" benzeri bir
   durumu net gösterir.

## Davranış Sözleşmesi (behavior-contract)

| Girdi durumu | Beklenen çıktı |
|---|---|
| `message.result` yok | `ResultCard` render edilmez |
| `result.status === 'completed'`, `fileCount > 0` | Kart görünür, dosya sayısı + klasör listesi + "tamamlandı" metni |
| `result.destinationFolders === []` | Kart çökmez, boş liste durumu net metinle gösterilir |
| `ResultCard` görünürken | `chat-input-textarea` disabled OLMAZ (mevcut `isGeneratingPlan` state'inden bağımsız) |

## Riskler / Varsayımlar / Bilinmeyenler
- **Varsayım:** Gerçek backend wiring (Saga #285) tamamlanana kadar bu
  component sadece izole (mock props) test edilecek, uçtan uca
  doğrulanamayacak — bu açıkça AI_DEVLOG'a yazılacak (Saga #273/#276
  ile tutarlı dürüstlük ilkesi).
- **Çözüldü (red-team bulgusu, aynı gün):** `TransactionResult`↔backend
  eşleşmesi belirsiz bırakılmıştı — `ui/src/lib/transactionResult.ts:
  toTransactionResult()` ile netleştirildi ve test edildi. Sözleşme:
  `destinationFolders` = `operations[].destination_path`'in EBEVEYN
  klasörlerinin (tekilleştirilmiş) listesi; `transaction.status`
  eşlemesi: `"committed"→"completed"`, `"rolled_back"→"failed"`
  (Saga #274/#276 hep-ya-da-hiç atomik geri alma garantisi verdiği
  için net sonuç sıfır dosyadır, "partial" DEĞİL), `"pending"→"partial"`
  (sadece fiilen `"completed"` olan operasyonlar sayılır). Saga #285
  HTTP wiring'i bu fonksiyonu doğrudan çağırabilir.

## Test Stratejisi
70/0/30 (unit/e2e yok — proje playwright e2e'si sadece onboarding'i
kapsıyor, bu task'a e2e eklemek kapsam dışı). React Testing Library ile
`ResultCard.test.tsx` (izole) + `ChatScreen.test.tsx`'e entegrasyon
testleri (mesaj listesinde doğru konumda render, input etkinliği).

## Benchmark
Yok — UI component, performans hedefi tanımsız/geçerli değil.
