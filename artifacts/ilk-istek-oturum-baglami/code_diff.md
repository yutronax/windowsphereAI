# Code Diff — ilk-istek-oturum-baglami
_Reference: atdd.md, plan.md, test_diff.md_

> **Not:** Codex kotası dolu; implementasyon istisnai olarak Claude
> tarafından yazıldı (`saga-oto` skill'i altında).

## Yeni Dosya: `backend/models.py`
`SessionRequest` (`selectedFolder`, `requestText`, ikisi de `field_validator`
ile trim edilince boş olamaz) ve `SessionContext` (`sessionId`,
`selectedFolder`, `requestText`) Pydantic modelleri. Bu projede ilk Pydantic
`BaseModel` kullanımı — daha önce `config.py`/`main.py` sade `dict[str, str]`
kullanıyordu; FastAPI'nin kendi bağımlılığı olduğu için ek paket kurulumu
gerekmedi (doğrulandı: `pydantic 2.12.5` zaten kurulu).

## Değiştirilen Dosya: `backend/main.py`
- Yeni import: `uuid`, `status` (fastapi), `SessionContext`/`SessionRequest` (models.py).
- Modül seviyesinde `_sessions: dict[str, SessionContext] = {}` — in-memory
  session store (atdd.md'nin bilinçli kapsam kararı: MVP için DB gereksiz).
- Yeni route:
  ```python
  @app.post("/api/session", status_code=status.HTTP_201_CREATED)
  def create_session(payload: SessionRequest) -> SessionContext:
      session = SessionContext(
          sessionId=str(uuid.uuid4()),
          selectedFolder=payload.selectedFolder,
          requestText=payload.requestText,
      )
      _sessions[session.sessionId] = session
      return session
  ```
  FastAPI, `SessionRequest` gövde doğrulamasını (boş/whitespace-only alanlar
  için `422`) otomatik uyguluyor — davranış sözleşmesi tablosundaki 2.
  satırla (AC-2) uyumlu.

## Değiştirilen Dosya: `ui/src/lib/backendHealth.ts`
`BACKEND_ORIGIN` sabiti `export` edildi — `OnboardingScreen.tsx`'in yeni
`fetch` çağrısı bunu import edip kullanıyor, aynı origin string'i iki
yerde tekrar tanımlanmadı.

## Değiştirilen Dosya: `ui/src/components/onboarding/OnboardingScreen.tsx`
- Yeni import: `BACKEND_ORIGIN`.
- Yeni state'ler: `isSubmitting`, `submitError`.
- `canSubmit` predicate'ine `!isSubmitting` eklendi (çift gönderim engelleme, AC-4).
- `handleContinueClick` `async` oldu: boş-istek kontrolünden sonra
  `fetch(BACKEND_ORIGIN + '/api/session', {method:'POST', ...})` çağrılıyor;
  `response.ok` ise `onContinue()` çağrılır (AC-1), aksi halde (HTTP hatası
  VEYA `fetch` reddi — ikisi de aynı `catch` bloğunda) `submitError` set
  edilip mevcut `.onboarding-error-message`/`aria-live` pattern'iyle
  gösterilir (AC-2, AC-3 — aynı davranış sözleşmesi satırında birleştirildi,
  atdd.md'de gerekçelendirildiği gibi).
- JSX'e `submitError` gösterimi eklendi (mevcut hata pattern'i tekrar kullanıldı, yeni CSS yok).

## Değiştirilen Dosya: `ui/src/App.tsx`
- Yeni state: `sessionId` (`string | null`).
- `onContinue={() => {}}` → `onContinue={setSessionId}`.
- Render koşulu `if (config)` → `if (config || sessionId)` — mevcut
  `main-chat-screen` stub'ı olduğu gibi yeniden kullanıldı, yeni bir ekran
  İNŞA EDİLMEDİ (atdd.md Kapsam Dışı kararıyla uyumlu).

**Red-team düzeltmesi (commit öncesi uygulandı):** İlk versiyonda backend'in
ürettiği gerçek `sessionId` (UUID) frontend'e ulaşır ulaşmaz atılıyordu —
`onContinue()` parametresiz çağrılıyor, `App.tsx` sadece bir boolean
(`sessionStarted`) tutuyordu. Bağımsız red-team incelemesi bunu AC-5'in
("başarı iddiası doğrulanabilir bir kimliğe dayanmalı") sadece testte
doğrulanıp çalışan uygulamada hiç tutulmadığını, ucuz bir düzeltme
olduğunu belirtti. **Düzeltme:** `OnboardingScreen`'in `onContinue` prop
tipi `(sessionId: string) => void` oldu, `handleContinueClick` başarılı
yanıtı `response.json()` ile parse edip `onContinue(session.sessionId)`
çağırıyor; `App.tsx` bunu `sessionId` state'inde tutuyor. Gelecekteki
Decision/Planner entegrasyonu (Saga #24 kapsamında) bu kimliği yeniden
türetmek zorunda kalmayacak.

## Yeni Dosya: `ui/src/App.test.tsx`
İlk kez App.tsx için bir test dosyası — `OnboardingScreen` mock'lanarak
sadece `onContinue` → `main-chat-screen` geçişi dar kapsamda doğrulanıyor.

## Değiştirilmeyen (plan.md ile tutarlı)
- Decision/Planner modülü — yok, eklenmedi (kapsam dışı).
- `config.py`/`/api/config` — dokunulmadı.
- CORS middleware yapılandırması — değişmedi, sadece bir regresyon testi eklendi.

## Doğrulama
- `"../.venv/Scripts/python.exe" -m pytest backend/tests/ -v` → 13/13 geçti.
- `npx vitest run` → 42/42 geçti.
- `npx playwright test ui/e2e/onboarding.spec.ts` → 26/26 geçti.
- `npx tsc --noEmit` → hatasız.
- `npm run build` → başarılı.
- Manuel ekran görüntüsü (`artifacts/ilk-istek-oturum-baglami/submit_error_state.png`): gönderim hatası mesajı ve aktif "Devam" butonu doğrulandı.
