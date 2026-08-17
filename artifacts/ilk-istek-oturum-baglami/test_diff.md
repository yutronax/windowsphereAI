# Test Diff — ilk-istek-oturum-baglami
_Reference: atdd.md, plan.md_

> **Not:** Codex CLI kotası dolu. `saga-oto` skill'i altında, testler +
> implementasyon istisnai olarak Claude tarafından doğrudan yazıldı.
> ATDD/plan netleştirme soruları da `AskUserQuestion` çağrılmadan
> otomatik (Recommended) cevaplandı — bkz. atdd.md.

## Eklenen Testler

### `backend/tests/test_main_integration.py` (pytest — TestClient)
Mevcut pattern genişletildi, 5 yeni test:

| Test | AC | Doğruladığı |
|---|---|---|
| test_session_endpoint_creates_a_session_with_a_uuid_and_echoes_input | AC-1, AC-5 | Happy path: `201` + gerçek bir UUID `sessionId` + girilen alanların yankılanması |
| test_session_endpoint_returns_422_for_empty_selected_folder | AC-2 | Boş `selectedFolder` reddedilir |
| test_session_endpoint_returns_422_for_whitespace_only_request_text | AC-2 | Sadece boşluktan oluşan `requestText` reddedilir |
| test_session_endpoint_returns_422_for_missing_fields | AC-2 | Eksik alanlarla `422` |
| test_cors_header_present_for_session_post_from_allowed_origin | AC-6 | `POST /api/session`'ın da CORS middleware'inden geçtiği (regresyon) |

Çalıştırma önce (red): 4/6 yeni test FAIL (`404`, route henüz yoktu),
8 eski test PASS.

### `ui/src/components/onboarding/OnboardingScreen.test.tsx` (unit — Vitest/RTL)
Dosya geneline bir `beforeEach` eklendi (`vi.stubGlobal('fetch', ...)`,
varsayılan olarak başarılı yanıt döner) — mevcut testlerin `handleContinueClick`
artık gerçek bir `fetch` çağrısı içerdiği için kırılmaması sağlandı; 2 eski
test (AC-1 happy path, klavye AC-3) senkron `onContinue` beklentisinden
`await waitFor(...)`e geçirildi (implementasyon regresyonu değil, testin
artık asenkron bir çağrıyı beklemesi gerekiyor).

Yeni `describe('session submission (ilk-istek-oturum-baglami)')` bloğu, 4 test:

| Test | AC | Doğruladığı |
|---|---|---|
| POSTs the selected folder and request text to /api/session and calls onContinue on success | AC-1 | Doğru URL/body ile POST, başarıda `onContinue` çağrılıyor |
| shows a submit error and does not call onContinue when the backend rejects the request | AC-2 | `response.ok=false` → hata mesajı, `onContinue` ÇAĞRILMAZ |
| shows a submit error and does not call onContinue when the network request fails | AC-3 | `fetch` reddi → hata mesajı, buton tekrar aktif |
| disables Continue while the request is in flight to prevent a double submit | AC-4 | Bekleyen promise sırasında buton disabled, sonuçlanınca tekrar aktif |

### `ui/src/App.test.tsx` (unit — Vitest/RTL, YENİ dosya)
`OnboardingScreen` mock'lanarak (dar kapsam — kendi mantığı zaten kendi
dosyasında test ediliyor), App.tsx'in `onContinue`'u gerçekten
`main-chat-screen`'e geçişe bağladığı doğrulandı (AC-1).

### `ui/e2e/onboarding.spec.ts` (e2e — Playwright)
2 yeni test:

| Test | AC | Doğruladığı |
|---|---|---|
| posts the request to /api/session and shows the main chat screen on success | AC-1 | Gerçek tarayıcıda uçtan uca: POST gövdesi doğru, başarıda ana ekrana geçiş |
| shows a submit error and keeps Continue usable when the backend is unreachable | AC-3 | Gerçek tarayıcıda ağ hatası senaryosu, buton tekrar aktif, ana ekrana geçiş YOK |

## Doğrulama Komutları ve Sonuç (red → green)
```
"../.venv/Scripts/python.exe" -m pytest backend/tests/ -v
```
- Öncesi: 4 failed / 9 passed (13 total).
- Sonrası: **13 passed (13)**.

```
npx vitest run
```
- **42 passed (42)** — 3 test dosyası (backendHealth, App, OnboardingScreen).

```
npx playwright test ui/e2e/onboarding.spec.ts
```
- **26 passed (26)**, hiçbir mevcut test regresyona uğramadı.

```
npx tsc --noEmit
```
- Küçük bir tip hatası (`Promise<Response>` generic'i eksikti) düzeltildi, sonrasında hatasız.

## Kapsam Dışı Bırakılanlar (atdd.md ile tutarlı)
- Decision/Planner katmanına gerçek çağrı — test edilmedi (henüz yok).
- Session persistence/expiry — test edilmedi (in-memory, MVP kapsamı).

## Red-Team Sonrası Güncelleme
`App.test.tsx`'teki mock `onContinue` çağrısı, red-team düzeltmesiyle
(sessionId'nin artık gerçekten `onContinue(sessionId)` ile iletilmesi)
tutarlı olacak şekilde güncellendi — mock artık gerçek bir UUID string'i
ile çağırıyor. Tüm testler (13 pytest + 42 vitest + 26 e2e) düzeltme
sonrası yeniden çalıştırılıp yeşil kaldı.
