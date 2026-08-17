---
task_slug: plan-skeleton-sinir-sema-dogrulamasi
priority: medium
coverage_target: "AC'lerin tamamı unit test ile kapsanır"
performance_target: "yok (saf fonksiyon, ölçülebilir performans hedefi yok)"
test_strategy: "100/0/0 (unit) — saf fonksiyon, DOM/integration gerektirmiyor"
affected_modules: ["ui/src/components/chat/planValidation.ts"]
---

# LLM plan-skeleton yanıtı için sınırda (boundary) şema doğrulaması ekle (Saga #280)

## Persona
Backend'den (henüz entegre edilmemiş LLM plan-skeleton yanıtı) gelen veriyi
işleyecek olan gelecekteki entegrasyon kodu ve dolaylı olarak, bir dosya
işlemini onaylamadan önce doğru kapsam bilgisini görmesi gereken kullanıcı.

## Goal
`Plan` tipindeki veri (order/operationType/targetFolder/affectedFileCount)
backend'den geldiği NOKTADA (henüz gerçek bir fetch/parse noktası yok, bu
task saf bir doğrulama fonksiyonu sağlıyor) runtime'da doğrulanmalı:
order alanı non-negative-integer + adımlar arasında tekil olmalı,
operationType bilinen bir enum'dan olmalı, affectedFileCount
non-negative-integer olmalı. Malformed/adversarial bir yanıt PlanCard'a
asla ulaşmamalı.

## User Story
Bir geliştirici olarak, backend entegrasyonu geldiğinde LLM'den gelen
plan-skeleton yanıtını PlanCard'a geçirmeden önce tek bir fonksiyonla
doğrulayabilmek istiyorum, böylece malformed bir yanıt kullanıcıya yanlış
kapsam (ör. negatif dosya sayısı, bilinmeyen bir işlem türü) göstermez.

## Acceptance Criteria (öncelik sırasına göre)
1. `validatePlanResponse(data: unknown)` saf bir fonksiyon dışa aktarılır;
   `{ ok: true, plan: Plan }` veya `{ ok: false, error: string }` döner
   (fail-closed: belirsiz/eksik veri asla sessizce "geçerli" sayılmaz).
2. `order`: negatif olmayan tamsayı olmalı; `steps` dizisi içinde TEKİL
   olmalı (aynı order iki kez geçemez).
3. `operationType`: bilinen bir enum'dan biri olmalı (`Taşı`, `Kopyala`,
   `Sil`, `Yeniden Adlandır`, `Listele`) — bilinmeyen bir değer reddedilir.
4. `affectedFileCount`: negatif olmayan tamsayı olmalı.
5. `targetFolder`: boş olmayan bir string olmalı.
6. `securityStatus` (opsiyonel): verilirse `'approved'` veya `'rejected'`
   olmalı; başka bir değer reddedilir.
7. `steps` dizisi boş olabilir (geçerli, PlanCard zaten boş listeyi
   destekliyor — Saga #262 behaviour contract).
8. Hata mesajı, hangi alanın/adımın geçersiz olduğunu kısaca belirtir
   (debug edilebilirlik).

## Behaviour-contract tablosu
| Girdi | Beklenen sonuç |
|---|---|
| Geçerli, tam bir Plan nesnesi | `{ ok: true, plan }` |
| `steps` dizisi boş | `{ ok: true, plan: { steps: [] } }` |
| `order` negatif veya ondalık | `{ ok: false, error: ... }` |
| İki adımda aynı `order` | `{ ok: false, error: ... }` |
| Bilinmeyen `operationType` | `{ ok: false, error: ... }` |
| `affectedFileCount` negatif | `{ ok: false, error: ... }` |
| `targetFolder` boş string | `{ ok: false, error: ... }` |
| `data` bir obje değil / `steps` yok | `{ ok: false, error: ... }` |
| Geçersiz `securityStatus` (ör. `"maybe"`) | `{ ok: false, error: ... }` |

## Risks/Assumptions/Unknowns
- Assumption: Yeni bir bağımlılık (zod vb.) EKLENMEDİ — proje
  `package.json`'da böyle bir kütüphane yok ve tek bir saf fonksiyon için
  yeni bağımlılık eklemek dar-kapsam ilkesiyle çelişir; el yazımı bir
  doğrulayıcı yeterli ve test edilebilir. (saga-oto tarafından otomatik
  seçildi)
- Assumption: Bilinen `operationType` enum'u (`Taşı`, `Kopyala`, `Sil`,
  `Yeniden Adlandır`, `Listele`) bu task'ta İLK KEZ tanımlanıyor —
  gerçek backend/LLM sözleşmesi henüz yok, bu proje-içi bir varsayım.
  Gerçek entegrasyon geldiğinde bu liste güncellenebilir. (saga-oto
  tarafından otomatik seçildi)
- Assumption: Bu fonksiyon HENÜZ `ChatScreen`/`PlanCard`'a bağlanmadı —
  gerçek bir fetch/parse noktası olmadığı için entegre edilecek somut bir
  yer yok (dar kapsam, #264-267 ile aynı desen: backend entegrasyonu
  ayrı bir task). Fonksiyon, o entegrasyon geldiğinde doğrudan kullanılmaya
  hazır, bağımsız test edilmiş bir yapı taşı olarak sağlanıyor. (saga-oto
  tarafından otomatik seçildi)

## Test Strategy
100/0/0 unit. `planValidation.test.ts` — saf fonksiyon, DOM gerektirmiyor.

## Benchmark
Kabul kriteri: `npx vitest run` içinde tüm testler yeşil.

## Sorular ve Cevaplar (saga-oto otomatik)
- S: zod gibi bir kütüphane mi kullanılmalı? C: Hayır — proje bunu zaten
  kullanmıyor, tek bir doğrulama fonksiyonu için yeni bağımlılık eklemek
  dar-kapsam ilkesiyle çelişir. El yazımı, test edilmiş bir fonksiyon
  yeterli. (saga-oto tarafından otomatik seçildi)
- S: Fonksiyon şimdi ChatScreen'e bağlanmalı mı? C: Hayır — henüz gerçek
  bir backend/fetch entegrasyon noktası yok, bağlamak için "sahte" bir
  entegrasyon noktası icat etmek kapsam dışına taşar. (saga-oto
  tarafından otomatik seçildi)
