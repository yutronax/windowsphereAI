# Code Diff — onboarding-kurumsal-tema

## Kapsam
Saf görsel yeniden markalama (rebrand) — `OnboardingScreen.tsx`'in birincil rengi ve textarea köşe
yuvarlaklığı, Stitch'te tasarlanan "Kurumsal Mavi" tasarım sistemine (round-8, #1E3A8A lacivert vurgu,
nötr gri paletler) uyarlandı. Davranış/mantık DEĞİŞMEDİ.

## Değişen Dosyalar
- `ui/src/components/onboarding/OnboardingScreen.tsx` — 7 satır (CSS-in-JS `<style>` bloğu)
- `ui/src/components/onboarding/OnboardingScreen.test.tsx` — 3 assertion (aynı renk/köşe değişikliğine uyacak şekilde)

## Değişiklik Detayı
| Selector | Önce | Sonra |
|---|---|---|
| `.onboarding-primary-btn` background | `#2563EB` | `#1E3A8A` |
| `.onboarding-primary-btn:hover` background | `#1D4ED8` | `#1E3172` |
| `.onboarding-primary-btn:active` background | `#1E40AF` | `#172554` |
| `.onboarding-primary-btn:focus-visible` outline | `#1E40AF` | `#1E3A8A` |
| `.onboarding-textarea` border-radius | `12px` | `8px` |
| `.onboarding-textarea:focus` border-color | `#2563EB` | `#1E3A8A` |
| `.onboarding-textarea:focus` box-shadow rgba | `rgba(37, 99, 235, 0.1)` | `rgba(30, 58, 138, 0.1)` |

Dokunulmayanlar: buton border-radius (zaten 8px), disabled gri (#94A3B8), hata kırmızısı (#DC2626),
placeholder grisi (#9CA3AF) — tasarım sistemi bu renkleri değiştirmiyor.

## Kaynak
Stitch proje `8201928347519567924`, ekran `b0b3f7a52b8148ddb5bed1effb392fc1` ("Karşılama Ekranı" v2,
kullanıcı tarafından "daha kurumsal" olarak seçildi), tasarım sistemi `assets/7397222156595862201`
("Windows AI Files — Kurumsal Mavi": NEUTRAL variant, #1E3A8A seed, ROUND_EIGHT).

## Doğrulama (bu adımda zaten yapıldı)
- `npx vitest run ui/src/components/onboarding` → 38/38 PASS
- Tarayıcıda canlı ekran görüntüsüyle doğrulandı (backend `/api/health` 200 ile ready durumunda,
  buton koyu lacivert, textarea round-8 görünüyor)

## Atdd/Test Strategy Notu
Bu görev için ayrı bir `atdd.md`/`test_diff.md` yazılmadı — kapsam çok dar (2 dosya, 10 satır, davranış
değişikliği yok, sadece var olan görsel-spec testlerinin güncellenmesi) ve zaten mevcut Saga #257
davranış testleri (klavye/odak) tarafından bütünlük korunuyor. `verify`/`red-team` yine de tam
zincirden geçiyor.
