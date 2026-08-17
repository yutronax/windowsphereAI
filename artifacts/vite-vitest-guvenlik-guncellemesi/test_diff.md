# Test Diff — vite-vitest-guvenlik-guncellemesi
_Reference: atdd.md_

Bu task yeni bir test YAZMADI (atdd.md'nin kendi kararı — bir bağımlılık
yükseltmesi task'ı, davranış değişikliği yok). Mevcut TÜM test paketi
regresyon kanıtı olarak kullanıldı:

- Backend: `pytest` → 13/13 (değişmedi, npm'e bağımlı değil).
- Frontend unit: `vitest` → 42/42 (yükseltmeden önce de 42'ydi).
- Frontend e2e: `playwright` → 26/26 (yükseltmeden önce de 26'ydı).
- Build: `npm run build` → başarılı.
- `npm audit` → öncesi 5 zafiyet (3 moderate, 1 high, 1 critical), sonrası 0.
