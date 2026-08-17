# Plan — ilk-istek-oturum-baglami
_Reference: atdd.md_

## Files to Modify
| File | Why | Risk |
|------|-----|------|
| backend/main.py | Yeni `POST /api/session` route'u eklenecek — `SessionRequest` gövdesini alıp `models.py`'deki Pydantic modellerle doğrular, geçerliyse `uuid4()` ile `sessionId` üretip in-memory bir `dict`'e (`_sessions: dict[str, SessionContext]`) kaydeder, `201` + `SessionContext` döner. | medium |
| backend/models.py | Yeni dosya — `SessionRequest` (`selectedFolder: str`, `requestText: str`, ikisi de `min_length=1` ile boş/whitespace-only reddedilir — Pydantic `field_validator` ile `.strip()` kontrolü) ve `SessionContext` (`sessionId: str`, `selectedFolder: str`, `requestText: str`) modelleri. | low |
| backend/tests/test_main_integration.py | Mevcut `TestClient` pattern'i genişletilecek: happy path (`201` + `sessionId` UUID formatı kontrolü), boş `selectedFolder`/`requestText` ile `422`, CORS `POST` için `tauri://localhost` origin testi (AC-6). | low |
| ui/src/lib/backendHealth.ts | `BACKEND_ORIGIN` sabiti `export` edilecek — `OnboardingScreen.tsx`'in yeni `fetch` çağrısı bunu import edip kullanacak, aynı origin string'i iki yerde tekrar tanımlanmayacak. | low |
| ui/src/components/onboarding/OnboardingScreen.tsx | `handleContinueClick` async hale getirilecek: `canSubmit`/boş-istek kontrollerinden SONRA `fetch(BACKEND_ORIGIN + '/api/session', {method:'POST', ...})` çağrılır. Yeni state'ler: `isSubmitting` (buton disabled'a eklenir, AC-4), `submitError` (mevcut `.onboarding-error-message`/`aria-live` pattern'iyle gösterilir, AC-3). Başarılı yanıtta `onContinue()` çağrılır (AC-1). | medium |
| ui/src/components/onboarding/OnboardingScreen.test.tsx | Yeni testler: happy path (`global.fetch` mock, `onContinue` çağrıldığını doğrula), backend hatası (fetch reject/non-ok → `submitError` gösterilir, `onContinue` ÇAĞRILMAZ), çift-gönderim engelleme (`isSubmitting` sırasında buton disabled). | low |
| ui/src/App.tsx | `onContinue={() => {}}` yerine gerçek bir state güncelleyen fonksiyon: `const [sessionStarted, setSessionStarted] = useState(false); ... onContinue={() => setSessionStarted(true)}`. Render koşulu `if (config) return <main-chat-screen>` yerine `if (config || sessionStarted) return <main-chat-screen>` olacak — mevcut stub yeniden kullanılıyor, yeni bir ekran YOK. | low |
| ui/src/App.test.tsx | Yeni dosya — şu an `App.tsx` için hiç test yok. Minimal kapsam: `onContinue` çağrıldığında `main-chat-screen`'in göründüğünü doğrulayan bir test (AC-1'in App.tsx tarafı). `OnboardingScreen`'in kendi fetch mantığı zaten kendi test dosyasında kapsandığından, burada `OnboardingScreen`'i `vi.mock` ile sadeleştirip sadece `onContinue` prop'unun çağrılması simüle edilecek (dar kapsam — App.tsx'in tüm mevcut davranışını yeniden test etmek bu task'ın işi değil). | low |
| ui/e2e/onboarding.spec.ts | Yeni testler: `page.route('**/api/session', ...)` ile happy path (main-chat-screen'e geçiş) ve backend-hatası (`route.fulfill({status: 500})` veya `route.abort()`) senaryoları. | low |

## New Files
| File | Purpose |
|------|---------|
| backend/models.py | `SessionRequest`/`SessionContext` Pydantic modelleri (Entry katmanının veri sözleşmesi). |
| ui/src/App.test.tsx | App.tsx için ilk test dosyası — minimal, sadece bu task'ın eklediği geçiş mantığını kapsar. |

## Dependencies
- `backend/main.py`, mevcut `CORSMiddleware` yapılandırmasına (zaten `allow_methods=["*"]`) DOKUNMUYOR — POST zaten kapsanıyor, sadece bir regresyon testi ekleniyor (AC-6).
- Yeni `models.py`, mevcut `config.py`'nin kullandığı sade `dict[str, str]` yerine ilk kez Pydantic `BaseModel` kullanacak — bu projede bir ilk, ama FastAPI zaten Pydantic'i transitive olarak içeriyor (ek bağımlılık gerekmiyor, `import pydantic` proje `node_modules`/`site-packages`'ında zaten mevcut olmalı — `plan` doğrulaması sırasında kontrol edilecek).
- `OnboardingScreen.tsx`'in mevcut `isFolderInvalid`/`isValidatingFolder`/`isRequestEmpty` state mimarisiyle TUTARLI yeni state'ler (`isSubmitting`, `submitError`) ekleniyor — aynı adlandırma ve hata gösterme konvansiyonu (`.onboarding-error-message`, `aria-live="polite"`) tekrar kullanılıyor, yeni bir mekanizma icat edilmiyor.
- `App.tsx`'in mevcut `config`/`backendStatus` state mimarisi KORUNUYOR, sadece yeni bir `sessionStarted` state'i ekleniyor — mevcut `waitForBackendHealth`/`fetch('/api/config')` mantığına dokunulmuyor.

## Migration Required?
No — backend'de DB/schema yok (in-memory `dict`), frontend'de sadece yeni bir `fetch` çağrısı ve state.

## Risks
- (atdd.md'den taşındı) `SessionContext` şemasının ileride Decision/Planner entegrasyonuyla genişleyebileceği — bu task'ın kapsamı dışı, sadece not düşülüyor.
- (atdd.md'den taşındı) In-memory session store restart'ta kaybolur — MVP için kabul edilebilir.
- `pydantic`'in backend'de gerçekten kurulu/import edilebilir olduğu doğrulanmalı (FastAPI'nin bir bağımlılığı olduğu için büyük ihtimalle zaten var, ama proje kendi `requirements.txt`'unu tanımlamadığından — SETUP.md satır 18 — hangi paket setinin gerçekte kurulu olduğu net değil). İmplementasyon adımında `"../.venv/Scripts/python.exe" -c "import pydantic"` ile doğrulanacak, başarısız olursa (paket eksikse) bu bir gerçek engelleyici olur ve kullanıcıya raporlanır (kurulum adımı bu skill'in "standing yetkisi" kapsamında değil — paket kurulumu proje bağımlılık yönetimini etkiler).
- `ui/src/App.test.tsx` yeni bir dosya olduğu için, `OnboardingScreen`'i mock'larken gerçek prop tipini (`backendStatus`, `onContinue`, `onRetry`) doğru simüle etmek gerekiyor — implementasyon sırasında dikkat edilecek.

## Open Questions
Yok — atdd.md'deki 10 soru-cevap ve yukarıdaki pydantic-kurulum doğrulama adımı planı tamamlamaya yetti. `saga-oto` modunda olduğumuz için bir açık soru çıksa bile kullanıcıya sorulmayacak, en dar/en düşük riskli seçenek seçilip Assumptions'a yazılacaktı.

## Not
`OnboardingScreen.tsx` ve `App.tsx` rendered web UI dosyaları — `verify` adımında görsel doğrulama (Codex vision-test kotası dolu olduğu için manuel/Playwright screenshot yöntemiyle) gönderim-hatası mesajının doğru göründüğünü teyit edecek.
