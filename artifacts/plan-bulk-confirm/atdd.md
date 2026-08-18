# ATDD — Büyük planlar için bulk-onay eşiği (Saga #311)

## Persona
Mali müşavir, yanlış klasörde/pattern'de çok sayıda dosyayı etkileyen bir
planı yanlışlıkla tek tıkla onaylayabilir ("yanlış klasör, 1000 dosya"
riski).

## Goal
`PlanCard`, toplam `affectedFileCount` bir eşiği (20) aşarsa normal
onaya ek olarak ikinci bir açık onay adımı istesin — `ResultCard`'ın
revert butonundaki mevcut iki-aşamalı desenle (confirming state) TUTARLI.

## Acceptance Criteria
1. **P0** — Tüm step'lerin `affectedFileCount` toplamı ≤ 20 ise davranış
   DEĞİŞMEZ: "Planı onayla" butonu tek tıkla `onApprove`'u tetikler.
2. **P0** — Toplam > 20 ise "Planı onayla" tıklanınca `onApprove` HEMEN
   tetiklenmez — buton "Evet, onayla (N dosya)"/"Vazgeç" ikilisine döner
   (ResultCard'ın `confirming` state deseniyle aynı).
3. **P0** — Bu ikinci ekranda SADECE "Evet, onayla" tıklanırsa `onApprove`
   tetiklenir. "Vazgeç" ilk duruma döner, `onApprove` ÇAĞRILMAZ.
4. **P1** — Eşik aşıldığında kullanıcıya toplam dosya sayısını gösteren
   bir uyarı metni görünür olmalı (aria-live, mevcut `statusText` deseniyle
   tutarlı erişilebilirlik).
5. **P1** — `canApprove` (fail-closed: securityStatus==='approved' vb.)
   mantığı DEĞİŞMEZ — bulk-confirm SADECE zaten onaylanabilir bir planın
   ÜZERİNE ek bir adım ekler, güvenlik kontrolünü BYPASS ETMEZ.

## Behavior-Contract Table
| Senaryo | Beklenen |
|---|---|
| Toplam affectedFileCount = 5 | Tek tıkla onay, eski davranış |
| Toplam affectedFileCount = 20 (eşik dahil) | Tek tıkla onay (eşik "aşan", yani >20 tetikler) |
| Toplam affectedFileCount = 21 | İki aşamalı onay gerekir |
| İkinci aşamada "Vazgeç" | onApprove çağrılmaz, ilk duruma döner |
| İkinci aşamada "Evet, onayla" | onApprove bir kez çağrılır |

## Test Strategy
`ui/src/components/chat/PlanCard.test.tsx` — mevcut testing-library
deseniyle (render + fireEvent/userEvent), yeni test case'ler eklenir.

## Risks/Assumptions
- Eşik değeri (20) sabit/hardcoded — konfigüre edilebilir hale getirmek
  kapsam dışı (YAGNI, ihtiyaç çıkarsa ayrı task).
- Backend'de HİÇBİR değişiklik yok — affectedFileCount zaten PlanStep
  şemasında var, sadece frontend'de toplanıp eşikle karşılaştırılıyor.
