# AI_DEVLOG.md — windows-ai-files

## ilk-istek-oturum-baglami (Saga #258, epic #23)

**İlk `saga-oto` (tam otonom, çok-task'lı) koşusu.** Bu task, yeni
oluşturulan `saga-oto` skill'i altında işlendi — ATDD/plan netleştirme
soruları kullanıcıya sorulmadı, en makul (Recommended) seçenekler
otomatik seçildi (bkz. `artifacts/ilk-istek-oturum-baglami/atdd.md`
"Sorular ve Cevaplar" bölümü, 10 soru).

**İlk backend değişikliği — Entry katmanı gerçekten bağlandı.** Frontend'in
`onContinue={() => {}}` no-op'u (Saga #255'ten beri bilinçli olarak
bekletiliyordu) artık gerçek bir `POST /api/session` çağrısı yapıyor.
Backend'de `backend/models.py` (bu projede ilk Pydantic `BaseModel`
kullanımı) + `backend/main.py`'a yeni bir route eklendi; session'lar
in-memory bir `dict`'te tutuluyor (MVP kapsamı, DB yok).

**Bulunan ve düzeltilen bug — atılan sessionId (red-team, MEDIUM).**
Backend'in ürettiği gerçek `sessionId` (UUID) frontend'e ulaşır ulaşmaz
atılıyordu — `onContinue()` parametresiz çağrılıyordu, `App.tsx` sadece
bir boolean (`sessionStarted`) tutuyordu. ATDD'nin kendi AC-5'i
("başarı iddiası doğrulanabilir bir kimliğe dayanmalı") bu yüzden sadece
testte doğrulanıyor, çalışan uygulamada hiç tutulmuyordu. Düzeltme ucuzdu
(2 dosya, `onContinue` imzasına bir parametre eklemek) — commit öncesi
uygulandı, `App.tsx` artık gerçek `sessionId`'yi state'te tutuyor.

**Bilinçli kapsam kararları.** Decision/Planner (LLM) katmanına gerçek bir
çağrı yapılmadı — backend'de henüz böyle bir modül yok, ayrı bir MVP task'ı
(muhtemelen epic #24). Session persistence/expiry yok (in-memory, restart'ta
kaybolur) — tek-kullanıcılı masaüstü MVP'si için kabul edilebilir, red-team
tarafından da onaylandı (düşük öncelikli, engelleyici değil).

## ilk-acilis-klasor-secimi-ekrani (Saga #250, epic #23)

**Zorluk — Codex kotası tükendi task ortasında.** Tooling scaffold'u yazdıktan
sonra Codex (`gpt-5.6-terra`) kullanım limitine ulaştı (Eylül 15'e kadar
kullanılamaz durumda). Kalan düzeltmeler (test cleanup/matcher kaydı, 3 e2e
hatası, red-team bulguları) `efektor` subagent'ına devredildi — pipeline'ın
öngördüğü yedek yol (bkz. proje hafızası "Copilot → Codex Geçişi").

**Bulunan bug — CORS/relative-path fetch (red-team, HIGH).** Frontend
`fetch('/api/health')` gibi göreli yollar kullanıyordu; backend'de CORS
middleware yoktu. Bu, 17 testin tamamı backend'i mock'ladığı için hiç
yakalanmamıştı — paketlenmiş Tauri uygulamasında webview origin'i
(`tauri://localhost`) ile FastAPI sidecar origin'i (`127.0.0.1:8000`) farklı
olacağından, onboarding ekranı gerçek kullanıcıda sonsuza kadar
"Başlatılıyor…" da takılı kalabilirdi. Düzeltme: mutlak URL + açık CORS
origin listesi + gerçek FastAPI `TestClient` entegrasyon testi eklendi
(`backend/tests/test_main_integration.py`) — atdd.md'nin vaat ettiği %30
integration coverage'ı artık gerçekten mock'suz karşılıyor.

**Bilinçli kapsam kararı.** Tauri/Rust iskeleti (`src-tauri/`) ve `unit_test`
tarzı ikinci bir test klasörü bu task'tan bilinçli olarak çıkarıldı — bu task
yalnızca `docs/DESIGN_DECISIONS.md`'nin frontend/backend katmanlarını
gerçekten çalışır kılmayı hedefledi, native masaüstü paketleme ayrı bir task.

## onboarding-istek-placeholder (Saga #254, epic #23)

**Zorluk — Codex kotası task başlamadan önce tamamen doluydu.** #250'de
kota task ortasında tükenmişti (yukarı bakınız); bu task'ta ise ilk
`write_tests()` çağrısı anında `ERROR: You've hit your usage limit... try
again at Sep 15th, 2026` ile başarısız oldu — hiç Codex bütçesi
harcanamadı. Kullanıcıya soruldu (dar kapsam: tek dosya, ~5 satır
implementasyon), kullanıcı onayıyla testler VE implementasyon istisnai
olarak Claude (ana asistan) tarafından yazıldı — normal test-copilot/
code-copilot kuralı ("her satır Codex'ten gelir") bu tek task için bilinçli
olarak esnetildi. Riski azaltmak için: red-team incelemesi `obss-red-team`
subagent'ı ile bağımsız çalıştırıldı ve gerçek `git diff`'i code_diff.md/
test_diff.md iddialarıyla birebir karşılaştırdı (verdict: approve,
ready_to_commit: true).

**Kalıcı öneri (red-team'den, bu task'ta uygulanmadı).** Placeholder metni
("Bu klasördeki PDF'leri tarihe göre sırala") 3 dosyada literal string
olarak tekrarlanıyor (component, unit test, e2e test). Saga #257/#258 veya
i18n bu ekrana dokunursa, ortak bir sabite (`PLACEHOLDER_TEXT` gibi)
çıkarılması önerilir — bu task'ın dar kapsamı için gerekli görülmedi.

## bos-istek-engelleme (Saga #255, epic #23)

**Codex kotası hâlâ dolu (2026-09-15'e kadar).** #254'teki gibi, `saga` skill
Bölüm C override'ı uygulandı: testler VE implementasyon Claude (ana asistan)
tarafından doğrudan yazıldı, `test-copilot`/`code-copilot` (Codex) çağrılmadı.
Bağımsız doğrulama yine `obss-red-team` subagent'ı ile yapıldı — gerçek
`git diff`'i code_diff.md/test_diff.md iddialarıyla karşılaştırdı, 21 unit +
16 e2e testi ve `tsc --noEmit`'i kendi bağlamında yeniden çalıştırıp PASS
buldu (verdict: ready_to_commit: evet).

**CSS özgüllük tuzağı önceden öngörüldü ve çözüldü.** `.onboarding-textarea:focus`
(odak kenarlığı, mavi) ile yeni `.onboarding-textarea.has-error` (hata
kenarlığı, kırmızı) aynı CSS özgüllüğüne (0,2,0) sahipti — hangisinin
kazanacağı sadece stylesheet'teki tanım sırasına bağlı kalırdı (kırılgan).
`.onboarding-textarea.has-error:focus` (0,3,0) eklenerek hata durumunun
odaklanmışken de kırmızı kalması garanti edildi; red-team bunu elle
doğrulayıp doğru bulduğunu teyit etti.

**Codex vision-test de kota nedeniyle kullanılamadı.** Standart `vision-test`
skill'i de Codex'e bağımlı olduğu için, görsel doğrulama Codex vision yerine
gerçek Vite dev server + Playwright ile alınan bir ekran görüntüsünün
(`artifacts/bos-istek-engelleme/empty_request_error_state.png`) Claude
tarafından doğrudan incelenmesiyle yapıldı — bu istisna verify_report.md'de
açıkça not edildi.

**Kalıcı öneri (red-team'den, bu task'ta uygulanmadı — low severity).**
(1) `trim()` zero-width Unicode karakterleri (ör. U+200B) temizlemiyor,
sadece bu tür karakterlerden oluşan bir istek teknik olarak "boş değil"
sayılabilir. (2) `aria-live="polite"` container'ı koşullu mount ediliyor
(her zaman DOM'da olup sadece içeriği değişen bir container yerine) — bazı
ekran okuyucu/tarayıcı kombinasyonlarında duyuru güvenilirliğini
etkileyebilir. İkisi de bu task'ın dar kapsamı (client-side, backend
validasyonu yok) için engelleyici değil, ayrı bir iyileştirme task'ı olarak
değerlendirilebilir.

## gecersiz-klasor-reddi (Saga #256, epic #23)

**Codex kotası hâlâ dolu — aynı override deseni devam ediyor.** Testler ve
implementasyon yine Claude tarafından doğrudan yazıldı, bağımsız doğrulama
`obss-red-team` subagent'ı ile yapıldı.

**Mimari keşif — src-tauri/ ve @tauri-apps/plugin-fs hiç yok.** Bu görev
"klasörün erişilebilir olduğunu doğrula" istiyordu, ama projede gerçek bir
Tauri native kabuğu (`src-tauri/`) veya dosya sistemi plugin'i henüz
scaffold edilmemiş (#250'de bilinçli olarak dışarıda bırakılmıştı).
Kullanıcıya soruldu, kullanıcı "mock'lanabilir Tauri invoke ile ilerle"
seçeneğini onayladı: yeni kod `invoke('plugin:fs|exists', {path})`
çağırıyor ama bu şu an sadece testlerde (`__TAURI_INTERNALS__` / vi.mock)
karşılık buluyor, gerçek bir dosya sistemi kontrolü yok.

**Bulunan risk — HIGH, red-team'den (bu task'ın kendi hatası değil, proje
geneli bir eksiklik).** Eğer uygulama gerçek `plugin-fs` bağlanmadan
paketlenip (`tauri build`) kullanıcıya ulaşırsa, `invoke` reddedilir ve kod
bunu "erişilemez" sayıp HER klasörü reddeder — onboarding kalıcı bir çıkmaz
sokak olur, hiçbir testte görünmez çünkü tüm testler mock'lanmış IPC
katmanını kullanıyor. Bu, 2026-08-16'daki Codex "success:True ama hiçbir
şey yapmadı" olayıyla aynı sınıftan bir risk — sadece test zamanında değil,
paketleme zamanında ortaya çıkıyor. **Aksiyon:** Saga task #279
("RELEASE-BLOCKER: Gerçek @tauri-apps/plugin-fs entegrasyonu", critical,
#256'ya `depends_on`) oluşturuldu — bu task tamamlanmadan `.exe`/installer
paketleme yapılmamalı.

**Bulunan ve düzeltilen bug — TOCTOU boşluğu (red-team, MEDIUM).** İlk
implementasyonda, kullanıcı zaten geçerli bir klasör seçmişken (Devam
aktif) yeni bir klasör seçtiğinde, yeni `exists` kontrolü sonuçlanana kadar
geçen asenkron pencerede eski `isFolderInvalid=false` durumu geçerli
kalıyordu — "Devam" doğrulanmamış yeni bir klasörle tıklanabilir kalıyordu,
tam da bu task'ın önlemeye çalıştığı senaryonun bir zamanlama varyantı.
Düzeltme: `isValidatingFolder` state'i eklenip "Devam"ın `disabled`
koşuluna dahil edildi; bunu doğrulayan test eklenirken mevcut bir testte
(AC-5) senkron `isFolderInvalid(false)` sıfırlamasının yarattığı stale-DOM
eşleşme yarışı da ortaya çıktı ve `waitFor` sıralaması düzeltilerek
giderildi.

**Bilinçli kapsam kararı.** "Yok" ile "izinsiz" hata nedenleri ayrı ele
alınmadı (tek "erişilemez" mesajı), kapsamlı path normalization (case,
symlink) yapılmadı — sadece trailing slash/backslash temizlendi. Red-team
kök sürücü path'lerinde (`C:\` → `C:`) bu minimal normalize'ın bir edge
case'i kaçırdığını (low severity) not etti, düzeltilmedi.

## klavye-ile-form-gezintisi (Saga #257, epic #23)

**Codex kotası hâlâ dolu — aynı override deseni.** Testler ve
implementasyon Claude tarafından doğrudan yazıldı, bağımsız doğrulama
`obss-red-team` subagent'ı ile yapıldı.

**Bulunan ve düzeltilen bug — doğrulama atlatma (red-team, MEDIUM).**
`handleContinueClick`, "Devam" butonunun `disabled` özniteliğindeki
`isFolderInvalid`/`isValidatingFolder` kontrollerini içermiyordu — bu
kontrol sadece JSX'teki `disabled` ifadesinde vardı, fonksiyonun kendi
mantığında değil. Bu görev kapsamında `selected-folder-path` elementine
Enter-ile-submit eklenince (klasör durumundan bağımsız her zaman
odaklanabilir bir eleman), klavye kullanıcısı geçersiz bir klasör
seçiliyken bu elemana Tab'layıp Enter'a basarak `onContinue()`'u
tetikleyebiliyordu — fare kullanıcısının disabled buton sayesinde
atlayamadığı bir kontrolü klavye kullanıcısı atlatabiliyordu. Tam da
erişilebilirlik odaklı bir görevin önlemesi gereken türden bir
mouse/klavye asimetrisi. **Düzeltme:** `canSubmit` adında tek bir
paylaşılan predicate çıkarıldı (`isReady && selectedFolder && !isFolderInvalid
&& !isValidatingFolder`), hem butonun `disabled`'ında hem
`handleContinueClick`'in başında kullanıldı — kural artık tek yerde
tanımlı, bir regresyon testiyle doğrulandı.

**Mimari keşif — native buton Enter davranışına güvenme kararı doğrulandı.**
`atdd.md`/`plan.md` aşamasında, "Klasör Seç" ve "Devam" butonlarına Enter
için ayrı `onKeyDown` eklenip eklenmeyeceği bir Unknown olarak
işaretlenmişti (jsdom'da native Enter→click davranışı güvenilir simüle
edilemiyor). Gerçek Playwright/Chromium'da test edilince bu varsayım
doğrulandı — ek kod gerekmedi, sadece native buton olmayan tek odaklanabilir
eleman olan `selected-folder-path`'e `onKeyDown` eklendi. Red-team ayrıca
gerçek paketlemede Tauri'nin WebView2 (Windows) kullanacağını, bunun
Playwright'ın Chromium'undan farklı bir motor olabileceğini not etti —
bu, henüz gerçek Tauri paketlemesi olmadığı için (Saga #279, release-blocker)
doğrudan test edilemedi, ileride #279 kapatılınca yeniden doğrulanmalı.
